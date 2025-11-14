"""
Killmail sync tasks

Syncs killmails from ESI and zKillboard RedisQ
"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import logging
import asyncio
import httpx
import hashlib
import json

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.killmail import Killmail
from app.models.eve_token import EveToken
from app.models.character import Character
from app.services.esi_client import esi_client, ESIError, ESIRateLimitError
from app.core.config import settings

logger = logging.getLogger(__name__)


def run_async(coro):
    """Helper to run async functions in sync context"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_killmails_from_esi(self):
    """
    Sync killmails from ESI for all characters with killmail read scope
    
    Runs every 5 minutes via Celery Beat
    """
    db: Session = SessionLocal()
    synced_count = 0
    error_count = 0
    
    try:
        # Find all active tokens with killmail read scope
        tokens = db.query(EveToken).filter(
            and_(
                EveToken.expires_at > datetime.utcnow(),
                EveToken.scope.contains("esi-killmails.read_killmails.v1"),
            )
        ).all()
        
        logger.info(f"Found {len(tokens)} tokens with killmail scope")
        
        for token in tokens:
            try:
                # Decrypt access token
                from app.core.encryption import encryption
                access_token = encryption.decrypt(token.access_token_encrypted)
                
                # Get character killmails from ESI
                # ESI endpoint: GET /characters/{character_id}/killmails/recent/
                killmails_data = run_async(
                    esi_client.request(
                        "GET",
                        f"/characters/{token.character_id}/killmails/recent/",
                        access_token=access_token,
                        params={"limit": 50},  # Get last 50 killmails
                    )
                )
                
                for km_data in killmails_data:
                    killmail_id = km_data.get("killmail_id")
                    killmail_hash = km_data.get("killmail_hash")
                    
                    if not killmail_id or not killmail_hash:
                        continue
                    
                    # Check if killmail already exists
                    existing = db.query(Killmail).filter(
                        Killmail.killmail_id == killmail_id
                    ).first()
                    
                    if existing:
                        continue  # Skip if already synced
                    
                    # Fetch full killmail details from ESI
                    try:
                        full_killmail = run_async(
                            esi_client.request(
                                "GET",
                                f"/killmails/{killmail_id}/{killmail_hash}/",
                            )
                        )
                    except ESIError as e:
                        logger.warning(f"Failed to fetch killmail {killmail_id}: {e}")
                        continue
                    
                    # Extract killmail data
                    victim = full_killmail.get("victim", {})
                    attackers = full_killmail.get("attackers", [])
                    
                    # Calculate total value (sum of destroyed items)
                    total_value = 0
                    items = victim.get("items", [])
                    for item in items:
                        # Value calculation would need type_id lookup
                        # For now, we'll store the raw data
                        pass
                    
                    # Create killmail record
                    killmail = Killmail(
                        killmail_id=killmail_id,
                        killmail_hash=killmail_hash,
                        time=datetime.fromisoformat(full_killmail.get("killmail_time", "").replace("Z", "+00:00")),
                        system_id=full_killmail.get("solar_system_id"),
                        victim_character_id=victim.get("character_id"),
                        victim_corporation_id=victim.get("corporation_id"),
                        victim_alliance_id=victim.get("alliance_id"),
                        victim_ship_type_id=victim.get("ship_type_id"),
                        attackers_count=len(attackers),
                        value=total_value,  # Will be calculated properly later
                        killmail_data=full_killmail,
                        zkill_url=f"https://zkillboard.com/kill/{killmail_id}/",
                    )
                    
                    db.add(killmail)
                    synced_count += 1
                
                db.commit()
                logger.info(f"Synced {synced_count} killmails for character {token.character_id}")
                
            except ESIRateLimitError as e:
                logger.warning(f"Rate limit hit for character {token.character_id}: {e}")
                error_count += 1
                # Wait a bit before continuing
                import time
                time.sleep(5)
            except Exception as e:
                logger.error(f"Error syncing killmails for character {token.character_id}: {e}")
                error_count += 1
                db.rollback()
        
        logger.info(f"Killmail sync completed: {synced_count} synced, {error_count} errors")
        return {
            "synced": synced_count,
            "errors": error_count,
            "total_tokens": len(tokens),
        }
        
    except Exception as e:
        logger.error(f"Killmail sync task error: {e}")
        db.rollback()
        raise self.retry(exc=e)
    finally:
        db.close()


