"""
Mail sync tasks

Syncs in-game mail from ESI
"""
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_
import logging
import asyncio

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.character import Character
from app.models.eve_token import EveToken
from app.models.mail import Mail, MailLabel, MailingList
from app.services.esi_client import esi_client, ESIError, ESIRateLimitError
from app.websockets.publisher import event_publisher

logger = logging.getLogger(__name__)


def run_async(coro):
    """Helper to run async functions in sync context"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_character_mail(self, character_id: int):
    """
    Sync mail for a character from ESI

    Args:
        character_id: EVE character ID
    """
    db: Session = SessionLocal()

    try:
        # Find valid token
        now = datetime.now(timezone.utc)
        token = db.query(EveToken).filter(
            and_(
                EveToken.character_id == character_id,
                EveToken.expires_at > now,
                EveToken.scope.contains("esi-mail.read_mail.v1"),
            )
        ).first()

        if not token:
            logger.warning(f"No valid token found for character {character_id}")
            return {"success": False, "error": "No valid token found"}

        from app.core.encryption import encryption
        access_token = encryption.decrypt(token.access_token_encrypted)

        # Get character
        character = db.query(Character).filter(
            Character.character_id == character_id
        ).first()

        if not character:
            logger.warning(f"Character {character_id} not found")
            return {"success": False, "error": "Character not found"}

        # Fetch mail headers
        mail_headers = run_async(
            esi_client.request(
                "GET",
                f"/characters/{character_id}/mail/",
                access_token=access_token,
            )
        )

        logger.info(f"Fetched {len(mail_headers)} mail headers for character {character_id}")

        synced_count = 0

        for header in mail_headers:
            mail_id = header.get("mail_id")

            # Check if mail already exists
            existing = db.query(Mail).filter(
                and_(
                    Mail.mail_id == mail_id,
                    Mail.character_id == character.id,
                )
            ).first()

            if existing:
                # Update is_read status
                if header.get("is_read") != existing.is_read:
                    existing.is_read = header.get("is_read", False)
                continue

            # Fetch full mail body
            try:
                mail_data = run_async(
                    esi_client.request(
                        "GET",
                        f"/characters/{character_id}/mail/{mail_id}/",
                        access_token=access_token,
                    )
                )
            except ESIError as e:
                logger.warning(f"Failed to fetch mail {mail_id}: {e}")
                continue

            # Create mail record
            mail = Mail(
                mail_id=mail_id,
                character_id=character.id,
                from_id=header.get("from"),
                subject=header.get("subject", ""),
                body=mail_data.get("body", ""),
                timestamp=datetime.fromisoformat(header.get("timestamp", "").replace("Z", "+00:00")),
                is_read=header.get("is_read", False),
                recipients=header.get("recipients", []),
                labels=header.get("labels", []),
            )

            db.add(mail)
            synced_count += 1

            # Publish WebSocket event for new mail
            try:
                event_publisher.publish_mail(
                    character_id=character_id,
                    mail_data={
                        "mail_id": mail_id,
                        "from_id": header.get("from"),
                        "subject": header.get("subject", ""),
                        "timestamp": header.get("timestamp"),
                        "is_read": False,
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to publish WebSocket event for mail {mail_id}: {e}")

        db.commit()

        # Sync mail labels
        try:
            labels_data = run_async(
                esi_client.request(
                    "GET",
                    f"/characters/{character_id}/mail/labels/",
                    access_token=access_token,
                )
            )

            # Update or create labels
            for label_data in labels_data.get("labels", []):
                label_id = label_data.get("label_id")

                existing_label = db.query(MailLabel).filter(
                    and_(
                        MailLabel.character_id == character.id,
                        MailLabel.label_id == label_id,
                    )
                ).first()

                if existing_label:
                    existing_label.name = label_data.get("name", "")
                    existing_label.color = label_data.get("color", "#FFFFFF")
                    existing_label.unread_count = label_data.get("unread_count", 0)
                else:
                    label = MailLabel(
                        character_id=character.id,
                        label_id=label_id,
                        name=label_data.get("name", ""),
                        color=label_data.get("color", "#FFFFFF"),
                        unread_count=label_data.get("unread_count", 0),
                    )
                    db.add(label)

            db.commit()

        except ESIError as e:
            logger.warning(f"Failed to sync mail labels: {e}")

        # Sync mailing lists
        try:
            lists_data = run_async(
                esi_client.request(
                    "GET",
                    f"/characters/{character_id}/mail/lists/",
                    access_token=access_token,
                )
            )

            for list_data in lists_data:
                mailing_list_id = list_data.get("mailing_list_id")

                existing_list = db.query(MailingList).filter(
                    and_(
                        MailingList.character_id == character.id,
                        MailingList.mailing_list_id == mailing_list_id,
                    )
                ).first()

                if not existing_list:
                    mailing_list = MailingList(
                        character_id=character.id,
                        mailing_list_id=mailing_list_id,
                        name=list_data.get("name", ""),
                    )
                    db.add(mailing_list)

            db.commit()

        except ESIError as e:
            logger.warning(f"Failed to sync mailing lists: {e}")

        logger.info(f"Synced {synced_count} mails for character {character_id}")
        return {"success": True, "synced": synced_count}

    except ESIRateLimitError as e:
        logger.warning(f"Rate limit hit for character {character_id}: {e}")
        raise self.retry(exc=e)
    except Exception as e:
        logger.error(f"Error syncing mail for character {character_id}: {e}")
        db.rollback()
        raise self.retry(exc=e)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_mail_task(
    self,
    character_id: int,
    subject: str,
    body: str,
    recipients: list,
    approved_cost: int = None,
):
    """
    Send in-game mail via ESI

    Args:
        character_id: EVE character ID
        subject: Mail subject
        body: Mail body
        recipients: List of recipient dicts [{recipient_id, recipient_type}]
        approved_cost: Approved ISK cost (for CSPA charge)
    """
    db: Session = SessionLocal()

    try:
        # Find valid token
        now = datetime.now(timezone.utc)
        token = db.query(EveToken).filter(
            and_(
                EveToken.character_id == character_id,
                EveToken.expires_at > now,
                EveToken.scope.contains("esi-mail.send_mail.v1"),
            )
        ).first()

        if not token:
            logger.warning(f"No valid token found for character {character_id}")
            return {"success": False, "error": "No valid token found"}

        from app.core.encryption import encryption
        access_token = encryption.decrypt(token.access_token_encrypted)

        # Prepare mail data
        mail_data = {
            "approved_cost": approved_cost,
            "body": body,
            "recipients": recipients,
            "subject": subject,
        }

        # Send mail via ESI
        response = run_async(
            esi_client.request(
                "POST",
                f"/characters/{character_id}/mail/",
                access_token=access_token,
                params=mail_data,
            )
        )

        logger.info(f"Sent mail from character {character_id}: {subject}")
        return {"success": True, "mail_id": response}

    except ESIError as e:
        logger.error(f"Failed to send mail: {e}")
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Error sending mail: {e}")
        db.rollback()
        raise self.retry(exc=e)
    finally:
        db.close()
