"""
Blueprint models for blueprint tracking
"""
from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class Blueprint(Base):
    """Blueprint model - tracks character blueprints"""
    __tablename__ = "blueprints"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False, index=True)
    item_id = Column(BigInteger, unique=True, nullable=False, index=True)

    # Blueprint details
    type_id = Column(Integer, nullable=False, index=True)
    location_id = Column(BigInteger, nullable=False, index=True)
    location_flag = Column(String(50), nullable=False)
    quantity = Column(Integer, default=1)

    # Blueprint stats
    time_efficiency = Column(Integer, default=0)  # TE level (0-20)
    material_efficiency = Column(Integer, default=0)  # ME level (0-10)
    runs = Column(Integer, default=-1)  # -1 for BPO, positive for BPC

    # Metadata
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    character = relationship("Character", back_populates="blueprints")


class BlueprintResearch(Base):
    """Blueprint research tracking"""
    __tablename__ = "blueprint_research"

    id = Column(Integer, primary_key=True, index=True)
    blueprint_id = Column(Integer, ForeignKey("blueprints.id"), nullable=False, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False, index=True)

    # Research details
    research_type = Column(String(50), nullable=False)  # ME, TE, copying, invention
    start_level = Column(Integer)
    target_level = Column(Integer)

    # Job tracking
    job_id = Column(BigInteger, index=True)
    status = Column(String(50))  # active, completed, cancelled
    start_date = Column(DateTime(timezone=True))
    end_date = Column(DateTime(timezone=True))

    # Metadata
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    blueprint = relationship("Blueprint")
    character = relationship("Character")
