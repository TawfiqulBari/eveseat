"""
Calendar API Endpoints

Handle character calendar events
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from app.core.database import get_db
from app.models.user import User
from app.models.character import Character
from app.models.calendar import CalendarEvent, CalendarEventAttendee
from app.api.deps import get_current_user
from app.tasks.calendar_sync import sync_character_calendar, respond_to_event_task
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic models
class CalendarEventResponse(BaseModel):
    id: int
    event_id: int
    title: str
    description: Optional[str] = None
    event_date: datetime
    duration: int
    importance: int
    owner_id: int
    owner_name: str
    owner_type: str
    response: Optional[str] = None

    class Config:
        from_attributes = True


class CalendarEventAttendeeResponse(BaseModel):
    id: int
    character_id: int
    event_response: str

    class Config:
        from_attributes = True


class RespondToEventRequest(BaseModel):
    character_id: int
    response: str  # accepted, declined, tentative


@router.get("/", response_model=List[CalendarEventResponse])
async def list_calendar_events(
    character_id: Optional[int] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    response_filter: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List calendar events for a character

    Query parameters:
    - character_id: Filter by character
    - from_date: Events from this date onwards
    - to_date: Events until this date
    - response_filter: Filter by response (accepted, declined, tentative, not_responded)
    - limit: Max results (default 50, max 200)
    - offset: Pagination offset
    """
    # Get character
    if character_id:
        character = db.query(Character).filter(
            and_(
                Character.id == character_id,
                Character.user_id == current_user.id,
            )
        ).first()
    else:
        character = db.query(Character).filter(
            Character.user_id == current_user.id
        ).first()

    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found"
        )

    # Build query
    query = db.query(CalendarEvent).filter(CalendarEvent.character_id == character.id)

    # Default to future events if no date filter provided
    if from_date is None and to_date is None:
        from_date = datetime.utcnow()

    if from_date:
        query = query.filter(CalendarEvent.event_date >= from_date)

    if to_date:
        query = query.filter(CalendarEvent.event_date <= to_date)

    if response_filter:
        query = query.filter(CalendarEvent.response == response_filter)

    # Order by event date ascending (upcoming first)
    query = query.order_by(CalendarEvent.event_date)

    # Pagination
    events = query.offset(offset).limit(limit).all()

    return events


@router.get("/{event_id}", response_model=CalendarEventResponse)
async def get_calendar_event(
    event_id: int,
    character_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific calendar event by ID"""
    # Get event
    event = db.query(CalendarEvent).filter(CalendarEvent.event_id == event_id).first()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calendar event not found"
        )

    # Verify ownership
    character = db.query(Character).filter(Character.id == event.character_id).first()
    if not character or character.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this event"
        )

    return event


@router.get("/{event_id}/attendees", response_model=List[CalendarEventAttendeeResponse])
async def get_event_attendees(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get attendees for a calendar event"""
    # Get event
    event = db.query(CalendarEvent).filter(CalendarEvent.event_id == event_id).first()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calendar event not found"
        )

    # Verify ownership
    character = db.query(Character).filter(Character.id == event.character_id).first()
    if not character or character.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this event"
        )

    # Get attendees
    attendees = db.query(CalendarEventAttendee).filter(
        CalendarEventAttendee.event_id == event_id
    ).all()

    return attendees


@router.put("/{event_id}/respond")
async def respond_to_event(
    event_id: int,
    request: RespondToEventRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Respond to a calendar event

    Response types: accepted, declined, tentative
    """
    # Verify character ownership
    character = db.query(Character).filter(
        and_(
            Character.id == request.character_id,
            Character.user_id == current_user.id,
        )
    ).first()

    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found"
        )

    # Get event
    event = db.query(CalendarEvent).filter(
        and_(
            CalendarEvent.event_id == event_id,
            CalendarEvent.character_id == character.id,
        )
    ).first()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calendar event not found"
        )

    # Validate response
    valid_responses = ["accepted", "declined", "tentative"]
    if request.response not in valid_responses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid response. Must be one of: {', '.join(valid_responses)}"
        )

    # Update local event
    event.response = request.response
    db.commit()

    # Queue task to respond via ESI
    task = respond_to_event_task.delay(
        character_id=character.character_id,
        event_id=event_id,
        response=request.response,
    )

    return {
        "success": True,
        "task_id": task.id,
        "message": f"Response '{request.response}' recorded and queued for ESI"
    }


@router.get("/upcoming/")
async def get_upcoming_events(
    character_id: Optional[int] = None,
    days: int = Query(7, le=30),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get upcoming events for the next N days

    Defaults to 7 days, max 30 days
    """
    # Get character
    if character_id:
        character = db.query(Character).filter(
            and_(
                Character.id == character_id,
                Character.user_id == current_user.id,
            )
        ).first()
    else:
        character = db.query(Character).filter(
            Character.user_id == current_user.id
        ).first()

    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found"
        )

    # Get events in date range
    from_date = datetime.utcnow()
    to_date = from_date + timedelta(days=days)

    events = db.query(CalendarEvent).filter(
        and_(
            CalendarEvent.character_id == character.id,
            CalendarEvent.event_date >= from_date,
            CalendarEvent.event_date <= to_date,
        )
    ).order_by(CalendarEvent.event_date).all()

    return events


@router.post("/sync/{character_id}")
async def trigger_calendar_sync(
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger manual calendar sync for a character"""
    # Verify character ownership
    character = db.query(Character).filter(
        and_(
            Character.id == character_id,
            Character.user_id == current_user.id,
        )
    ).first()

    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found"
        )

    # Queue sync task
    task = sync_character_calendar.delay(character.character_id)

    return {
        "success": True,
        "task_id": task.id,
        "message": "Calendar sync queued"
    }
