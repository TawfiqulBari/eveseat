"""
Clone models for jump clones and implants
"""
from sqlalchemy import Column, Integer, BigInteger, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import ARRAY
from datetime import datetime

from app.core.database import Base


class Clone(Base):
    """Jump clone model"""
    __tablename__ = "clones"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False, index=True)
    jump_clone_id = Column(BigInteger, unique=True, nullable=False, index=True)

    # Clone details
    name = Column(String(255))
    location_id = Column(BigInteger, nullable=False, index=True)
    location_type = Column(String(50))  # station, structure

    # Implants (array of type IDs)
    implants = Column(ARRAY(Integer), default=list)

    # Metadata
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    character = relationship("Character", back_populates="clones")


class ActiveImplant(Base):
    """Active implants in current clone"""
    __tablename__ = "active_implants"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False, index=True)
    type_id = Column(Integer, nullable=False, index=True)

    # Implant details
    name = Column(String(255))
    slot = Column(Integer)  # 1-10 for different implant slots

    # Metadata
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    character = relationship("Character", back_populates="active_implants")


class JumpCloneHistory(Base):
    """Jump clone usage history"""
    __tablename__ = "jump_clone_history"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False, index=True)

    # Jump details
    jump_date = Column(DateTime(timezone=True), nullable=False, index=True)
    from_location_id = Column(BigInteger)
    to_location_id = Column(BigInteger)
    to_clone_id = Column(BigInteger)

    # Metadata
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    character = relationship("Character")
