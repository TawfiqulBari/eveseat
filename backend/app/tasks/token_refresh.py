"""
Token refresh tasks for EVE Online ESI tokens
"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_
import logging
import asyncio

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.eve_token import EveToken
from app.services.esi_client import esi_client, ESITokenError
from app.core.encryption import encryption

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
def refresh_expired_tokens(self):
    """
    Celery task to refresh tokens that are expiring soon (within 5 minutes)
    
    Runs every 15 minutes via Celery Beat
    """
    db: Session = SessionLocal()
    refreshed_count = 0
    failed_count = 0
    
    try:
        # Find tokens expiring within 5 minutes
        expiry_threshold = datetime.utcnow() + timedelta(minutes=5)
        
        expiring_tokens = db.query(EveToken).filter(
            and_(
                EveToken.expires_at <= expiry_threshold,
                EveToken.expires_at > datetime.utcnow(),  # Not already expired
            )
        ).all()
        
        logger.info(f"Found {len(expiring_tokens)} tokens expiring soon")
        
        for token in expiring_tokens:
            try:
                # Refresh token (async call in sync context)
                token_response = run_async(
                    esi_client.refresh_access_token(token.refresh_token_encrypted)
                )
                
                access_token = token_response.get("access_token")
                refresh_token = token_response.get("refresh_token")
                expires_in = token_response.get("expires_in", 1200)
                
                # Encrypt new tokens
                encrypted_access = encryption.encrypt(access_token)
                encrypted_refresh = encryption.encrypt(refresh_token)
                
                # Update token
                token.access_token_encrypted = encrypted_access
                token.refresh_token_encrypted = encrypted_refresh
                token.expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                token.last_refreshed_at = datetime.utcnow()
                
                db.commit()
                refreshed_count += 1
                logger.info(f"Refreshed token for character {token.character_id}")
                
            except ESITokenError as e:
                logger.error(f"Failed to refresh token for character {token.character_id}: {e}")
                # Token might be invalid - mark for deletion or user re-auth
                failed_count += 1
                # Optionally delete invalid tokens
                # db.delete(token)
                db.commit()
            except Exception as e:
                logger.error(f"Error refreshing token for character {token.character_id}: {e}")
                failed_count += 1
                db.rollback()
        
        logger.info(f"Token refresh completed: {refreshed_count} refreshed, {failed_count} failed")
        return {
            "refreshed": refreshed_count,
            "failed": failed_count,
            "total": len(expiring_tokens),
        }
        
    except Exception as e:
        logger.error(f"Token refresh task error: {e}")
        db.rollback()
        # Retry the task
        raise self.retry(exc=e)
    finally:
        db.close()


@celery_app.task
def refresh_token_for_character(character_id: int):
    """
    Refresh token for a specific character
    
    Args:
        character_id: EVE character ID
    """
    db: Session = SessionLocal()
    
    try:
        token = db.query(EveToken).filter(
            EveToken.character_id == character_id
        ).first()
        
        if not token:
            logger.warning(f"Token not found for character {character_id}")
            return {"success": False, "error": "Token not found"}
        
        # Refresh token (async call in sync context)
        token_response = run_async(
            esi_client.refresh_access_token(token.refresh_token_encrypted)
        )
        
        access_token = token_response.get("access_token")
        refresh_token = token_response.get("refresh_token")
        expires_in = token_response.get("expires_in", 1200)
        
        # Encrypt new tokens
        encrypted_access = encryption.encrypt(access_token)
        encrypted_refresh = encryption.encrypt(refresh_token)
        
        # Update token
        token.access_token_encrypted = encrypted_access
        token.refresh_token_encrypted = encrypted_refresh
        token.expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        token.last_refreshed_at = datetime.utcnow()
        
        db.commit()
        
        logger.info(f"Refreshed token for character {character_id}")
        return {"success": True, "character_id": character_id}
        
    except ESITokenError as e:
        logger.error(f"Failed to refresh token for character {character_id}: {e}")
        db.rollback()
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Error refreshing token for character {character_id}: {e}")
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()

