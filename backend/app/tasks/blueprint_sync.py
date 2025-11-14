"""
Blueprint sync tasks

Syncs character blueprints from ESI
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
from app.models.blueprint import Blueprint
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
def sync_character_blueprints(self, character_id: int):
    """
    Sync blueprints for a character from ESI

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
                EveToken.scope.contains("esi-characters.read_blueprints.v1"),
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

        # Fetch blueprints
        blueprints_data = run_async(
            esi_client.request(
                "GET",
                f"/characters/{character_id}/blueprints/",
                access_token=access_token,
            )
        )

        logger.info(f"Fetched {len(blueprints_data)} blueprints for character {character_id}")

        synced_count = 0

        for bp_data in blueprints_data:
            item_id = bp_data.get("item_id")

            # Check if blueprint already exists
            existing = db.query(Blueprint).filter(
                Blueprint.item_id == item_id
            ).first()

            if existing:
                # Update blueprint stats
                existing.time_efficiency = bp_data.get("time_efficiency", 0)
                existing.material_efficiency = bp_data.get("material_efficiency", 0)
                existing.runs = bp_data.get("runs", -1)
                existing.quantity = bp_data.get("quantity", 1)
                existing.location_id = bp_data.get("location_id")
                existing.location_flag = bp_data.get("location_flag", "Hangar")
            else:
                # Create new blueprint
                blueprint = Blueprint(
                    character_id=character.id,
                    item_id=item_id,
                    type_id=bp_data.get("type_id"),
                    location_id=bp_data.get("location_id"),
                    location_flag=bp_data.get("location_flag", "Hangar"),
                    quantity=bp_data.get("quantity", 1),
                    time_efficiency=bp_data.get("time_efficiency", 0),
                    material_efficiency=bp_data.get("material_efficiency", 0),
                    runs=bp_data.get("runs", -1),
                )
                db.add(blueprint)
                synced_count += 1

        db.commit()

        # Publish WebSocket event
        event_publisher.publish(
            "blueprints",
            EventType.BLUEPRINT_UPDATE,
            {
                "character_id": character_id,
                "total_blueprints": len(blueprints_data),
                "synced": synced_count,
            },
        )

        logger.info(f"Synced {synced_count} new blueprints for character {character_id}")
        return {"success": True, "synced": synced_count}

    except ESIRateLimitError as e:
        logger.warning(f"Rate limit hit for character {character_id}: {e}")
        raise self.retry(exc=e)
    except Exception as e:
        logger.error(f"Error syncing blueprints for character {character_id}: {e}")
        db.rollback()
        raise self.retry(exc=e)
    finally:
        db.close()
