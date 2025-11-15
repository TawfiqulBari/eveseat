"""
War models for tracking wars between corporations and alliances
"""
from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Boolean, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

from app.core.database import Base


class War(Base):
    """Wars between corporations and alliances"""
    __tablename__ = "wars"

    id = Column(Integer, primary_key=True, index=True)
    war_id = Column(Integer, unique=True, nullable=False, index=True)

    # Aggressor (attacker)
    aggressor_corporation_id = Column(BigInteger, index=True)
    aggressor_alliance_id = Column(Integer, ForeignKey("alliances.id"), index=True)
    aggressor_isk_destroyed = Column(BigInteger, default=0)
    aggressor_ships_killed = Column(Integer, default=0)

    # Defender
    defender_corporation_id = Column(BigInteger, index=True)
    defender_alliance_id = Column(Integer, ForeignKey("alliances.id"), index=True)
    defender_isk_destroyed = Column(BigInteger, default=0)
    defender_ships_killed = Column(Integer, default=0)

    # War details
    declared = Column(DateTime(timezone=True), nullable=False, index=True)
    started = Column(DateTime(timezone=True), index=True)
    finished = Column(DateTime(timezone=True), index=True)
    retracted = Column(DateTime(timezone=True))

    mutual = Column(Boolean, default=False)
    open_for_allies = Column(Boolean, default=False)

    # Status
    is_active = Column(Boolean, default=True, index=True)

    synced_at = Column(DateTime(timezone=True))

    # Relationships
    aggressor_alliance = relationship("Alliance", foreign_keys=[aggressor_alliance_id], back_populates="wars_as_aggressor")
    defender_alliance = relationship("Alliance", foreign_keys=[defender_alliance_id], back_populates="wars_as_defender")
    allies = relationship("WarAlly", back_populates="war", cascade="all, delete-orphan")
    killmails = relationship("WarKillmail", back_populates="war", cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_wars_active_started', 'is_active', 'started'),
    )


class WarAlly(Base):
    """Allies in a war"""
    __tablename__ = "war_allies"

    id = Column(Integer, primary_key=True, index=True)
    war_id = Column(Integer, ForeignKey("wars.id"), nullable=False, index=True)

    ally_corporation_id = Column(BigInteger, index=True)
    ally_alliance_id = Column(BigInteger, index=True)

    # Which side (aggressor or defender)
    side = Column(String(20), nullable=False)  # 'aggressor' or 'defender'

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    war = relationship("War", back_populates="allies")


class WarKillmail(Base):
    """Killmails associated with wars"""
    __tablename__ = "war_killmails"

    id = Column(Integer, primary_key=True, index=True)
    war_id = Column(Integer, ForeignKey("wars.id"), nullable=False, index=True)
    killmail_id = Column(BigInteger, nullable=False, index=True)

    killmail_time = Column(DateTime(timezone=True), nullable=False, index=True)
    victim_side = Column(String(20))  # 'aggressor' or 'defender'
    isk_value = Column(BigInteger)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    war = relationship("War", back_populates="killmails")

    __table_args__ = (
        Index('ix_war_killmails_war_time', 'war_id', 'killmail_time'),
    )
