"""
Skill models for character skills tracking
"""
from sqlalchemy import Column, Integer, BigInteger, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class Skill(Base):
    """Character skill model"""
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False, index=True)
    skill_id = Column(Integer, nullable=False, index=True)

    # Skill details
    active_skill_level = Column(Integer, nullable=False)
    trained_skill_level = Column(Integer, nullable=False)
    skillpoints_in_skill = Column(BigInteger, nullable=False)

    # Metadata
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    character = relationship("Character", back_populates="skills")


class SkillQueue(Base):
    """Character skill queue model"""
    __tablename__ = "skill_queue"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False, index=True)
    skill_id = Column(Integer, nullable=False, index=True)

    # Queue details
    queue_position = Column(Integer, nullable=False)
    finished_level = Column(Integer, nullable=False)
    start_date = Column(DateTime(timezone=True))
    finish_date = Column(DateTime(timezone=True))
    training_start_sp = Column(Integer)
    level_start_sp = Column(Integer)
    level_end_sp = Column(Integer)

    # Metadata
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    character = relationship("Character", back_populates="skill_queue")


class SkillPlan(Base):
    """Custom skill training plans"""
    __tablename__ = "skill_plans"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False, index=True)

    # Plan details
    name = Column(String(255), nullable=False)
    description = Column(String(1000))
    is_active = Column(Boolean, default=False)

    # Skills in plan (ordered list)
    # Format: [{"skill_id": 123, "level": 5, "priority": 1}, ...]
    skills = Column(String)  # JSON string

    # Metadata
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    character = relationship("Character", back_populates="skill_plans")
