"""
Universe models for EVE Online map and route planning
"""
from sqlalchemy import Column, Integer, BigInteger, Float, String, DateTime, Index, ForeignKey, Text, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from geoalchemy2 import Geometry
from sqlalchemy.sql import func
from app.core.database import Base


class System(Base):
    """
    EVE Online system model
    
    Stores system information including coordinates for map rendering
    """
    __tablename__ = "systems"
    
    id = Column(Integer, primary_key=True, index=True)
    system_id = Column(BigInteger, unique=True, nullable=False, index=True)  # EVE system ID
    system_name = Column(String(255), nullable=False, index=True)
    
    # Location hierarchy
    constellation_id = Column(BigInteger, nullable=False, index=True)
    constellation_name = Column(String(255), nullable=True)
    region_id = Column(BigInteger, nullable=False, index=True)
    region_name = Column(String(255), nullable=True)
    
    # Coordinates (for map rendering)
    x = Column(Float, nullable=True)
    y = Column(Float, nullable=True)
    z = Column(Float, nullable=True)
    
    # Security status
    security_status = Column(Float, nullable=False, index=True)  # -1.0 to 1.0
    security_class = Column(String(10), nullable=True)  # e.g., "A", "B", "C", "0.0", "-1.0"
    
    # System type
    system_type = Column(String(50), nullable=True)  # e.g., "k-space", "w-space"
    
    # Additional system data
    system_data = Column(JSONB, nullable=True)  # Additional ESI data
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Indexes
    __table_args__ = (
        Index("idx_systems_region_constellation", "region_id", "constellation_id"),
        Index("idx_systems_security_status", "security_status"),
    )
    
    def __repr__(self):
        return f"<System(id={self.id}, system_id={self.system_id}, system_name='{self.system_name}', security={self.security_status})>"


class SystemJump(Base):
    """
    System jump connections (stargate connections)
    
    Represents the graph of stargate connections between systems
    """
    __tablename__ = "system_jumps"
    
    id = Column(Integer, primary_key=True, index=True)
    from_system_id = Column(BigInteger, ForeignKey("systems.system_id"), nullable=False, index=True)
    to_system_id = Column(BigInteger, ForeignKey("systems.system_id"), nullable=False, index=True)
    
    # Stargate information
    stargate_id = Column(BigInteger, nullable=True, unique=True, index=True)
    
    # Jump metadata
    jump_data = Column(JSONB, nullable=True)  # Additional stargate data
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Indexes for efficient route queries
    __table_args__ = (
        Index("idx_system_jumps_from_to", "from_system_id", "to_system_id"),
        Index("idx_system_jumps_to_from", "to_system_id", "from_system_id"),
    )
    
    def __repr__(self):
        return f"<SystemJump(id={self.id}, from={self.from_system_id}, to={self.to_system_id})>"


class SystemActivity(Base):
    """
    System activity tracking
    
    Time-series data for system activity (kills, jumps, etc.)
    """
    __tablename__ = "system_activity"
    
    id = Column(Integer, primary_key=True, index=True)
    system_id = Column(BigInteger, ForeignKey("systems.system_id"), nullable=False, index=True)
    
    # Activity metrics
    kills_last_hour = Column(Integer, default=0, nullable=False)
    jumps_last_hour = Column(Integer, default=0, nullable=False)
    npc_kills_last_hour = Column(Integer, default=0, nullable=False)
    pod_kills_last_hour = Column(Integer, default=0, nullable=False)
    ship_kills_last_hour = Column(Integer, default=0, nullable=False)
    
    # Timestamp for this activity snapshot
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Additional activity data
    activity_data = Column(JSONB, nullable=True)  # Additional metrics
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Indexes for efficient time-series queries
    __table_args__ = (
        Index("idx_system_activity_system_timestamp", "system_id", "timestamp", postgresql_ops={"timestamp": "DESC"}),
        Index("idx_system_activity_timestamp_desc", "timestamp", postgresql_ops={"timestamp": "DESC"}),
    )
    
    def __repr__(self):
        return f"<SystemActivity(id={self.id}, system_id={self.system_id}, timestamp='{self.timestamp}', kills={self.kills_last_hour})>"


class UniverseType(Base):
    """
    Universe type cache model
    
    Caches item type information from ESI to reduce API calls.
    Type information changes infrequently, so caching is very effective.
    """
    __tablename__ = "universe_types"
    
    id = Column(Integer, primary_key=True, index=True)
    type_id = Column(BigInteger, unique=True, nullable=False, index=True)  # EVE type ID
    
    # Basic type information
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Type hierarchy
    group_id = Column(BigInteger, nullable=True, index=True)
    group_name = Column(String(255), nullable=True)
    category_id = Column(BigInteger, nullable=True, index=True)
    category_name = Column(String(255), nullable=True)
    
    # Type metadata
    mass = Column(Float, nullable=True)
    volume = Column(Float, nullable=True)
    capacity = Column(Float, nullable=True)
    portion_size = Column(Integer, nullable=True)
    published = Column(Boolean, default=True, nullable=False)
    
    # Icon and graphic information
    icon_id = Column(Integer, nullable=True)
    icon_url = Column(String(500), nullable=True)  # Pre-computed icon URL
    
    # Additional type data from ESI
    type_data = Column(JSONB, nullable=True)  # Full ESI type response
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    
    # Indexes for efficient lookups
    __table_args__ = (
        Index("idx_universe_types_group", "group_id"),
        Index("idx_universe_types_category", "category_id"),
        Index("idx_universe_types_name", "name"),
    )
    
    def __repr__(self):
        return f"<UniverseType(id={self.id}, type_id={self.type_id}, name='{self.name}')>"

