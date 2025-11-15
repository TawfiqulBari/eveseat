"""
Structure models for EVE Online structures (Citadels, Engineering Complexes, etc.)
"""
from sqlalchemy import Column, Integer, BigInteger, String, Float, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base


class Structure(Base):
    """Corporation structure model"""
    __tablename__ = "structures"

    id = Column(Integer, primary_key=True, index=True)
    corporation_id = Column(Integer, ForeignKey("corporations.id"), nullable=False, index=True)
    structure_id = Column(BigInteger, unique=True, nullable=False, index=True)

    # Basic information
    name = Column(String(255))
    type_id = Column(Integer, nullable=False, index=True)  # Structure type
    system_id = Column(Integer, nullable=False, index=True)

    # Position
    position_x = Column(Float)
    position_y = Column(Float)
    position_z = Column(Float)

    # State and fuel
    state = Column(String(50), index=True)  # online, offline, anchoring, unanchoring, etc.
    state_timer_start = Column(DateTime(timezone=True))
    state_timer_end = Column(DateTime(timezone=True))
    unanchors_at = Column(DateTime(timezone=True))

    # Fuel and reinforcement
    fuel_expires = Column(DateTime(timezone=True))
    next_reinforce_hour = Column(Integer)
    next_reinforce_day = Column(Integer)

    # Services
    services = Column(JSON)  # Array of active services

    # Metadata
    profile_id = Column(Integer)
    reinforce_hour = Column(Integer)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default="NOW()")
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default="NOW()", onupdate="NOW()")
    synced_at = Column(DateTime(timezone=True))

    # Relationships
    corporation = relationship("Corporation", back_populates="structures")
    vulnerabilities = relationship("StructureVulnerability", back_populates="structure", cascade="all, delete-orphan")


class StructureVulnerability(Base):
    """Structure vulnerability window model"""
    __tablename__ = "structure_vulnerabilities"

    id = Column(Integer, primary_key=True, index=True)
    structure_id = Column(Integer, ForeignKey("structures.id"), nullable=False, index=True)

    # Vulnerability window
    day_of_week = Column(Integer, nullable=False)  # 0 = Monday, 6 = Sunday
    hour = Column(Integer, nullable=False)  # 0-23

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default="NOW()")

    # Relationships
    structure = relationship("Structure", back_populates="vulnerabilities")


class StructureService(Base):
    """Structure service model"""
    __tablename__ = "structure_services"

    id = Column(Integer, primary_key=True, index=True)
    structure_id = Column(Integer, ForeignKey("structures.id"), nullable=False, index=True)

    # Service information
    name = Column(String(100), nullable=False)
    state = Column(String(50), nullable=False)  # online, offline

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default="NOW()")
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default="NOW()", onupdate="NOW()")

    # Relationships
    structure = relationship("Structure")
