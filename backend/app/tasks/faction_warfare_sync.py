"""
Faction Warfare sync tasks
"""
import asyncio
from celery import Task
from datetime import datetime

from app.core.celery_app import celery_app
from app.core.database import get_db_session
from app.models.faction_warfare import (
    FactionWarfareSystem,
    FactionWarfareStatistics,
    CharacterFactionWarfare,
    FactionWarfareLeaderboard,
    FactionWarfareSystemHistory
)
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
def sync_faction_warfare_systems(self: Task):
    """Sync all faction warfare systems from ESI"""
    try:
        db = next(get_db_session())
        esi_client = ESIClient()

        # Fetch all FW systems from ESI (public data)
        systems_data = run_async(
            esi_client.request("GET", "/fw/systems/")
        )

        synced_count = 0
        for sys_data in systems_data:
            solar_system_id = sys_data.get('solar_system_id')

            # Update or create FW system
            fw_system = db.query(FactionWarfareSystem).filter(
                FactionWarfareSystem.solar_system_id == solar_system_id
            ).first()

            old_contested = fw_system.contested if fw_system else None
            old_occupier = fw_system.occupier_faction_id if fw_system else None

            if fw_system:
                fw_system.occupier_faction_id = sys_data.get('occupier_faction_id')
                fw_system.owner_faction_id = sys_data.get('owner_faction_id')
                fw_system.contested = sys_data.get('contested', 'uncontested')
                fw_system.victory_points = sys_data.get('victory_points', 0)
                fw_system.victory_points_threshold = sys_data.get('victory_points_threshold', 3000)
                fw_system.synced_at = datetime.utcnow()
            else:
                fw_system = FactionWarfareSystem(
                    solar_system_id=solar_system_id,
                    occupier_faction_id=sys_data.get('occupier_faction_id'),
                    owner_faction_id=sys_data.get('owner_faction_id'),
                    contested=sys_data.get('contested', 'uncontested'),
                    victory_points=sys_data.get('victory_points', 0),
                    victory_points_threshold=sys_data.get('victory_points_threshold', 3000),
                )
                db.add(fw_system)

            db.flush()

            # Record system history if contested status or occupier changed
            if old_contested != fw_system.contested or old_occupier != fw_system.occupier_faction_id:
                history = FactionWarfareSystemHistory(
                    fw_system_id=fw_system.id,
                    occupier_faction_id=fw_system.occupier_faction_id,
                    contested=fw_system.contested,
                    victory_points=fw_system.victory_points,
                )
                db.add(history)

                # Publish event for system change
                publish_event(EventType.FW_SYSTEM_CHANGE, {
                    "solar_system_id": solar_system_id,
                    "contested": fw_system.contested,
                    "occupier_faction_id": fw_system.occupier_faction_id,
                })

            synced_count += 1

        db.commit()

        # Publish general update event
        publish_event(EventType.FW_UPDATE, {
            "synced_count": synced_count
        })

        logger.info(f"Synced {synced_count} faction warfare systems")

    except Exception as e:
        logger.error(f"Failed to sync faction warfare systems: {str(e)}")
        db.rollback()
        raise self.retry(exc=e)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_faction_warfare_stats(self: Task):
    """Sync faction warfare statistics from ESI"""
    try:
        db = next(get_db_session())
        esi_client = ESIClient()

        # Fetch FW stats for each faction (public data)
        factions = [500001, 500002, 500003, 500004]  # Caldari, Minmatar, Amarr, Gallente

        for faction_id in factions:
            try:
                stats_data = run_async(
                    esi_client.request("GET", f"/fw/stats/")
                )

                # Process faction-wide statistics
                for faction_stats in stats_data:
                    if faction_stats.get('faction_id') == faction_id:
                        # Update or create statistics
                        stats = db.query(FactionWarfareStatistics).filter(
                            FactionWarfareStatistics.faction_id == faction_id
                        ).first()

                        if stats:
                            stats.pilots = faction_stats.get('pilots', 0)
                            stats.systems_controlled = faction_stats.get('systems_controlled', 0)
                            stats.kills_yesterday = faction_stats.get('kills', {}).get('yesterday', 0)
                            stats.kills_last_week = faction_stats.get('kills', {}).get('last_week', 0)
                            stats.kills_total = faction_stats.get('kills', {}).get('total', 0)
                            stats.victory_points_yesterday = faction_stats.get('victory_points', {}).get('yesterday', 0)
                            stats.victory_points_last_week = faction_stats.get('victory_points', {}).get('last_week', 0)
                            stats.victory_points_total = faction_stats.get('victory_points', {}).get('total', 0)
                            stats.synced_at = datetime.utcnow()
                        else:
                            stats = FactionWarfareStatistics(
                                faction_id=faction_id,
                                pilots=faction_stats.get('pilots', 0),
                                systems_controlled=faction_stats.get('systems_controlled', 0),
                                kills_yesterday=faction_stats.get('kills', {}).get('yesterday', 0),
                                kills_last_week=faction_stats.get('kills', {}).get('last_week', 0),
                                kills_total=faction_stats.get('kills', {}).get('total', 0),
                                victory_points_yesterday=faction_stats.get('victory_points', {}).get('yesterday', 0),
                                victory_points_last_week=faction_stats.get('victory_points', {}).get('last_week', 0),
                                victory_points_total=faction_stats.get('victory_points', {}).get('total', 0),
                            )
                            db.add(stats)

            except Exception as e:
                logger.warning(f"Failed to sync stats for faction {faction_id}: {str(e)}")
                continue

        db.commit()
        logger.info("Synced faction warfare statistics")

    except Exception as e:
        logger.error(f"Failed to sync faction warfare stats: {str(e)}")
        db.rollback()
        raise self.retry(exc=e)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_character_faction_warfare(self: Task, character_id: int):
    """Sync faction warfare enrollment for a character"""
    try:
        db = next(get_db_session())
        esi_client = ESIClient()

        character = db.query(Character).filter(Character.id == character_id).first()
        if not character:
            logger.warning(f"Character {character_id} not found")
            return

        # Fetch character's FW stats from ESI (requires auth)
        try:
            fw_stats = run_async(
                esi_client.request(
                    "GET",
                    f"/characters/{character.character_id}/fw/stats/",
                    character=character
                )
            )

            # Update or create character FW record
            char_fw = db.query(CharacterFactionWarfare).filter(
                CharacterFactionWarfare.character_id == character.id
            ).first()

            if char_fw:
                char_fw.faction_id = fw_stats.get('faction_id')
                char_fw.enlisted = fw_stats.get('enlisted')
                char_fw.current_rank = fw_stats.get('current_rank', 0)
                char_fw.highest_rank = fw_stats.get('highest_rank', 0)
                char_fw.kills_yesterday = fw_stats.get('kills', {}).get('yesterday', 0)
                char_fw.kills_last_week = fw_stats.get('kills', {}).get('last_week', 0)
                char_fw.kills_total = fw_stats.get('kills', {}).get('total', 0)
                char_fw.victory_points_yesterday = fw_stats.get('victory_points', {}).get('yesterday', 0)
                char_fw.victory_points_last_week = fw_stats.get('victory_points', {}).get('last_week', 0)
                char_fw.victory_points_total = fw_stats.get('victory_points', {}).get('total', 0)
                char_fw.is_enrolled = True
                char_fw.synced_at = datetime.utcnow()
            else:
                char_fw = CharacterFactionWarfare(
                    character_id=character.id,
                    faction_id=fw_stats.get('faction_id'),
                    enlisted=fw_stats.get('enlisted'),
                    current_rank=fw_stats.get('current_rank', 0),
                    highest_rank=fw_stats.get('highest_rank', 0),
                    kills_yesterday=fw_stats.get('kills', {}).get('yesterday', 0),
                    kills_last_week=fw_stats.get('kills', {}).get('last_week', 0),
                    kills_total=fw_stats.get('kills', {}).get('total', 0),
                    victory_points_yesterday=fw_stats.get('victory_points', {}).get('yesterday', 0),
                    victory_points_last_week=fw_stats.get('victory_points', {}).get('last_week', 0),
                    victory_points_total=fw_stats.get('victory_points', {}).get('total', 0),
                    is_enrolled=True,
                )
                db.add(char_fw)

            db.commit()

            # Publish event
            publish_event(EventType.FW_CHARACTER_UPDATE, {
                "character_id": character.character_id,
                "faction_id": fw_stats.get('faction_id'),
                "current_rank": fw_stats.get('current_rank', 0),
            })

            logger.info(f"Synced faction warfare stats for character {character_id}")

        except Exception as e:
            # Character might not be enrolled in FW
            if "404" in str(e) or "403" in str(e):
                # Mark as not enrolled
                char_fw = db.query(CharacterFactionWarfare).filter(
                    CharacterFactionWarfare.character_id == character.id
                ).first()
                if char_fw:
                    char_fw.is_enrolled = False
                    char_fw.synced_at = datetime.utcnow()
                    db.commit()
                logger.info(f"Character {character_id} not enrolled in faction warfare")
            else:
                raise

    except Exception as e:
        logger.error(f"Failed to sync character faction warfare: {str(e)}")
        db.rollback()
        raise self.retry(exc=e)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def update_faction_warfare_leaderboard(self: Task, faction_id: int):
    """Update faction warfare leaderboard for a faction"""
    try:
        db = next(get_db_session())
        esi_client = ESIClient()

        # Fetch leaderboard from ESI
        leaderboard_data = run_async(
            esi_client.request("GET", f"/fw/leaderboards/")
        )

        # Process kills leaderboard
        if 'kills' in leaderboard_data:
            kills_data = leaderboard_data['kills']
            if 'yesterday' in kills_data:
                for idx, entry in enumerate(kills_data['yesterday'][:10]):  # Top 10
                    character_id = entry.get('character_id')
                    if character_id:
                        # Find character in our DB
                        character = db.query(Character).filter(
                            Character.character_id == character_id
                        ).first()

                        if character:
                            # Update or create leaderboard entry
                            leaderboard = db.query(FactionWarfareLeaderboard).filter(
                                FactionWarfareLeaderboard.character_id == character.id,
                                FactionWarfareLeaderboard.stat_type == 'kills_yesterday'
                            ).first()

                            if leaderboard:
                                leaderboard.rank = idx + 1
                                leaderboard.amount = entry.get('amount', 0)
                                leaderboard.synced_at = datetime.utcnow()
                            else:
                                leaderboard = FactionWarfareLeaderboard(
                                    character_id=character.id,
                                    stat_type='kills_yesterday',
                                    rank=idx + 1,
                                    amount=entry.get('amount', 0),
                                )
                                db.add(leaderboard)

        # Process victory points leaderboard
        if 'victory_points' in leaderboard_data:
            vp_data = leaderboard_data['victory_points']
            if 'yesterday' in vp_data:
                for idx, entry in enumerate(vp_data['yesterday'][:10]):
                    character_id = entry.get('character_id')
                    if character_id:
                        character = db.query(Character).filter(
                            Character.character_id == character_id
                        ).first()

                        if character:
                            leaderboard = db.query(FactionWarfareLeaderboard).filter(
                                FactionWarfareLeaderboard.character_id == character.id,
                                FactionWarfareLeaderboard.stat_type == 'victory_points_yesterday'
                            ).first()

                            if leaderboard:
                                leaderboard.rank = idx + 1
                                leaderboard.amount = entry.get('amount', 0)
                                leaderboard.synced_at = datetime.utcnow()
                            else:
                                leaderboard = FactionWarfareLeaderboard(
                                    character_id=character.id,
                                    stat_type='victory_points_yesterday',
                                    rank=idx + 1,
                                    amount=entry.get('amount', 0),
                                )
                                db.add(leaderboard)

        db.commit()
        logger.info(f"Updated faction warfare leaderboard for faction {faction_id}")

    except Exception as e:
        logger.error(f"Failed to update FW leaderboard: {str(e)}")
        db.rollback()
        raise self.retry(exc=e)
    finally:
        db.close()
