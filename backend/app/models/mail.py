"""
Mail models

EVE Online in-game mail system
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, BigInteger, ARRAY
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base


class Mail(Base):
    """In-game mail messages"""

    __tablename__ = "mails"

    # EVE mail data
    mail_id = Column(BigInteger, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False, index=True)
    from_id = Column(BigInteger, index=True)  # Character or mailing list ID
    subject = Column(String(255))
    body = Column(Text)  # Mail body content
    timestamp = Column(DateTime(timezone=True), index=True)
    is_read = Column(Boolean, default=False, index=True)

    # Recipients (array of recipient IDs)
    recipients = Column(JSONB)  # [{recipient_id, recipient_type}]

    # Labels
    labels = Column(ARRAY(Integer))  # Array of label IDs

    # Metadata
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    character = relationship("Character", back_populates="mails")

    def __repr__(self):
        return f"<Mail(mail_id={self.mail_id}, from_id={self.from_id}, subject='{self.subject[:30]}')>"


class MailLabel(Base):
    """Mail labels/folders"""

    __tablename__ = "mail_labels"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False, index=True)
    label_id = Column(Integer)  # EVE label ID
    name = Column(String(255))
    color = Column(String(20))  # Hex color code
    unread_count = Column(Integer, default=0)

    # Metadata
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    character = relationship("Character", back_populates="mail_labels")

    def __repr__(self):
        return f"<MailLabel(label_id={self.label_id}, name='{self.name}')>"


class MailingList(Base):
    """Mailing lists the character is subscribed to"""

    __tablename__ = "mailing_lists"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False, index=True)
    mailing_list_id = Column(BigInteger, index=True)
    name = Column(String(255))

    # Metadata
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    character = relationship("Character", back_populates="mailing_lists")

    def __repr__(self):
        return f"<MailingList(mailing_list_id={self.mailing_list_id}, name='{self.name}')>"
