"""
Celery tasks for syncing moon extractions and mining ledger from ESI
"""
import asyncio
from datetime import datetime
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.corporation import Corporation
from app.models.moon import MoonExtraction, MiningLedger
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
def sync_moon_extractions(self, corporation_id: int):
    """
    Sync moon extractions from ESI

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

        # Get character token
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

        # Fetch moon extractions from ESI
        esi_client = ESIClient()
        extractions_data = run_async(
            esi_client.request(
                "GET",
                f"/corporation/{corporation.corporation_id}/mining/extractions/",
                access_token=access_token,
            )
        )

        if not extractions_data:
            logger.info(f"No moon extractions found for corporation {corporation_id}")
            return

        # Clear existing extractions and re-add
        db.query(MoonExtraction).filter(MoonExtraction.corporation_id == corporation.id).delete()
        db.commit()

        for extraction_data in extractions_data:
            extraction = MoonExtraction(
                corporation_id=corporation.id,
                structure_id=extraction_data.get("structure_id"),
                moon_id=extraction_data.get("moon_id"),
                chunk_arrival_time=extraction_data.get("chunk_arrival_time"),
                extraction_start_time=extraction_data.get("extraction_start_time"),
                natural_decay_time=extraction_data.get("natural_decay_time"),
                status="started",  # Default status
                synced_at=datetime.utcnow(),
            )
            db.add(extraction)

        db.commit()

        # Publish WebSocket event
        publish_event(
            EventType.MOON_EXTRACTION_UPDATE,
            {
                "corporation_id": corporation_id,
                "count": len(extractions_data),
            },
        )

        logger.info(f"Synced {len(extractions_data)} moon extractions for corporation {corporation_id}")

    except Exception as exc:
        logger.error(f"Error syncing moon extractions for corporation {corporation_id}: {exc}")
        db.rollback()
        raise self.retry(exc=exc)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_mining_ledger(self, corporation_id: int):
    """
    Sync corporation mining ledger from ESI

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

        # Get character token
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

        # Fetch mining ledger from ESI
        esi_client = ESIClient()
        ledger_data = run_async(
            esi_client.request(
                "GET",
                f"/corporation/{corporation.corporation_id}/mining/observers/",
                access_token=access_token,
            )
        )

        if not ledger_data:
            logger.info(f"No mining ledger found for corporation {corporation_id}")
            return

        # Process each observer
        for observer in ledger_data:
            observer_id = observer.get("observer_id")

            # Fetch observer details
            observer_details = run_async(
                esi_client.request(
                    "GET",
                    f"/corporation/{corporation.corporation_id}/mining/observers/{observer_id}/",
                    access_token=access_token,
                )
            )

            if observer_details:
                for entry_data in observer_details:
                    # Check if entry already exists
                    existing = db.query(MiningLedger).filter(
                        MiningLedger.corporation_id == corporation.id,
                        MiningLedger.character_id == entry_data.get("character_id"),
                        MiningLedger.date == entry_data.get("last_updated"),
                        MiningLedger.type_id == entry_data.get("type_id"),
                    ).first()

                    if not existing:
                        entry = MiningLedger(
                            corporation_id=corporation.id,
                            character_id=entry_data.get("character_id"),
                            date=entry_data.get("last_updated"),
                            type_id=entry_data.get("type_id"),
                            quantity=entry_data.get("quantity"),
                            system_id=observer.get("observer_type") if "observer_type" in observer else 0,
                        )
                        db.add(entry)

        db.commit()

        # Publish WebSocket event
        publish_event(
            EventType.MINING_LEDGER_UPDATE,
            {
                "corporation_id": corporation_id,
            },
        )

        logger.info(f"Synced mining ledger for corporation {corporation_id}")

    except Exception as exc:
        logger.error(f"Error syncing mining ledger for corporation {corporation_id}: {exc}")
        db.rollback()
        raise self.retry(exc=exc)
    finally:
        db.close()
