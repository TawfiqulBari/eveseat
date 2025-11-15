"""
Corporation models
"""
from sqlalchemy import Column, Integer, BigInteger, DateTime, String, ForeignKey, Boolean, Index, Float
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Corporation(Base):
    """
    Corporation model - stores EVE Online corporation information
    """
    __tablename__ = "corporations"
    
    id = Column(Integer, primary_key=True, index=True)
    corporation_id = Column(BigInteger, unique=True, nullable=False, index=True)  # EVE corporation ID
    corporation_name = Column(String(255), nullable=False, index=True)
    
    # Corporation details from ESI
    ticker = Column(String(10), nullable=True)
    ceo_id = Column(BigInteger, nullable=True)
    ceo_name = Column(String(255), nullable=True)
    alliance_id = Column(BigInteger, nullable=True, index=True)
    alliance_name = Column(String(255), nullable=True)
    date_founded = Column(DateTime(timezone=True), nullable=True)
    creator_id = Column(BigInteger, nullable=True)
    creator_name = Column(String(255), nullable=True)
    member_count = Column(Integer, nullable=True)
    shares = Column(BigInteger, nullable=True)
    tax_rate = Column(Float, nullable=True)
    
    # Corporation metadata
    description = Column(String(5000), nullable=True)
    url = Column(String(500), nullable=True)
    faction_id = Column(Integer, nullable=True)
    home_station_id = Column(BigInteger, nullable=True)
    
    # Additional corporation data
    corporation_data = Column(JSONB, nullable=True)  # Additional ESI data
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    members = relationship("CorporationMember", back_populates="corporation", cascade="all, delete-orphan")
    assets = relationship("CorporationAsset", back_populates="corporation", cascade="all, delete-orphan")
    structures = relationship("CorporationStructure", back_populates="corporation", cascade="all, delete-orphan")

    # Phase 5 relationships
    moon_extractions = relationship("MoonExtraction", back_populates="corporation", cascade="all, delete-orphan")
    mining_ledger = relationship("MiningLedger", back_populates="corporation", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Corporation(id={self.id}, corporation_id={self.corporation_id}, corporation_name='{self.corporation_name}')>"


class CorporationMember(Base):
    """
    Corporation member model
    
    Tracks corporation members and their roles
    """
    __tablename__ = "corporation_members"
    
    id = Column(Integer, primary_key=True, index=True)
    corporation_id = Column(BigInteger, ForeignKey("corporations.corporation_id", ondelete="CASCADE"), nullable=False, index=True)
    character_id = Column(BigInteger, nullable=False, index=True)
    character_name = Column(String(255), nullable=False)
    
    # Member details
    start_date = Column(DateTime(timezone=True), nullable=True)
    
    # Roles (stored as JSONB array for flexibility)
    roles = Column(JSONB, nullable=True)  # Array of role names
    grantable_roles = Column(JSONB, nullable=True)  # Array of grantable role names
    roles_at_hq = Column(JSONB, nullable=True)  # Roles at HQ
    roles_at_base = Column(JSONB, nullable=True)  # Roles at base
    roles_at_other = Column(JSONB, nullable=True)  # Roles at other locations
    
    # Additional member data
    member_data = Column(JSONB, nullable=True)  # Additional ESI data
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    corporation = relationship("Corporation", back_populates="members")
    
    # Indexes
    __table_args__ = (
        Index("idx_corp_members_corp_character", "corporation_id", "character_id", unique=True),
    )
    
    def __repr__(self):
        return f"<CorporationMember(id={self.id}, corporation_id={self.corporation_id}, character_id={self.character_id})>"


class CorporationAsset(Base):
    """
    Corporation asset model
    
    Stores corporation assets (ships, modules, etc.)
    """
    __tablename__ = "corporation_assets"
    
    id = Column(Integer, primary_key=True, index=True)
    corporation_id = Column(BigInteger, ForeignKey("corporations.corporation_id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Asset details
    type_id = Column(BigInteger, nullable=False, index=True)
    type_name = Column(String(255), nullable=True)
    quantity = Column(Integer, nullable=False, default=1)
    
    # Location
    location_id = Column(BigInteger, nullable=True, index=True)
    location_type = Column(String(50), nullable=True)  # "station", "solar_system", etc.
    location_name = Column(String(255), nullable=True)
    
    # Asset metadata
    is_singleton = Column(Boolean, default=False, nullable=False)
    item_id = Column(BigInteger, nullable=True, unique=True, index=True)
    flag = Column(String(50), nullable=True)  # Asset flag (e.g., "Cargo")
    
    # Additional asset data
    asset_data = Column(JSONB, nullable=True)  # Additional ESI data
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    corporation = relationship("Corporation", back_populates="assets")
    
    # Indexes
    __table_args__ = (
        Index("idx_corp_assets_corp_location", "corporation_id", "location_id"),
        Index("idx_corp_assets_type", "type_id"),
    )
    
    def __repr__(self):
        return f"<CorporationAsset(id={self.id}, corporation_id={self.corporation_id}, type_id={self.type_id}, quantity={self.quantity})>"


class CorporationStructure(Base):
    """
    Corporation structure model
    
    Stores corporation structures (stations, citadels, etc.)
    """
    __tablename__ = "corporation_structures"
    
    id = Column(Integer, primary_key=True, index=True)
    corporation_id = Column(BigInteger, ForeignKey("corporations.corporation_id", ondelete="CASCADE"), nullable=False, index=True)
    structure_id = Column(BigInteger, unique=True, nullable=False, index=True)  # EVE structure ID
    
    # Structure details
    structure_type_id = Column(BigInteger, nullable=True, index=True)
    structure_name = Column(String(255), nullable=True)
    
    # Location
    system_id = Column(BigInteger, nullable=True, index=True)
    system_name = Column(String(255), nullable=True)
    
    # Structure state
    fuel_expires = Column(DateTime(timezone=True), nullable=True)
    state = Column(String(50), nullable=True)  # "anchor_vulnerable", "anchoring", etc.
    state_timer_start = Column(DateTime(timezone=True), nullable=True)
    state_timer_end = Column(DateTime(timezone=True), nullable=True)
    unanchors_at = Column(DateTime(timezone=True), nullable=True)
    
    # Reinforcement
    reinforce_hour = Column(Integer, nullable=True)
    reinforce_weekday = Column(Integer, nullable=True)
    
    # Services
    services = Column(JSONB, nullable=True)  # Array of structure services
    
    # Additional structure data
    structure_data = Column(JSONB, nullable=True)  # Additional ESI data
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    corporation = relationship("Corporation", back_populates="structures")
    
    # Indexes
    __table_args__ = (
        Index("idx_corp_structures_corp_system", "corporation_id", "system_id"),
    )
    
    def __repr__(self):
        return f"<CorporationStructure(id={self.id}, structure_id={self.structure_id}, structure_name='{self.structure_name}')>"

