"""
Contact sync tasks

Syncs character contacts from ESI
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
from app.models.contact import Contact, ContactLabel
from app.services.esi_client import esi_client, ESIError, ESIRateLimitError

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
def sync_character_contacts(self, character_id: int):
    """
    Sync contacts for a character from ESI

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
                EveToken.scope.contains("esi-characters.read_contacts.v1"),
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

        # Fetch contacts
        contacts_data = run_async(
            esi_client.request(
                "GET",
                f"/characters/{character_id}/contacts/",
                access_token=access_token,
            )
        )

        logger.info(f"Fetched {len(contacts_data)} contacts for character {character_id}")

        synced_count = 0

        # Track existing contact IDs to detect deletions
        existing_contact_ids = {
            c.contact_id for c in db.query(Contact).filter(Contact.character_id == character.id).all()
        }
        fetched_contact_ids = set()

        for contact_data in contacts_data:
            contact_id = contact_data.get("contact_id")
            fetched_contact_ids.add(contact_id)

            # Check if contact already exists
            existing = db.query(Contact).filter(
                and_(
                    Contact.contact_id == contact_id,
                    Contact.character_id == character.id,
                )
            ).first()

            if existing:
                # Update existing contact
                existing.standing = contact_data.get("standing", 0.0)
                existing.contact_type = contact_data.get("contact_type", "character")
                existing.is_watched = contact_data.get("is_watched", False)
                existing.is_blocked = contact_data.get("is_blocked", False)
                existing.label_ids = contact_data.get("label_ids", [])
            else:
                # Create new contact
                contact = Contact(
                    character_id=character.id,
                    contact_id=contact_id,
                    contact_type=contact_data.get("contact_type", "character"),
                    standing=contact_data.get("standing", 0.0),
                    is_watched=contact_data.get("is_watched", False),
                    is_blocked=contact_data.get("is_blocked", False),
                    label_ids=contact_data.get("label_ids", []),
                )
                db.add(contact)
                synced_count += 1

        # Delete contacts that no longer exist in ESI
        deleted_contact_ids = existing_contact_ids - fetched_contact_ids
        if deleted_contact_ids:
            db.query(Contact).filter(
                and_(
                    Contact.character_id == character.id,
                    Contact.contact_id.in_(deleted_contact_ids),
                )
            ).delete(synchronize_session=False)

        db.commit()

        # Sync contact labels
        try:
            labels_data = run_async(
                esi_client.request(
                    "GET",
                    f"/characters/{character_id}/contacts/labels/",
                    access_token=access_token,
                )
            )

            # Update or create labels
            for label_data in labels_data:
                label_id = label_data.get("label_id")

                existing_label = db.query(ContactLabel).filter(
                    and_(
                        ContactLabel.character_id == character.id,
                        ContactLabel.label_id == label_id,
                    )
                ).first()

                if existing_label:
                    existing_label.name = label_data.get("label_name", "")
                else:
                    label = ContactLabel(
                        character_id=character.id,
                        label_id=label_id,
                        name=label_data.get("label_name", ""),
                    )
                    db.add(label)

            db.commit()

        except ESIError as e:
            logger.warning(f"Failed to sync contact labels: {e}")

        logger.info(f"Synced {synced_count} new contacts for character {character_id}")
        return {"success": True, "synced": synced_count, "deleted": len(deleted_contact_ids)}

    except ESIRateLimitError as e:
        logger.warning(f"Rate limit hit for character {character_id}: {e}")
        raise self.retry(exc=e)
    except Exception as e:
        logger.error(f"Error syncing contacts for character {character_id}: {e}")
        db.rollback()
        raise self.retry(exc=e)
    finally:
        db.close()
