"""
Faction Warfare models for tracking FW statistics and systems
"""
from sqlalchemy import Column, Integer, BigInteger, String, Float, DateTime, Boolean, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

from app.core.database import Base


class FactionWarfareSystem(Base):
    """Faction warfare system control"""
    __tablename__ = "faction_warfare_systems"

    id = Column(Integer, primary_key=True, index=True)
    solar_system_id = Column(Integer, unique=True, nullable=False, index=True)

    # System details
    occupier_faction_id = Column(Integer, nullable=False, index=True)
    owner_faction_id = Column(Integer, nullable=False, index=True)
    contested = Column(String(20), nullable=False)  # 'contested', 'uncontested', 'vulnerable'
    victory_points = Column(Integer, default=0)
    victory_points_threshold = Column(Integer, default=3000)

    synced_at = Column(DateTime(timezone=True))

    __table_args__ = (
        Index('ix_fw_systems_occupier', 'occupier_faction_id', 'contested'),
    )


class FactionWarfareStatistics(Base):
    """Faction warfare statistics by faction"""
    __tablename__ = "faction_warfare_statistics"

    id = Column(Integer, primary_key=True, index=True)
    faction_id = Column(Integer, nullable=False, index=True)
    date = Column(DateTime(timezone=True), nullable=False, index=True)

    # Kills
    kills_yesterday = Column(Integer, default=0)
    kills_last_week = Column(Integer, default=0)
    kills_total = Column(Integer, default=0)

    # Victory points
    victory_points_yesterday = Column(Integer, default=0)
    victory_points_last_week = Column(Integer, default=0)
    victory_points_total = Column(Integer, default=0)

    # Pilots enrolled
    pilots = Column(Integer, default=0)
    systems_controlled = Column(Integer, default=0)

    synced_at = Column(DateTime(timezone=True))

    __table_args__ = (
        Index('ix_fw_stats_faction_date', 'faction_id', 'date'),
    )


class CharacterFactionWarfare(Base):
    """Character faction warfare enrollment and statistics"""
    __tablename__ = "character_faction_warfare"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, unique=True, nullable=False, index=True)

    # Enrollment
    faction_id = Column(Integer, nullable=False, index=True)
    enlisted = Column(DateTime(timezone=True))
    current_rank = Column(Integer, default=0)

    # Statistics
    kills_yesterday = Column(Integer, default=0)
    kills_last_week = Column(Integer, default=0)
    kills_total = Column(Integer, default=0)

    victory_points_yesterday = Column(Integer, default=0)
    victory_points_last_week = Column(Integer, default=0)
    victory_points_total = Column(Integer, default=0)

    synced_at = Column(DateTime(timezone=True))


class FactionWarfareLeaderboard(Base):
    """Faction warfare kill leaderboard"""
    __tablename__ = "faction_warfare_leaderboard"

    id = Column(Integer, primary_key=True, index=True)
    faction_id = Column(Integer, nullable=False, index=True)
    date = Column(DateTime(timezone=True), nullable=False, index=True)

    # Leaderboard type
    leaderboard_type = Column(String(50), nullable=False)  # 'kills', 'victory_points'
    timeframe = Column(String(20), nullable=False)  # 'yesterday', 'last_week', 'total'

    # Top entries
    entries = Column(JSON)  # [{character_id, character_name, amount, rank}]

    synced_at = Column(DateTime(timezone=True))

    __table_args__ = (
        Index('ix_fw_leaderboard_faction_type', 'faction_id', 'leaderboard_type', 'timeframe'),
    )


class FactionWarfareSystemHistory(Base):
    """Historical faction warfare system captures"""
    __tablename__ = "faction_warfare_system_history"

    id = Column(Integer, primary_key=True, index=True)
    solar_system_id = Column(Integer, nullable=False, index=True)
    captured_at = Column(DateTime(timezone=True), nullable=False, index=True)

    # Capture details
    from_faction_id = Column(Integer, nullable=False)
    to_faction_id = Column(Integer, nullable=False)

    # Siege duration
    siege_started_at = Column(DateTime(timezone=True))
    siege_duration_hours = Column(Integer)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('ix_fw_history_system_captured', 'solar_system_id', 'captured_at'),
    )
