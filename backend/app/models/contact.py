"""
Contact models

EVE Online contacts system
"""
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, BigInteger, ARRAY
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base


class Contact(Base):
    """Character or corporation contacts"""

    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False, index=True)
    contact_id = Column(BigInteger, index=True)  # EVE entity ID (character/corp/alliance)
    contact_type = Column(String(50))  # character, corporation, alliance, faction
    standing = Column(Float)  # -10.0 to +10.0
    is_watched = Column(String(20), default=False)  # Watched list flag
    is_blocked = Column(String(20), default=False)  # Blocked flag

    # Contact labels (array of label IDs)
    label_ids = Column(ARRAY(Integer), default=[])

    # Metadata
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    character = relationship("Character", back_populates="contacts")

    def __repr__(self):
        return f"<Contact(contact_id={self.contact_id}, type='{self.contact_type}', standing={self.standing})>"


class ContactLabel(Base):
    """Contact labels/tags"""

    __tablename__ = "contact_labels"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False, index=True)
    label_id = Column(BigInteger)  # EVE label ID
    name = Column(String(255))

    # Metadata
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    character = relationship("Character", back_populates="contact_labels")

    def __repr__(self):
        return f"<ContactLabel(label_id={self.label_id}, name='{self.name}')>"
