"""
Moon mining models for tracking extractions and operations
"""
from sqlalchemy import Column, Integer, BigInteger, String, Float, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base


class MoonExtraction(Base):
    """Moon extraction model"""
    __tablename__ = "moon_extractions"

    id = Column(Integer, primary_key=True, index=True)
    structure_id = Column(BigInteger, nullable=False, index=True)
    corporation_id = Column(Integer, ForeignKey("corporations.id"), nullable=False, index=True)

    # Moon information
    moon_id = Column(Integer, nullable=False, index=True)

    # Extraction timing
    chunk_arrival_time = Column(DateTime(timezone=True), nullable=False, index=True)
    extraction_start_time = Column(DateTime(timezone=True), nullable=False)
    natural_decay_time = Column(DateTime(timezone=True))

    # Status
    status = Column(String(50), index=True)  # started, ready, collected, cancelled

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default="NOW()")
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default="NOW()", onupdate="NOW()")
    synced_at = Column(DateTime(timezone=True))

    # Relationships
    corporation = relationship("Corporation", back_populates="moon_extractions")


class Moon(Base):
    """Moon information and composition"""
    __tablename__ = "moons"

    id = Column(Integer, primary_key=True, index=True)
    moon_id = Column(Integer, unique=True, nullable=False, index=True)

    # Location
    system_id = Column(Integer, nullable=False, index=True)
    name = Column(String(255))

    # Moon composition (if scanned)
    composition = Column(JSON)  # {type_id: percentage}
    estimated_value = Column(BigInteger)  # ISK value estimate

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default="NOW()")
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default="NOW()", onupdate="NOW()")
    last_scanned = Column(DateTime(timezone=True))


class MiningLedger(Base):
    """Corporation mining ledger entries"""
    __tablename__ = "mining_ledger"

    id = Column(Integer, primary_key=True, index=True)
    corporation_id = Column(Integer, ForeignKey("corporations.id"), nullable=False, index=True)
    character_id = Column(Integer, nullable=False, index=True)

    # Mining details
    date = Column(DateTime(timezone=True), nullable=False, index=True)
    type_id = Column(Integer, nullable=False, index=True)
    quantity = Column(BigInteger, nullable=False)
    system_id = Column(Integer, nullable=False, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default="NOW()")

    # Relationships
    corporation = relationship("Corporation", back_populates="mining_ledger")
