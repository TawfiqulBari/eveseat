"""
Planetary Interaction models
"""
from sqlalchemy import Column, Integer, BigInteger, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from datetime import datetime

from app.core.database import Base


class Planet(Base):
    """Character planet model"""
    __tablename__ = "planets"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False, index=True)
    planet_id = Column(BigInteger, unique=True, nullable=False, index=True)

    # Planet details
    solar_system_id = Column(BigInteger, nullable=False, index=True)
    planet_type = Column(String(50), nullable=False)  # temperate, barren, oceanic, etc.
    owner_id = Column(BigInteger, nullable=False)

    # Upgrade level
    upgrade_level = Column(Integer, default=0)
    num_pins = Column(Integer, default=0)

    # Last update
    last_update = Column(DateTime(timezone=True))

    # Metadata
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    character = relationship("Character", back_populates="planets")
    pins = relationship("PlanetPin", back_populates="planet", cascade="all, delete-orphan")
    routes = relationship("PlanetRoute", back_populates="planet", cascade="all, delete-orphan")


class PlanetPin(Base):
    """Planet pin (extractor, factory, storage, etc.)"""
    __tablename__ = "planet_pins"

    id = Column(Integer, primary_key=True, index=True)
    planet_id = Column(Integer, ForeignKey("planets.id"), nullable=False, index=True)
    pin_id = Column(BigInteger, unique=True, nullable=False, index=True)

    # Pin details
    type_id = Column(Integer, nullable=False)
    schematic_id = Column(Integer)  # For processors
    latitude = Column(Float)
    longitude = Column(Float)

    # Extractor details (if applicable)
    install_time = Column(DateTime(timezone=True))
    expiry_time = Column(DateTime(timezone=True))
    product_type_id = Column(Integer)
    cycle_time = Column(Integer)
    quantity_per_cycle = Column(Integer)

    # Contents (JSONB for flexibility)
    # Format: [{"type_id": 2268, "amount": 5000}, ...]
    contents = Column(JSONB)

    # Metadata
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    planet = relationship("Planet", back_populates="pins")


class PlanetRoute(Base):
    """Planet route between pins"""
    __tablename__ = "planet_routes"

    id = Column(Integer, primary_key=True, index=True)
    planet_id = Column(Integer, ForeignKey("planets.id"), nullable=False, index=True)
    route_id = Column(BigInteger, unique=True, nullable=False, index=True)

    # Route details
    source_pin_id = Column(BigInteger, nullable=False)
    destination_pin_id = Column(BigInteger, nullable=False)
    content_type_id = Column(Integer, nullable=False)
    quantity = Column(Float, nullable=False)

    # Metadata
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    planet = relationship("Planet", back_populates="routes")


class PlanetExtraction(Base):
    """Tracks active planet extractions"""
    __tablename__ = "planet_extractions"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False, index=True)
    planet_id = Column(BigInteger, nullable=False, index=True)
    pin_id = Column(BigInteger, nullable=False, index=True)

    # Extraction details
    product_type_id = Column(Integer, nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    expiry_time = Column(DateTime(timezone=True), nullable=False, index=True)
    cycle_time = Column(Integer)
    quantity_per_cycle = Column(Integer)

    # Status
    status = Column(String(50), default="active")  # active, expired, collected

    # Metadata
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    character = relationship("Character")
