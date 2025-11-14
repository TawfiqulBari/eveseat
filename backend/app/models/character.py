"""
Character model - represents an EVE Online character
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, BigInteger, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Character(Base):
    """
    Character model - represents an EVE Online character
    
    Stores character information synced from ESI API
    """
    __tablename__ = "characters"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    character_id = Column(BigInteger, unique=True, nullable=False, index=True)  # EVE character ID
    character_name = Column(String(255), nullable=False, index=True)
    
    # Character details from ESI
    corporation_id = Column(BigInteger, nullable=True, index=True)
    corporation_name = Column(String(255), nullable=True)
    alliance_id = Column(BigInteger, nullable=True, index=True)
    alliance_name = Column(String(255), nullable=True)
    
    # Character metadata
    security_status = Column(String(20), nullable=True)  # e.g., "0.5", "-1.2"
    birthday = Column(DateTime(timezone=True), nullable=True)  # Character creation date
    gender = Column(String(20), nullable=True)
    race_id = Column(Integer, nullable=True)
    bloodline_id = Column(Integer, nullable=True)
    ancestry_id = Column(Integer, nullable=True)
    
    # Additional character data (JSONB for flexibility)
    character_data = Column(JSON, nullable=True)  # Store additional ESI data
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="characters")
    eve_token = relationship("EveToken", foreign_keys="EveToken.character_id", primaryjoin="Character.character_id == EveToken.character_id", uselist=False)
    mails = relationship("Mail", back_populates="character", cascade="all, delete-orphan")
    mail_labels = relationship("MailLabel", back_populates="character", cascade="all, delete-orphan")
    mailing_lists = relationship("MailingList", back_populates="character", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Character(id={self.id}, character_id={self.character_id}, character_name='{self.character_name}')>"

