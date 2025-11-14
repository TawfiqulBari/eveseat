"""
Calendar models

EVE Online calendar events system
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, BigInteger
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base


class CalendarEvent(Base):
    """Calendar events"""

    __tablename__ = "calendar_events"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False, index=True)
    event_id = Column(BigInteger, unique=True, index=True)  # EVE event ID
    title = Column(String(255))
    description = Column(Text)
    event_date = Column(DateTime(timezone=True), index=True)
    duration = Column(Integer)  # Duration in minutes
    importance = Column(Integer)  # 0 = normal, 1 = important

    # Owner information
    owner_id = Column(BigInteger)
    owner_name = Column(String(255))
    owner_type = Column(String(50))  # character, corporation, alliance

    # Event response
    response = Column(String(50))  # accepted, declined, tentative, not_responded

    # Metadata
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    character = relationship("Character", back_populates="calendar_events")

    def __repr__(self):
        return f"<CalendarEvent(event_id={self.event_id}, title='{self.title}', date={self.event_date})>"


class CalendarEventAttendee(Base):
    """Calendar event attendees"""

    __tablename__ = "calendar_event_attendees"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(BigInteger, ForeignKey("calendar_events.event_id"), nullable=False, index=True)
    character_id = Column(BigInteger)  # Attendee character ID
    event_response = Column(String(50))  # accepted, declined, tentative, not_responded

    # Metadata
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<CalendarEventAttendee(event_id={self.event_id}, character_id={self.character_id}, response='{self.event_response}')>"
