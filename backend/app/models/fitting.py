"""
Fitting models for ship fittings management
"""
from sqlalchemy import Column, Integer, BigInteger, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

from app.core.database import Base


class Fitting(Base):
    """Ship fitting model"""
    __tablename__ = "fittings"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False, index=True)
    fitting_id = Column(BigInteger, unique=True, nullable=False, index=True)

    # Fitting details
    name = Column(String(255), nullable=False)
    description = Column(Text)
    ship_type_id = Column(Integer, nullable=False, index=True)

    # Items (modules, rigs, cargo, etc.)
    # Format: [{"type_id": 123, "flag": "HiSlot0", "quantity": 1}, ...]
    items = Column(JSONB, nullable=False, default=list)

    # Metadata
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    character = relationship("Character", back_populates="fittings")


class FittingAnalysis(Base):
    """Fitting analysis and simulation results"""
    __tablename__ = "fitting_analysis"

    id = Column(Integer, primary_key=True, index=True)
    fitting_id = Column(Integer, ForeignKey("fittings.id"), nullable=False, index=True)

    # Calculated stats (stored as JSONB for flexibility)
    # Format: {"ehp": 50000, "dps": 500, "cap_stable": true, "speed": 1500, ...}
    stats = Column(JSONB)

    # Analysis metadata
    analyzed_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    version = Column(String(50))  # EVE version when analyzed

    # Relationships
    fitting = relationship("Fitting")
