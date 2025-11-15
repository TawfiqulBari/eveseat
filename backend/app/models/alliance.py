"""
Alliance models for alliance management and tracking
"""
from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Boolean, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

from app.core.database import Base


class Alliance(Base):
    """Alliance information and tracking"""
    __tablename__ = "alliances"

    id = Column(Integer, primary_key=True, index=True)
    alliance_id = Column(BigInteger, unique=True, nullable=False, index=True)
    alliance_name = Column(String(255), nullable=False, index=True)
    ticker = Column(String(10))

    # Alliance details
    executor_corporation_id = Column(BigInteger, index=True)
    executor_corporation_name = Column(String(255))
    creator_id = Column(BigInteger)
    creator_corporation_id = Column(BigInteger)
    date_founded = Column(DateTime(timezone=True))

    # Statistics
    member_count = Column(Integer, default=0)
    corporation_count = Column(Integer, default=0)

    # Faction warfare
    faction_id = Column(Integer, index=True)  # If enrolled in FW

    # Metadata
    is_closed = Column(Boolean, default=False)
    alliance_data = Column(JSON)  # Additional ESI data

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    synced_at = Column(DateTime(timezone=True))

    # Relationships
    corporations = relationship("AllianceCorporation", back_populates="alliance", cascade="all, delete-orphan")
    wars_as_aggressor = relationship("War", foreign_keys="War.aggressor_alliance_id", back_populates="aggressor_alliance")
    wars_as_defender = relationship("War", foreign_keys="War.defender_alliance_id", back_populates="defender_alliance")


class AllianceCorporation(Base):
    """Corporations in an alliance"""
    __tablename__ = "alliance_corporations"

    id = Column(Integer, primary_key=True, index=True)
    alliance_id = Column(Integer, ForeignKey("alliances.id"), nullable=False, index=True)
    corporation_id = Column(BigInteger, nullable=False, index=True)
    corporation_name = Column(String(255))

    joined_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    alliance = relationship("Alliance", back_populates="corporations")

    __table_args__ = (
        Index('ix_alliance_corps_alliance_corp', 'alliance_id', 'corporation_id', unique=True),
    )


class AllianceContact(Base):
    """Alliance contacts and standings"""
    __tablename__ = "alliance_contacts"

    id = Column(Integer, primary_key=True, index=True)
    alliance_id = Column(BigInteger, nullable=False, index=True)
    contact_id = Column(BigInteger, nullable=False, index=True)
    contact_type = Column(String(50))  # character, corporation, alliance

    standing = Column(Integer, nullable=False)  # -10 to +10
    label_ids = Column(JSON)

    synced_at = Column(DateTime(timezone=True))

    __table_args__ = (
        Index('ix_alliance_contacts_alliance_contact', 'alliance_id', 'contact_id', unique=True),
    )
