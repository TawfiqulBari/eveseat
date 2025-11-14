"""
Loyalty Points sync tasks

Syncs character loyalty points from ESI
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
from app.models.loyalty import LoyaltyPoint
from app.services.esi_client import esi_client, ESIError, ESIRateLimitError
from app.websockets.events import EventType
from app.websockets.publisher import EventPublisher

logger = logging.getLogger(__name__)
event_publisher = EventPublisher()


def run_async(coro):
    """Helper to run async functions in sync context"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_character_loyalty(self, character_id: int):
    """
    Sync loyalty points for a character from ESI

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
                EveToken.scope.contains("esi-characters.read_loyalty.v1"),
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

        # Fetch loyalty points
        lp_data = run_async(
            esi_client.request(
                "GET",
                f"/characters/{character_id}/loyalty/points/",
                access_token=access_token,
            )
        )

        logger.info(f"Fetched {len(lp_data)} LP entries for character {character_id}")

        synced_count = 0

        for lp_entry in lp_data:
            corporation_id = lp_entry.get("corporation_id")
            loyalty_points = lp_entry.get("loyalty_points", 0)

            # Check if LP entry already exists
            existing = db.query(LoyaltyPoint).filter(
                and_(
                    LoyaltyPoint.character_id == character.id,
                    LoyaltyPoint.corporation_id == corporation_id,
                )
            ).first()

            if existing:
                # Update loyalty points
                existing.loyalty_points = loyalty_points
            else:
                # Create new entry
                lp = LoyaltyPoint(
                    character_id=character.id,
                    corporation_id=corporation_id,
                    loyalty_points=loyalty_points,
                )
                db.add(lp)
                synced_count += 1

        db.commit()

        # Publish WebSocket event
        event_publisher.publish(
            "loyalty",
            EventType.LOYALTY_UPDATE,
            {
                "character_id": character_id,
                "total_corporations": len(lp_data),
                "synced": synced_count,
            },
        )

        logger.info(f"Synced {synced_count} new LP entries for character {character_id}")
        return {"success": True, "synced": synced_count}

    except ESIRateLimitError as e:
        logger.warning(f"Rate limit hit for character {character_id}: {e}")
        raise self.retry(exc=e)
    except Exception as e:
        logger.error(f"Error syncing loyalty for character {character_id}: {e}")
        db.rollback()
        raise self.retry(exc=e)
    finally:
        db.close()
