"""
Celery tasks for syncing corporation structures from ESI
"""
import asyncio
from datetime import datetime
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.corporation import Corporation
from app.models.structure import Structure, StructureVulnerability, StructureService
from app.services.esi_client import ESIClient
from app.core.logging import logger
from app.websockets.publisher import publish_event
from app.websockets.events import EventType


def run_async(coro):
    """Helper to run async code in sync context"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_corporation_structures(self, corporation_id: int):
    """
    Sync corporation structures from ESI

    Args:
        corporation_id: Corporation ID
    """
    db = SessionLocal()
    try:
        # Get corporation
        corporation = db.query(Corporation).filter(
            Corporation.id == corporation_id
        ).first()

        if not corporation:
            logger.error(f"Corporation {corporation_id} not found")
            return

        # Find a character token with required scopes
        # For simplicity, we'll assume the corporation has a director with tokens
        # In production, you'd need to handle token selection more carefully
        from app.models.character import Character
        from app.models.eve_token import EveToken

        character = db.query(Character).filter(
            Character.corporation_id == corporation.corporation_id
        ).first()

        if not character:
            logger.warning(f"No character found for corporation {corporation_id}")
            return

        token = db.query(EveToken).filter(EveToken.character_id == character.id).first()
        if not token:
            logger.warning(f"No token found for character {character.id}")
            return

        access_token = token.access_token

        # Fetch structures from ESI
        esi_client = ESIClient()
        structures_data = run_async(
            esi_client.request(
                "GET",
                f"/corporations/{corporation.corporation_id}/structures/",
                access_token=access_token,
            )
        )

        if not structures_data:
            logger.info(f"No structures found for corporation {corporation_id}")
            return

        # Clear existing structures and re-add
        db.query(Structure).filter(Structure.corporation_id == corporation.id).delete()
        db.commit()

        for structure_data in structures_data:
            structure = Structure(
                corporation_id=corporation.id,
                structure_id=structure_data.get("structure_id"),
                name=structure_data.get("name"),
                type_id=structure_data.get("type_id"),
                system_id=structure_data.get("system_id"),
                position_x=structure_data.get("position", {}).get("x"),
                position_y=structure_data.get("position", {}).get("y"),
                position_z=structure_data.get("position", {}).get("z"),
                state=structure_data.get("state"),
                state_timer_start=structure_data.get("state_timer_start"),
                state_timer_end=structure_data.get("state_timer_end"),
                unanchors_at=structure_data.get("unanchors_at"),
                fuel_expires=structure_data.get("fuel_expires"),
                next_reinforce_hour=structure_data.get("next_reinforce_hour"),
                next_reinforce_day=structure_data.get("next_reinforce_weekday"),
                services=structure_data.get("services", []),
                profile_id=structure_data.get("profile_id"),
                reinforce_hour=structure_data.get("reinforce_hour"),
                synced_at=datetime.utcnow(),
            )
            db.add(structure)

        db.commit()

        # Publish WebSocket event
        publish_event(
            EventType.STRUCTURE_UPDATE,
            {
                "corporation_id": corporation_id,
                "count": len(structures_data),
            },
        )

        logger.info(f"Synced {len(structures_data)} structures for corporation {corporation_id}")

    except Exception as exc:
        logger.error(f"Error syncing structures for corporation {corporation_id}: {exc}")
        db.rollback()
        raise self.retry(exc=exc)
    finally:
        db.close()
