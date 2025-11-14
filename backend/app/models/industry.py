"""
Industry models for jobs and facilities
"""
from sqlalchemy import Column, Integer, BigInteger, String, Float, Boolean, DateTime, ForeignKey, Text, DECIMAL
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

from app.core.database import Base


class IndustryJob(Base):
    """Industry job model"""
    __tablename__ = "industry_jobs"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False, index=True)
    job_id = Column(BigInteger, unique=True, nullable=False, index=True)

    # Job details
    installer_id = Column(BigInteger, nullable=False)
    facility_id = Column(BigInteger, nullable=False)
    location_id = Column(BigInteger, nullable=False)
    activity_id = Column(Integer, nullable=False)  # 1=manufacturing, 3=TE research, 4=ME research, 5=copying, 8=invention
    blueprint_id = Column(BigInteger, nullable=False)
    blueprint_type_id = Column(Integer, nullable=False)
    blueprint_location_id = Column(BigInteger, nullable=False)
    output_location_id = Column(BigInteger, nullable=False)

    # Product details
    product_type_id = Column(Integer)
    runs = Column(Integer, nullable=False)
    licensed_runs = Column(Integer)

    # Cost and probability
    cost = Column(DECIMAL(precision=20, scale=2))
    probability = Column(Float)

    # Timing
    status = Column(String(50), nullable=False)  # active, paused, ready, delivered, cancelled, reverted
    start_date = Column(DateTime(timezone=True), nullable=False, index=True)
    end_date = Column(DateTime(timezone=True), nullable=False, index=True)
    pause_date = Column(DateTime(timezone=True))
    completed_date = Column(DateTime(timezone=True))

    # Success metrics
    completed_character_id = Column(BigInteger)
    successful_runs = Column(Integer)

    # Metadata
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    character = relationship("Character", back_populates="industry_jobs")


class IndustryFacility(Base):
    """Industry facility/structure model"""
    __tablename__ = "industry_facilities"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False, index=True)
    facility_id = Column(BigInteger, unique=True, nullable=False, index=True)

    # Facility details
    owner_id = Column(BigInteger, nullable=False)
    solar_system_id = Column(BigInteger, nullable=False, index=True)
    type_id = Column(Integer)
    name = Column(String(255))

    # Bonuses (JSONB for flexible activity bonuses)
    # Format: {"manufacturing": {"material": 0.01, "time": 0.25}, "research_time": {"material": 0.0, "time": 0.25}}
    bonuses = Column(JSONB)

    # Tax rates
    tax = Column(Float)

    # Metadata
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    character = relationship("Character", back_populates="industry_facilities")


class IndustryActivity(Base):
    """Industry activity tracking for analytics"""
    __tablename__ = "industry_activities"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False, index=True)

    # Activity summary
    activity_id = Column(Integer, nullable=False, index=True)
    activity_name = Column(String(100))

    # Metrics
    total_jobs = Column(Integer, default=0)
    completed_jobs = Column(Integer, default=0)
    active_jobs = Column(Integer, default=0)
    total_runs = Column(Integer, default=0)
    total_cost = Column(DECIMAL(precision=20, scale=2), default=0)

    # Time period
    period_start = Column(DateTime(timezone=True), nullable=False, index=True)
    period_end = Column(DateTime(timezone=True), nullable=False)

    # Metadata
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    character = relationship("Character", back_populates="industry_activities")
