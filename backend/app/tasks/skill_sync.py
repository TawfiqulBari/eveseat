"""
Skill sync tasks

Syncs character skills and skill queue from ESI
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
from app.models.skill import Skill, SkillQueue
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
def sync_character_skills(self, character_id: int):
    """
    Sync skills and skill queue for a character from ESI

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
                EveToken.scope.contains("esi-skills.read_skills.v1"),
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

        # Fetch skills
        skills_data = run_async(
            esi_client.request(
                "GET",
                f"/characters/{character_id}/skills/",
                access_token=access_token,
            )
        )

        logger.info(f"Fetched skills for character {character_id}")

        # Clear existing skills and re-add (simpler than tracking deltas)
        db.query(Skill).filter(Skill.character_id == character.id).delete()

        skills_list = skills_data.get("skills", [])
        for skill_data in skills_list:
            skill = Skill(
                character_id=character.id,
                skill_id=skill_data.get("skill_id"),
                active_skill_level=skill_data.get("active_skill_level", 0),
                trained_skill_level=skill_data.get("trained_skill_level", 0),
                skillpoints_in_skill=skill_data.get("skillpoints_in_skill", 0),
            )
            db.add(skill)

        # Fetch skill queue
        queue_data = run_async(
            esi_client.request(
                "GET",
                f"/characters/{character_id}/skillqueue/",
                access_token=access_token,
            )
        )

        # Clear existing queue and re-add
        db.query(SkillQueue).filter(SkillQueue.character_id == character.id).delete()

        for queue_item in queue_data:
            skill_queue = SkillQueue(
                character_id=character.id,
                skill_id=queue_item.get("skill_id"),
                queue_position=queue_item.get("queue_position", 0),
                finished_level=queue_item.get("finished_level", 0),
                start_date=(
                    datetime.fromisoformat(queue_item.get("start_date", "").replace("Z", "+00:00"))
                    if queue_item.get("start_date")
                    else None
                ),
                finish_date=(
                    datetime.fromisoformat(queue_item.get("finish_date", "").replace("Z", "+00:00"))
                    if queue_item.get("finish_date")
                    else None
                ),
                training_start_sp=queue_item.get("training_start_sp"),
                level_start_sp=queue_item.get("level_start_sp"),
                level_end_sp=queue_item.get("level_end_sp"),
            )
            db.add(skill_queue)

        db.commit()

        # Publish WebSocket event
        event_publisher.publish(
            "skills",
            EventType.SKILL_UPDATE,
            {
                "character_id": character_id,
                "total_skills": len(skills_list),
                "queue_length": len(queue_data),
            },
        )

        logger.info(f"Synced {len(skills_list)} skills and {len(queue_data)} queue items for character {character_id}")
        return {"success": True, "skills": len(skills_list), "queue": len(queue_data)}

    except ESIRateLimitError as e:
        logger.warning(f"Rate limit hit for character {character_id}: {e}")
        raise self.retry(exc=e)
    except Exception as e:
        logger.error(f"Error syncing skills for character {character_id}: {e}")
        db.rollback()
        raise self.retry(exc=e)
    finally:
        db.close()
