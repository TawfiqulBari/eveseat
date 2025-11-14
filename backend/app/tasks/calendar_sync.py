"""
Calendar sync tasks

Syncs character calendar events from ESI
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
from app.models.calendar import CalendarEvent, CalendarEventAttendee
from app.services.esi_client import esi_client, ESIError, ESIRateLimitError

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
def sync_character_calendar(self, character_id: int):
    """
    Sync calendar events for a character from ESI

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
                EveToken.scope.contains("esi-calendar.read_calendar_events.v1"),
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

        # Fetch calendar event summaries
        events_data = run_async(
            esi_client.request(
                "GET",
                f"/characters/{character_id}/calendar/",
                access_token=access_token,
            )
        )

        logger.info(f"Fetched {len(events_data)} calendar events for character {character_id}")

        synced_count = 0

        for event_summary in events_data:
            event_id = event_summary.get("event_id")

            # Check if event already exists
            existing = db.query(CalendarEvent).filter(
                CalendarEvent.event_id == event_id
            ).first()

            # Fetch full event details
            try:
                event_details = run_async(
                    esi_client.request(
                        "GET",
                        f"/characters/{character_id}/calendar/{event_id}/",
                        access_token=access_token,
                    )
                )
            except ESIError as e:
                logger.warning(f"Failed to fetch event {event_id} details: {e}")
                continue

            if existing:
                # Update existing event
                existing.title = event_details.get("title", "")
                existing.description = event_details.get("text", "")
                existing.event_date = datetime.fromisoformat(
                    event_summary.get("event_date", "").replace("Z", "+00:00")
                )
                existing.duration = event_summary.get("duration", 0)
                existing.importance = event_summary.get("importance", 0)
                existing.response = event_summary.get("event_response", "not_responded")
                existing.owner_id = event_details.get("owner_id")
                existing.owner_name = event_details.get("owner_name", "")
                existing.owner_type = event_details.get("owner_type", "character")
            else:
                # Create new event
                event = CalendarEvent(
                    character_id=character.id,
                    event_id=event_id,
                    title=event_details.get("title", ""),
                    description=event_details.get("text", ""),
                    event_date=datetime.fromisoformat(
                        event_summary.get("event_date", "").replace("Z", "+00:00")
                    ),
                    duration=event_summary.get("duration", 0),
                    importance=event_summary.get("importance", 0),
                    owner_id=event_details.get("owner_id"),
                    owner_name=event_details.get("owner_name", ""),
                    owner_type=event_details.get("owner_type", "character"),
                    response=event_summary.get("event_response", "not_responded"),
                )
                db.add(event)
                synced_count += 1

            # Sync attendees (if available)
            try:
                attendees_data = run_async(
                    esi_client.request(
                        "GET",
                        f"/characters/{character_id}/calendar/{event_id}/attendees/",
                        access_token=access_token,
                    )
                )

                # Clear existing attendees
                db.query(CalendarEventAttendee).filter(
                    CalendarEventAttendee.event_id == event_id
                ).delete()

                # Add new attendees
                for attendee_data in attendees_data:
                    attendee = CalendarEventAttendee(
                        event_id=event_id,
                        character_id=attendee_data.get("character_id"),
                        event_response=attendee_data.get("event_response", "not_responded"),
                    )
                    db.add(attendee)

            except ESIError as e:
                logger.warning(f"Failed to fetch attendees for event {event_id}: {e}")

        db.commit()

        logger.info(f"Synced {synced_count} new calendar events for character {character_id}")
        return {"success": True, "synced": synced_count}

    except ESIRateLimitError as e:
        logger.warning(f"Rate limit hit for character {character_id}: {e}")
        raise self.retry(exc=e)
    except Exception as e:
        logger.error(f"Error syncing calendar for character {character_id}: {e}")
        db.rollback()
        raise self.retry(exc=e)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def respond_to_event_task(
    self,
    character_id: int,
    event_id: int,
    response: str,
):
    """
    Respond to a calendar event via ESI

    Args:
        character_id: EVE character ID
        event_id: Calendar event ID
        response: Response type (accepted, declined, tentative)
    """
    db: Session = SessionLocal()

    try:
        # Find valid token
        now = datetime.now(timezone.utc)
        token = db.query(EveToken).filter(
            and_(
                EveToken.character_id == character_id,
                EveToken.expires_at > now,
                EveToken.scope.contains("esi-calendar.respond_calendar_events.v1"),
            )
        ).first()

        if not token:
            logger.warning(f"No valid token found for character {character_id}")
            return {"success": False, "error": "No valid token found"}

        from app.core.encryption import encryption
        access_token = encryption.decrypt(token.access_token_encrypted)

        # Send response to ESI
        response_data = {
            "response": response
        }

        result = run_async(
            esi_client.request(
                "PUT",
                f"/characters/{character_id}/calendar/{event_id}/",
                access_token=access_token,
                params=response_data,
            )
        )

        logger.info(f"Responded to event {event_id} for character {character_id}: {response}")
        return {"success": True, "response": response}

    except ESIError as e:
        logger.error(f"Failed to respond to event: {e}")
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Error responding to event: {e}")
        db.rollback()
        raise self.retry(exc=e)
    finally:
        db.close()
