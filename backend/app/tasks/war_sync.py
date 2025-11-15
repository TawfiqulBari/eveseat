"""
War sync tasks
"""
import asyncio
from celery import Task
from datetime import datetime

from app.core.celery_app import celery_app
from app.core.database import get_db_session
from app.models.war import War, WarAlly, WarKillmail
from app.models.alliance import Alliance
from app.services.esi_client import ESIClient
from app.websockets.publisher import publish_event
from app.websockets.events import EventType
from app.core.logger import logger


def run_async(coro):
    """Helper to run async code in Celery tasks"""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_wars_data(self: Task):
    """Sync all active wars from ESI"""
    try:
        db = next(get_db_session())
        esi_client = ESIClient()

        # Fetch all wars from ESI
        wars_data = run_async(
            esi_client.request("GET", "/wars/")
        )

        synced_count = 0
        for war_id in wars_data:
            # Fetch detailed war info
            war_details = run_async(
                esi_client.request("GET", f"/wars/{war_id}/")
            )

            # Find or create aggressor and defender alliances if they exist
            aggressor_alliance = None
            defender_alliance = None

            if 'aggressor' in war_details and 'alliance_id' in war_details['aggressor']:
                aggressor_alliance_id = war_details['aggressor']['alliance_id']
                aggressor_alliance = db.query(Alliance).filter(
                    Alliance.alliance_id == aggressor_alliance_id
                ).first()
                if not aggressor_alliance:
                    # Create placeholder alliance
                    aggressor_alliance = Alliance(
                        alliance_id=aggressor_alliance_id,
                        alliance_name=f"Alliance {aggressor_alliance_id}",
                        ticker="???",
                    )
                    db.add(aggressor_alliance)
                    db.flush()

            if 'defender' in war_details and 'alliance_id' in war_details['defender']:
                defender_alliance_id = war_details['defender']['alliance_id']
                defender_alliance = db.query(Alliance).filter(
                    Alliance.alliance_id == defender_alliance_id
                ).first()
                if not defender_alliance:
                    # Create placeholder alliance
                    defender_alliance = Alliance(
                        alliance_id=defender_alliance_id,
                        alliance_name=f"Alliance {defender_alliance_id}",
                        ticker="???",
                    )
                    db.add(defender_alliance)
                    db.flush()

            # Update or create war
            war = db.query(War).filter(War.war_id == war_id).first()

            if war:
                war.declared = war_details.get('declared')
                war.started = war_details.get('started')
                war.finished = war_details.get('finished')
                war.is_mutual = war_details.get('mutual', False)
                war.is_open_for_allies = war_details.get('open_for_allies', False)
                war.aggressor_alliance_id = aggressor_alliance.id if aggressor_alliance else None
                war.defender_alliance_id = defender_alliance.id if defender_alliance else None
                war.aggressor_ships_killed = war_details.get('aggressor', {}).get('ships_killed', 0)
                war.defender_ships_killed = war_details.get('defender', {}).get('ships_killed', 0)
                war.aggressor_isk_destroyed = war_details.get('aggressor', {}).get('isk_destroyed', 0)
                war.defender_isk_destroyed = war_details.get('defender', {}).get('isk_destroyed', 0)
                war.is_active = war_details.get('finished') is None
                war.synced_at = datetime.utcnow()
            else:
                war = War(
                    war_id=war_id,
                    declared=war_details.get('declared'),
                    started=war_details.get('started'),
                    finished=war_details.get('finished'),
                    is_mutual=war_details.get('mutual', False),
                    is_open_for_allies=war_details.get('open_for_allies', False),
                    aggressor_alliance_id=aggressor_alliance.id if aggressor_alliance else None,
                    defender_alliance_id=defender_alliance.id if defender_alliance else None,
                    aggressor_ships_killed=war_details.get('aggressor', {}).get('ships_killed', 0),
                    defender_ships_killed=war_details.get('defender', {}).get('ships_killed', 0),
                    aggressor_isk_destroyed=war_details.get('aggressor', {}).get('isk_destroyed', 0),
                    defender_isk_destroyed=war_details.get('defender', {}).get('isk_destroyed', 0),
                    is_active=war_details.get('finished') is None,
                )
                db.add(war)

            db.flush()

            # Sync allies if applicable
            if war_details.get('allies'):
                for ally_data in war_details['allies']:
                    ally_alliance_id = ally_data.get('alliance_id')
                    if ally_alliance_id:
                        ally_alliance = db.query(Alliance).filter(
                            Alliance.alliance_id == ally_alliance_id
                        ).first()
                        if not ally_alliance:
                            ally_alliance = Alliance(
                                alliance_id=ally_alliance_id,
                                alliance_name=f"Alliance {ally_alliance_id}",
                                ticker="???",
                            )
                            db.add(ally_alliance)
                            db.flush()

                        # Check if ally already exists
                        existing_ally = db.query(WarAlly).filter(
                            WarAlly.war_id == war.id,
                            WarAlly.alliance_id == ally_alliance.id
                        ).first()

                        if not existing_ally:
                            war_ally = WarAlly(
                                war_id=war.id,
                                alliance_id=ally_alliance.id,
                            )
                            db.add(war_ally)

            synced_count += 1

        db.commit()

        # Publish WebSocket event
        publish_event(EventType.WAR_UPDATE, {
            "synced_count": synced_count,
            "active_wars": db.query(War).filter(War.is_active == True).count()
        })

        logger.info(f"Synced {synced_count} wars")

    except Exception as e:
        logger.error(f"Failed to sync wars: {str(e)}")
        db.rollback()
        raise self.retry(exc=e)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_war_killmails(self: Task, war_id: int):
    """Sync killmails for a specific war"""
    try:
        db = next(get_db_session())
        esi_client = ESIClient()

        war = db.query(War).filter(War.war_id == war_id).first()
        if not war:
            logger.warning(f"War {war_id} not found")
            return

        # Fetch war killmails from ESI
        killmails_data = run_async(
            esi_client.request("GET", f"/wars/{war_id}/killmails/")
        )

        synced_count = 0
        for km_data in killmails_data:
            killmail_id = km_data.get('killmail_id')
            killmail_hash = km_data.get('killmail_hash')

            # Check if killmail already exists
            existing = db.query(WarKillmail).filter(
                WarKillmail.war_id == war.id,
                WarKillmail.killmail_id == killmail_id
            ).first()

            if not existing:
                war_killmail = WarKillmail(
                    war_id=war.id,
                    killmail_id=killmail_id,
                    killmail_hash=killmail_hash,
                )
                db.add(war_killmail)
                synced_count += 1

        db.commit()

        logger.info(f"Synced {synced_count} killmails for war {war_id}")

    except Exception as e:
        logger.error(f"Failed to sync killmails for war {war_id}: {str(e)}")
        db.rollback()
        raise self.retry(exc=e)
    finally:
        db.close()
