"""
Clone sync tasks

Syncs character jump clones and implants from ESI
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
from app.models.clone import Clone, ActiveImplant
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
def sync_character_clones(self, character_id: int):
    """
    Sync jump clones and implants for a character from ESI

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
                EveToken.scope.contains("esi-clones.read_clones.v1"),
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

        # Fetch clones
        clones_data = run_async(
            esi_client.request(
                "GET",
                f"/characters/{character_id}/clones/",
                access_token=access_token,
            )
        )

        logger.info(f"Fetched clones for character {character_id}")

        # Clear existing clones and re-add
        db.query(Clone).filter(Clone.character_id == character.id).delete()

        jump_clones = clones_data.get("jump_clones", [])
        synced_count = 0

        for clone_data in jump_clones:
            clone = Clone(
                character_id=character.id,
                jump_clone_id=clone_data.get("jump_clone_id"),
                name=clone_data.get("name"),
                location_id=clone_data.get("location_id"),
                location_type=clone_data.get("location_type"),
                implants=clone_data.get("implants", []),
            )
            db.add(clone)
            synced_count += 1

        # Fetch implants in active clone
        implants_data = run_async(
            esi_client.request(
                "GET",
                f"/characters/{character_id}/implants/",
                access_token=access_token,
            )
        )

        # Clear existing active implants and re-add
        db.query(ActiveImplant).filter(ActiveImplant.character_id == character.id).delete()

        for idx, implant_type_id in enumerate(implants_data):
            implant = ActiveImplant(
                character_id=character.id,
                type_id=implant_type_id,
                slot=idx + 1,  # Implant slots are 1-10
            )
            db.add(implant)

        db.commit()

        # Publish WebSocket event
        event_publisher.publish(
            "clones",
            EventType.CLONE_UPDATE,
            {
                "character_id": character_id,
                "total_clones": len(jump_clones),
                "active_implants": len(implants_data),
            },
        )

        logger.info(f"Synced {synced_count} clones and {len(implants_data)} implants for character {character_id}")
        return {"success": True, "clones": synced_count, "implants": len(implants_data)}

    except ESIRateLimitError as e:
        logger.warning(f"Rate limit hit for character {character_id}: {e}")
        raise self.retry(exc=e)
    except Exception as e:
        logger.error(f"Error syncing clones for character {character_id}: {e}")
        db.rollback()
        raise self.retry(exc=e)
    finally:
        db.close()
