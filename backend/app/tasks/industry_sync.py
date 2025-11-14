"""
Industry sync tasks

Syncs character industry jobs and facilities from ESI
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
from app.models.industry import IndustryJob, IndustryFacility
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
def sync_character_industry(self, character_id: int):
    """
    Sync industry jobs and facilities for a character from ESI

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
                EveToken.scope.contains("esi-industry.read_character_jobs.v1"),
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

        # Fetch industry jobs
        jobs_data = run_async(
            esi_client.request(
                "GET",
                f"/characters/{character_id}/industry/jobs/",
                access_token=access_token,
            )
        )

        logger.info(f"Fetched {len(jobs_data)} industry jobs for character {character_id}")

        synced_jobs = 0

        for job_data in jobs_data:
            job_id = job_data.get("job_id")

            # Check if job already exists
            existing = db.query(IndustryJob).filter(
                IndustryJob.job_id == job_id
            ).first()

            if existing:
                # Update status and completion
                existing.status = job_data.get("status", "unknown")
                existing.completed_date = (
                    datetime.fromisoformat(job_data.get("completed_date", "").replace("Z", "+00:00"))
                    if job_data.get("completed_date")
                    else None
                )
                existing.completed_character_id = job_data.get("completed_character_id")
                existing.successful_runs = job_data.get("successful_runs")
            else:
                # Create new job
                job = IndustryJob(
                    character_id=character.id,
                    job_id=job_id,
                    installer_id=job_data.get("installer_id"),
                    facility_id=job_data.get("facility_id"),
                    location_id=job_data.get("location_id"),
                    activity_id=job_data.get("activity_id"),
                    blueprint_id=job_data.get("blueprint_id"),
                    blueprint_type_id=job_data.get("blueprint_type_id"),
                    blueprint_location_id=job_data.get("blueprint_location_id"),
                    output_location_id=job_data.get("output_location_id"),
                    product_type_id=job_data.get("product_type_id"),
                    runs=job_data.get("runs", 1),
                    licensed_runs=job_data.get("licensed_runs"),
                    cost=job_data.get("cost"),
                    probability=job_data.get("probability"),
                    status=job_data.get("status", "unknown"),
                    start_date=datetime.fromisoformat(
                        job_data.get("start_date", "").replace("Z", "+00:00")
                    ),
                    end_date=datetime.fromisoformat(
                        job_data.get("end_date", "").replace("Z", "+00:00")
                    ),
                    pause_date=(
                        datetime.fromisoformat(job_data.get("pause_date", "").replace("Z", "+00:00"))
                        if job_data.get("pause_date")
                        else None
                    ),
                    completed_date=(
                        datetime.fromisoformat(job_data.get("completed_date", "").replace("Z", "+00:00"))
                        if job_data.get("completed_date")
                        else None
                    ),
                    completed_character_id=job_data.get("completed_character_id"),
                    successful_runs=job_data.get("successful_runs"),
                )
                db.add(job)
                synced_jobs += 1

        db.commit()

        # Publish WebSocket event
        event_publisher.publish(
            "industry",
            EventType.INDUSTRY_JOB_UPDATE,
            {
                "character_id": character_id,
                "total_jobs": len(jobs_data),
                "synced": synced_jobs,
            },
        )

        logger.info(f"Synced {synced_jobs} new industry jobs for character {character_id}")
        return {"success": True, "synced": synced_jobs}

    except ESIRateLimitError as e:
        logger.warning(f"Rate limit hit for character {character_id}: {e}")
        raise self.retry(exc=e)
    except Exception as e:
        logger.error(f"Error syncing industry for character {character_id}: {e}")
        db.rollback()
        raise self.retry(exc=e)
    finally:
        db.close()
