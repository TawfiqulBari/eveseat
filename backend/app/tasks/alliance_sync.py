"""
Alliance sync tasks
"""
import asyncio
from celery import Task

from app.core.celery_app import celery_app
from app.core.database import get_db_session
from app.models.alliance import Alliance, AllianceCorporation
from app.services.esi_client import ESIClient
from app.websockets.publisher import publish_event
from app.websockets.events import EventType
from app.core.logger import logger


def run_async(coro):
    """Helper to run async code in Celery tasks"""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_alliance_data(self: Task, alliance_id: int):
    """Sync alliance data from ESI"""
    try:
        db = next(get_db_session())
        esi_client = ESIClient()

        # Fetch alliance info from ESI
        alliance_data = run_async(
            esi_client.request("GET", f"/alliances/{alliance_id}/")
        )

        # Update or create alliance
        alliance = db.query(Alliance).filter(Alliance.alliance_id == alliance_id).first()

        if alliance:
            alliance.alliance_name = alliance_data.get('name', '')
            alliance.ticker = alliance_data.get('ticker', '')
            alliance.executor_corporation_id = alliance_data.get('executor_corporation_id')
            alliance.date_founded = alliance_data.get('date_founded')
            alliance.synced_at = datetime.utcnow()
        else:
            alliance = Alliance(
                alliance_id=alliance_id,
                alliance_name=alliance_data.get('name', ''),
                ticker=alliance_data.get('ticker', ''),
                executor_corporation_id=alliance_data.get('executor_corporation_id'),
                date_founded=alliance_data.get('date_founded'),
            )
            db.add(alliance)

        db.commit()

        # Publish WebSocket event
        publish_event(EventType.ALLIANCE_UPDATE, {
            "alliance_id": alliance_id,
            "alliance_name": alliance.alliance_name
        })

        logger.info(f"Synced alliance {alliance_id}")

    except Exception as e:
        logger.error(f"Failed to sync alliance {alliance_id}: {str(e)}")
        db.rollback()
        raise self.retry(exc=e)
    finally:
        db.close()
