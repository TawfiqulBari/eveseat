"""
Celery tasks for syncing sovereignty data from ESI
"""
import asyncio
from datetime import datetime
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.sovereignty import SystemSovereignty, SovereigntyStructure, SovereigntyCampaign
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
def sync_sovereignty_data(self):
    """
    Sync sovereignty data from ESI (public endpoint, no auth required)
    """
    db = SessionLocal()
    try:
        esi_client = ESIClient()

        # Fetch sovereignty map
        sov_map = run_async(
            esi_client.request("GET", "/sovereignty/map/")
        )

        if sov_map:
            # Clear existing sovereignty data
            db.query(SystemSovereignty).delete()
            db.commit()

            for sov_data in sov_map:
                sov = SystemSovereignty(
                    system_id=sov_data.get("system_id"),
                    alliance_id=sov_data.get("alliance_id"),
                    corporation_id=sov_data.get("corporation_id"),
                    faction_id=sov_data.get("faction_id"),
                    synced_at=datetime.utcnow(),
                )
                db.add(sov)

            db.commit()
            logger.info(f"Synced {len(sov_map)} system sovereignty entries")

        # Fetch sovereignty structures
        sov_structures = run_async(
            esi_client.request("GET", "/sovereignty/structures/")
        )

        if sov_structures:
            # Clear existing structures
            db.query(SovereigntyStructure).delete()
            db.commit()

            for structure_data in sov_structures:
                structure = SovereigntyStructure(
                    structure_id=structure_data.get("structure_id"),
                    system_id=structure_data.get("solar_system_id"),
                    structure_type_id=structure_data.get("structure_type_id"),
                    alliance_id=structure_data.get("alliance_id"),
                    vulnerable_start_time=structure_data.get("vulnerable_start_time"),
                    vulnerable_end_time=structure_data.get("vulnerable_end_time"),
                    vulnerability_occupancy_level=structure_data.get("vulnerability_occupancy_level"),
                    synced_at=datetime.utcnow(),
                )
                db.add(structure)

            db.commit()
            logger.info(f"Synced {len(sov_structures)} sovereignty structures")

        # Fetch sovereignty campaigns
        sov_campaigns = run_async(
            esi_client.request("GET", "/sovereignty/campaigns/")
        )

        if sov_campaigns:
            # Clear existing campaigns
            db.query(SovereigntyCampaign).delete()
            db.commit()

            for campaign_data in sov_campaigns:
                # Extract participants
                participants = campaign_data.get("participants", [])
                defender_score = 0
                attackers_score = 0

                for participant in participants:
                    score = participant.get("score", 0)
                    if participant.get("alliance_id") == campaign_data.get("defender_id"):
                        defender_score = score
                    else:
                        attackers_score += score

                campaign = SovereigntyCampaign(
                    campaign_id=campaign_data.get("campaign_id"),
                    system_id=campaign_data.get("solar_system_id"),
                    constellation_id=campaign_data.get("constellation_id"),
                    structure_id=campaign_data.get("structure_id"),
                    event_type=campaign_data.get("event_type"),
                    defender_id=campaign_data.get("defender_id"),
                    defender_score=defender_score,
                    attackers_score=attackers_score,
                    start_time=campaign_data.get("start_time"),
                    synced_at=datetime.utcnow(),
                )
                db.add(campaign)

            db.commit()
            logger.info(f"Synced {len(sov_campaigns)} sovereignty campaigns")

        # Publish WebSocket event
        publish_event(
            EventType.SOVEREIGNTY_UPDATE,
            {
                "systems": len(sov_map) if sov_map else 0,
                "structures": len(sov_structures) if sov_structures else 0,
                "campaigns": len(sov_campaigns) if sov_campaigns else 0,
            },
        )

        logger.info("Sovereignty sync completed")

    except Exception as exc:
        logger.error(f"Error syncing sovereignty data: {exc}")
        db.rollback()
        raise self.retry(exc=exc)
    finally:
        db.close()
