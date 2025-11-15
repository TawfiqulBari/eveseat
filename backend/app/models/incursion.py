"""
Incursion models for tracking Sansha incursions
"""
from sqlalchemy import Column, Integer, BigInteger, String, Float, DateTime, Boolean, JSON, Index
from sqlalchemy.sql import func
from datetime import datetime

from app.core.database import Base


class Incursion(Base):
    """Active Sansha incursions"""
    __tablename__ = "incursions"

    id = Column(Integer, primary_key=True, index=True)
    constellation_id = Column(Integer, unique=True, nullable=False, index=True)

    # Incursion details
    state = Column(String(50), nullable=False, index=True)  # 'mobilizing', 'established', 'withdrawing'
    faction_id = Column(Integer, nullable=False)  # Always Sansha (500019)
    influence = Column(Float, default=0)  # 0.0 to 1.0

    # Staging system
    staging_solar_system_id = Column(Integer, index=True)

    # Systems affected
    infested_solar_systems = Column(JSON)  # List of system IDs

    # Boss information
    has_boss = Column(Boolean, default=False)
    boss_defeated = Column(Boolean, default=False)

    # Timestamps
    started_at = Column(DateTime(timezone=True))
    estimated_end_at = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    synced_at = Column(DateTime(timezone=True))

    __table_args__ = (
        Index('ix_incursions_active_state', 'is_active', 'state'),
    )


class IncursionStatistics(Base):
    """Historical incursion statistics"""
    __tablename__ = "incursion_statistics"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime(timezone=True), nullable=False, index=True)

    # Statistics
    total_active = Column(Integer, default=0)
    total_mobilizing = Column(Integer, default=0)
    total_established = Column(Integer, default=0)
    total_withdrawing = Column(Integer, default=0)

    # By region
    incursions_by_region = Column(JSON)  # {region_id: count}

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('ix_incursion_stats_date', 'date', unique=True),
    )


class IncursionParticipation(Base):
    """Character participation in incursions"""
    __tablename__ = "incursion_participation"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, nullable=False, index=True)
    incursion_constellation_id = Column(Integer, nullable=False, index=True)

    # Participation details
    sites_completed = Column(Integer, default=0)
    isk_earned = Column(BigInteger, default=0)
    lp_earned = Column(BigInteger, default=0)

    # Timestamps
    first_participation = Column(DateTime(timezone=True))
    last_participation = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index('ix_incursion_participation_char_constellation', 'character_id', 'incursion_constellation_id'),
    )
