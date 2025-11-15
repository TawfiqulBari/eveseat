"""
Incursion sync tasks
"""
import asyncio
from celery import Task
from datetime import datetime

from app.core.celery_app import celery_app
from app.core.database import get_db_session
from app.models.incursion import Incursion, IncursionStatistics, IncursionParticipation
from app.models.character import Character
from app.services.esi_client import ESIClient
from app.websockets.publisher import publish_event
from app.websockets.events import EventType
from app.core.logger import logger


def run_async(coro):
    """Helper to run async code in Celery tasks"""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_incursions_data(self: Task):
    """Sync all active incursions from ESI"""
    try:
        db = next(get_db_session())
        esi_client = ESIClient()

        # Fetch all incursions from ESI (public data)
        incursions_data = run_async(
            esi_client.request("GET", "/incursions/")
        )

        # Mark all incursions as inactive first
        db.query(Incursion).update({"is_active": False})

        synced_count = 0
        for inc_data in incursions_data:
            constellation_id = inc_data.get('constellation_id')

            # Update or create incursion
            incursion = db.query(Incursion).filter(
                Incursion.constellation_id == constellation_id
            ).first()

            if incursion:
                incursion.state = inc_data.get('state', 'established')
                incursion.staging_solar_system_id = inc_data.get('staging_solar_system_id')
                incursion.influence = inc_data.get('influence', 0.0)
                incursion.has_boss = inc_data.get('has_boss', False)
                incursion.faction_id = inc_data.get('faction_id', 500019)  # Default to Sansha
                incursion.type = inc_data.get('type', 'Incursion')
                incursion.is_active = True
                incursion.synced_at = datetime.utcnow()
            else:
                incursion = Incursion(
                    constellation_id=constellation_id,
                    state=inc_data.get('state', 'established'),
                    staging_solar_system_id=inc_data.get('staging_solar_system_id'),
                    influence=inc_data.get('influence', 0.0),
                    has_boss=inc_data.get('has_boss', False),
                    faction_id=inc_data.get('faction_id', 500019),
                    type=inc_data.get('type', 'Incursion'),
                    is_active=True,
                )
                db.add(incursion)

                # Publish new incursion event
                publish_event(EventType.INCURSION_NEW, {
                    "constellation_id": constellation_id,
                    "state": inc_data.get('state', 'established'),
                    "staging_system": inc_data.get('staging_solar_system_id'),
                })

            synced_count += 1

        db.commit()

        # Publish general update event
        publish_event(EventType.INCURSION_UPDATE, {
            "active_count": synced_count,
            "total_synced": synced_count
        })

        logger.info(f"Synced {synced_count} active incursions")

    except Exception as e:
        logger.error(f"Failed to sync incursions: {str(e)}")
        db.rollback()
        raise self.retry(exc=e)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def update_incursion_statistics(self: Task, constellation_id: int):
    """Update statistics for a specific incursion"""
    try:
        db = next(get_db_session())

        incursion = db.query(Incursion).filter(
            Incursion.constellation_id == constellation_id
        ).first()

        if not incursion:
            logger.warning(f"Incursion in constellation {constellation_id} not found")
            return

        # Calculate statistics from participation records
        participations = db.query(IncursionParticipation).filter(
            IncursionParticipation.incursion_id == incursion.id
        ).all()

        total_sites = len(participations)
        total_isk = sum(p.isk_earned for p in participations)
        unique_participants = len(set(p.character_id for p in participations))

        # Update or create statistics
        stats = db.query(IncursionStatistics).filter(
            IncursionStatistics.incursion_id == incursion.id
        ).first()

        if stats:
            stats.total_sites_completed = total_sites
            stats.total_isk_earned = total_isk
            stats.unique_participants = unique_participants
            stats.synced_at = datetime.utcnow()
        else:
            stats = IncursionStatistics(
                incursion_id=incursion.id,
                total_sites_completed=total_sites,
                total_isk_earned=total_isk,
                unique_participants=unique_participants,
            )
            db.add(stats)

        db.commit()

        logger.info(f"Updated statistics for incursion {constellation_id}")

    except Exception as e:
        logger.error(f"Failed to update incursion statistics: {str(e)}")
        db.rollback()
        raise self.retry(exc=e)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def record_incursion_participation(
    self: Task,
    character_id: int,
    constellation_id: int,
    site_type: str,
    isk_earned: int
):
    """Record a character's participation in an incursion site"""
    try:
        db = next(get_db_session())

        character = db.query(Character).filter(Character.id == character_id).first()
        if not character:
            logger.warning(f"Character {character_id} not found")
            return

        incursion = db.query(Incursion).filter(
            Incursion.constellation_id == constellation_id,
            Incursion.is_active == True
        ).first()

        if not incursion:
            logger.warning(f"Active incursion in constellation {constellation_id} not found")
            return

        # Record participation
        participation = IncursionParticipation(
            incursion_id=incursion.id,
            character_id=character.id,
            site_type=site_type,
            isk_earned=isk_earned,
        )
        db.add(participation)
        db.commit()

        # Publish event
        publish_event(EventType.INCURSION_PARTICIPATION, {
            "character_id": character.character_id,
            "constellation_id": constellation_id,
            "site_type": site_type,
            "isk_earned": isk_earned,
        })

        logger.info(f"Recorded incursion participation for character {character_id}")

    except Exception as e:
        logger.error(f"Failed to record incursion participation: {str(e)}")
        db.rollback()
        raise self.retry(exc=e)
    finally:
        db.close()