@celery_app.task
def sync_killmail_from_zkillboard(killmail_id: int, killmail_hash: str = None):
    """
    Sync a specific killmail from zKillboard/ESI
    
    Args:
        killmail_id: EVE killmail ID
        killmail_hash: Killmail hash (optional, will fetch from zKillboard if not provided)
    """
    db: Session = SessionLocal()
    
    try:
        # Check if already exists
        existing = db.query(Killmail).filter(
            Killmail.killmail_id == killmail_id
        ).first()
        
        if existing:
            logger.info(f"Killmail {killmail_id} already exists")
            return {"success": True, "message": "Already exists"}
        
        # If no hash provided, try to get from zKillboard
        if not killmail_hash:
            try:
                zkill_data = run_async(_fetch_zkillboard_killmail(killmail_id))
                if zkill_data:
                    killmail_hash = zkill_data.get("zkb", {}).get("hash")
            except Exception as e:
                logger.warning(f"Failed to get hash from zKillboard: {e}")
        
        if not killmail_hash:
            logger.error(f"No hash available for killmail {killmail_id}")
            return {"success": False, "error": "No hash available"}
        
        # Fetch from ESI
        try:
            full_killmail = run_async(
                esi_client.request(
                    "GET",
                    f"/killmails/{killmail_id}/{killmail_hash}/",
                )
            )
        except ESIError as e:
            logger.error(f"Failed to fetch killmail {killmail_id} from ESI: {e}")
            return {"success": False, "error": str(e)}
        
        # Extract and save killmail (similar to sync_killmails_from_esi)
        victim = full_killmail.get("victim", {})
        attackers = full_killmail.get("attackers", [])
        
        killmail = Killmail(
            killmail_id=killmail_id,
            killmail_hash=killmail_hash,
            time=datetime.fromisoformat(full_killmail.get("killmail_time", "").replace("Z", "+00:00")),
            system_id=full_killmail.get("solar_system_id"),
            victim_character_id=victim.get("character_id"),
            victim_corporation_id=victim.get("corporation_id"),
            victim_alliance_id=victim.get("alliance_id"),
            victim_ship_type_id=victim.get("ship_type_id"),
            attackers_count=len(attackers),
            value=0,  # Will be calculated properly
            killmail_data=full_killmail,
            zkill_url=f"https://zkillboard.com/kill/{killmail_id}/",
        )
        
        db.add(killmail)
        db.commit()
        
        logger.info(f"Synced killmail {killmail_id} from zKillboard")
        return {"success": True, "killmail_id": killmail_id}
        
    except Exception as e:
        logger.error(f"Error syncing killmail {killmail_id}: {e}")
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()


async def _fetch_zkillboard_killmail(killmail_id: int) -> dict:
    """Fetch killmail data from zKillboard API"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://zkillboard.com/api/killID/{killmail_id}/",
            timeout=10.0,
        )
        response.raise_for_status()
        return response.json()


@celery_app.task
def subscribe_zkillboard_redisq():
    """
    Subscribe to zKillboard RedisQ for real-time killmail updates
    
    This task runs continuously and processes killmails as they come in
    """
    import redis
    import time
    
    try:
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        return
    
    queue_id = settings.ZKILL_REDISQ_QUEUE_ID
    if not queue_id:
        # Get a new queue ID
        try:
            async def get_queue_id():
                async with httpx.AsyncClient() as client:
                    response = await client.get(settings.ZKILL_REDISQ_URL, timeout=10.0)
                    response.raise_for_status()
                    return response.json().get("package")
            
            queue_data = run_async(get_queue_id())
            queue_id = queue_data.get("queueID") if queue_data else None
            
            if queue_id:
                # Store queue ID in settings/Redis for persistence
                redis_client.setex("zkill:queue_id", 86400, queue_id)  # 24 hours
        except Exception as e:
            logger.error(f"Failed to get zKillboard queue ID: {e}")
            return
    
    logger.info(f"Subscribing to zKillboard RedisQ with queue ID: {queue_id}")
    
    # Poll zKillboard RedisQ
    while True:
        try:
            # zKillboard RedisQ endpoint
            url = f"https://redisq.zkillboard.com/listen.php?queueID={queue_id}"
            
            async def poll_redisq():
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.get(url)
                    response.raise_for_status()
                    return response.json()
            
            data = run_async(poll_redisq())
            
            if data and data.get("package"):
                package = data["package"]
                killmail_id = package.get("killID")
                killmail_hash = package.get("zkb", {}).get("hash")
                
                if killmail_id and killmail_hash:
                    # Queue killmail sync task
                    sync_killmail_from_zkillboard.delay(killmail_id, killmail_hash)
                    logger.info(f"Queued killmail {killmail_id} from zKillboard RedisQ")
            
            # Small delay to avoid hammering the API
            time.sleep(1)
            
        except KeyboardInterrupt:
            logger.info("zKillboard RedisQ subscription stopped")
            break
        except Exception as e:
            logger.error(f"Error in zKillboard RedisQ subscription: {e}")
            time.sleep(5)  # Wait before retrying

