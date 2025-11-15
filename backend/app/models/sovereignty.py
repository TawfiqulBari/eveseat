"""
Sovereignty models for tracking system and constellation sovereignty
"""
from sqlalchemy import Column, Integer, BigInteger, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base


class SystemSovereignty(Base):
    """System sovereignty information"""
    __tablename__ = "system_sovereignty"

    id = Column(Integer, primary_key=True, index=True)
    system_id = Column(Integer, unique=True, nullable=False, index=True)

    # Ownership
    alliance_id = Column(Integer, index=True)
    corporation_id = Column(Integer, index=True)
    faction_id = Column(Integer, index=True)

    # Indexes
    ihub_vulnerability_timer = Column(Float)  # Activity Defense Multiplier
    tcu_vulnerability_timer = Column(Float)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default="NOW()")
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default="NOW()", onupdate="NOW()")
    synced_at = Column(DateTime(timezone=True))


class SovereigntyStructure(Base):
    """Sovereignty structures (TCU, IHUB)"""
    __tablename__ = "sovereignty_structures"

    id = Column(Integer, primary_key=True, index=True)
    structure_id = Column(BigInteger, unique=True, nullable=False, index=True)

    # Location
    system_id = Column(Integer, nullable=False, index=True)
    structure_type_id = Column(Integer, nullable=False)  # TCU or IHUB type

    # Ownership
    alliance_id = Column(Integer, nullable=False, index=True)

    # Vulnerability
    vulnerable_start_time = Column(DateTime(timezone=True))
    vulnerable_end_time = Column(DateTime(timezone=True))
    vulnerability_occupancy_level = Column(Float)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default="NOW()")
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default="NOW()", onupdate="NOW()")
    synced_at = Column(DateTime(timezone=True))


class SovereigntyCampaign(Base):
    """Ongoing sovereignty campaigns (contests)"""
    __tablename__ = "sovereignty_campaigns"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, unique=True, nullable=False, index=True)

    # Location
    system_id = Column(Integer, nullable=False, index=True)
    constellation_id = Column(Integer, nullable=False, index=True)

    # Structure under attack
    structure_id = Column(BigInteger, nullable=False)
    event_type = Column(String(100), nullable=False)  # tcu_defense, ihub_defense, station_defense

    # Participants
    defender_id = Column(Integer, index=True)  # Alliance ID
    defender_score = Column(Float, default=0)

    attackers_score = Column(Float, default=0)

    # Timing
    start_time = Column(DateTime(timezone=True), nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default="NOW()")
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default="NOW()", onupdate="NOW()")
    synced_at = Column(DateTime(timezone=True))
