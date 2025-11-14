"""
Bookmark sync tasks

Syncs character bookmarks and folders from ESI
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
from app.models.bookmark import Bookmark, BookmarkFolder
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
def sync_character_bookmarks(self, character_id: int):
    """
    Sync bookmarks and folders for a character from ESI

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
                EveToken.scope.contains("esi-bookmarks.read_character_bookmarks.v1"),
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

        # Fetch bookmark folders
        folders_data = run_async(
            esi_client.request(
                "GET",
                f"/characters/{character_id}/bookmarks/folders/",
                access_token=access_token,
            )
        )

        logger.info(f"Fetched {len(folders_data)} bookmark folders for character {character_id}")

        # Clear existing folders and re-add
        db.query(BookmarkFolder).filter(BookmarkFolder.character_id == character.id).delete()

        folder_map = {}  # Map ESI folder_id to DB id
        for folder_data in folders_data:
            folder = BookmarkFolder(
                character_id=character.id,
                folder_id=folder_data.get("folder_id"),
                name=folder_data.get("name", ""),
            )
            db.add(folder)
            db.flush()  # Get the ID
            folder_map[folder_data.get("folder_id")] = folder.id

        # Fetch bookmarks
        bookmarks_data = run_async(
            esi_client.request(
                "GET",
                f"/characters/{character_id}/bookmarks/",
                access_token=access_token,
            )
        )

        logger.info(f"Fetched {len(bookmarks_data)} bookmarks for character {character_id}")

        # Clear existing bookmarks and re-add
        db.query(Bookmark).filter(Bookmark.character_id == character.id).delete()

        synced_count = 0
        for bookmark_data in bookmarks_data:
            folder_id = bookmark_data.get("folder_id")
            db_folder_id = folder_map.get(folder_id) if folder_id else None

            bookmark = Bookmark(
                character_id=character.id,
                bookmark_id=bookmark_data.get("bookmark_id"),
                label=bookmark_data.get("label", ""),
                notes=bookmark_data.get("notes"),
                created=datetime.fromisoformat(
                    bookmark_data.get("created", "").replace("Z", "+00:00")
                ),
                location_id=bookmark_data.get("location_id"),
                creator_id=bookmark_data.get("creator_id"),
                folder_id=db_folder_id,
                coordinates=bookmark_data.get("coordinates"),
                item_id=bookmark_data.get("item", {}).get("item_id") if bookmark_data.get("item") else None,
                item_type_id=bookmark_data.get("item", {}).get("type_id") if bookmark_data.get("item") else None,
            )
            db.add(bookmark)
            synced_count += 1

        db.commit()

        # Publish WebSocket event
        event_publisher.publish(
            "bookmarks",
            EventType.BOOKMARK_UPDATE,
            {
                "character_id": character_id,
                "total_bookmarks": len(bookmarks_data),
                "total_folders": len(folders_data),
            },
        )

        logger.info(f"Synced {synced_count} bookmarks and {len(folders_data)} folders for character {character_id}")
        return {"success": True, "bookmarks": synced_count, "folders": len(folders_data)}

    except ESIRateLimitError as e:
        logger.warning(f"Rate limit hit for character {character_id}: {e}")
        raise self.retry(exc=e)
    except Exception as e:
        logger.error(f"Error syncing bookmarks for character {character_id}: {e}")
        db.rollback()
        raise self.retry(exc=e)
    finally:
        db.close()
