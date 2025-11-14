"""
Fleet models for fleet management and doctrine compliance
"""
from sqlalchemy import Column, Integer, BigInteger, DateTime, String, ForeignKey, Boolean, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Fleet(Base):
    """
    Fleet model
    
    Represents a fleet in EVE Online
    """
    __tablename__ = "fleets"
    
    id = Column(Integer, primary_key=True, index=True)
    fleet_id = Column(BigInteger, unique=True, nullable=False, index=True)  # EVE fleet ID
    
    # Fleet commander
    commander_character_id = Column(BigInteger, nullable=False, index=True)
    commander_character_name = Column(String(255), nullable=True)
    
    # Fleet details
    fleet_name = Column(String(255), nullable=True)
    is_free_move = Column(Boolean, default=False, nullable=False)
    is_registered = Column(Boolean, default=False, nullable=False)
    is_voice_enabled = Column(Boolean, default=False, nullable=False)
    motd = Column(String(1000), nullable=True)  # Message of the day
    
    # Doctrine
    doctrine_id = Column(Integer, ForeignKey("doctrines.id"), nullable=True, index=True)
    
    # Additional fleet data
    fleet_data = Column(JSONB, nullable=True)  # Additional ESI data
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    members = relationship("FleetMember", back_populates="fleet", cascade="all, delete-orphan")
    doctrine = relationship("Doctrine", back_populates="fleets")
    
    def __repr__(self):
        return f"<Fleet(id={self.id}, fleet_id={self.fleet_id}, commander={self.commander_character_id})>"


class FleetMember(Base):
    """
    Fleet member model
    
    Tracks members in a fleet
    """
    __tablename__ = "fleet_members"
    
    id = Column(Integer, primary_key=True, index=True)
    fleet_id = Column(BigInteger, ForeignKey("fleets.fleet_id", ondelete="CASCADE"), nullable=False, index=True)
    character_id = Column(BigInteger, nullable=False, index=True)
    character_name = Column(String(255), nullable=True)
    
    # Member details
    ship_type_id = Column(BigInteger, nullable=True, index=True)
    ship_type_name = Column(String(255), nullable=True)
    solar_system_id = Column(BigInteger, nullable=True, index=True)
    solar_system_name = Column(String(255), nullable=True)
    station_id = Column(BigInteger, nullable=True)
    station_name = Column(String(255), nullable=True)
    
    # Wing and squad
    wing_id = Column(BigInteger, nullable=True)
    squad_id = Column(BigInteger, nullable=True)
    role = Column(String(50), nullable=True)  # "fleet_commander", "squad_commander", etc.
    role_name = Column(String(255), nullable=True)
    takes_fleet_warp = Column(Boolean, default=True, nullable=False)
    
    # Additional member data
    member_data = Column(JSONB, nullable=True)  # Additional ESI data
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    fleet = relationship("Fleet", back_populates="members")
    
    # Indexes
    __table_args__ = (
        Index("idx_fleet_members_fleet_character", "fleet_id", "character_id", unique=True),
    )
    
    def __repr__(self):
        return f"<FleetMember(id={self.id}, fleet_id={self.fleet_id}, character_id={self.character_id})>"


class Doctrine(Base):
    """
    Doctrine model
    
    Stores ship doctrine definitions (ship types, fits, etc.)
    """
    __tablename__ = "doctrines"
    
    id = Column(Integer, primary_key=True, index=True)
    doctrine_name = Column(String(255), nullable=False, index=True)
    doctrine_description = Column(String(2000), nullable=True)
    
    # Doctrine definition (JSONB for flexibility)
    # Structure: {
    #   "ships": [
    #     {"type_id": 123, "type_name": "Ship Name", "role": "dps", "fit": {...}},
    #     ...
    #   ],
    #   "roles": ["dps", "logi", "tackle", ...],
    #   "requirements": {...}
    # }
    doctrine_definition = Column(JSONB, nullable=False)
    
    # Doctrine metadata
    is_active = Column(Boolean, default=True, nullable=False)
    created_by_character_id = Column(BigInteger, nullable=True)
    created_by_character_name = Column(String(255), nullable=True)
    
    # Additional doctrine data
    doctrine_data = Column(JSONB, nullable=True)  # Additional metadata
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    fleets = relationship("Fleet", back_populates="doctrine")
    
    def __repr__(self):
        return f"<Doctrine(id={self.id}, doctrine_name='{self.doctrine_name}')>"

