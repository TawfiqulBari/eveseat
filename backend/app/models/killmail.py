"""
Killmail models
"""
from sqlalchemy import Column, Integer, BigInteger, DateTime, String, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Killmail(Base):
    """
    Killmail model - stores EVE Online killmail data
    
    Uses JSONB for flexible storage of killmail payload
    """
    __tablename__ = "killmails"
    
    id = Column(Integer, primary_key=True, index=True)
    killmail_id = Column(BigInteger, unique=True, nullable=False, index=True)  # EVE killmail ID
    killmail_hash = Column(String(255), nullable=False, index=True)  # Hash for ESI retrieval
    
    # Timestamp
    time = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Location
    system_id = Column(BigInteger, nullable=True, index=True)
    system_name = Column(String(255), nullable=True)
    constellation_id = Column(BigInteger, nullable=True)
    region_id = Column(BigInteger, nullable=True)
    
    # Victim information
    victim_character_id = Column(BigInteger, nullable=True, index=True)
    victim_character_name = Column(String(255), nullable=True)
    victim_corporation_id = Column(BigInteger, nullable=True, index=True)
    victim_corporation_name = Column(String(255), nullable=True)
    victim_alliance_id = Column(BigInteger, nullable=True, index=True)
    victim_alliance_name = Column(String(255), nullable=True)
    victim_ship_type_id = Column(BigInteger, nullable=True, index=True)
    victim_ship_type_name = Column(String(255), nullable=True)
    
    # Killmail value (ISK)
    value = Column(BigInteger, nullable=True, index=True)  # Total value in ISK
    
    # Full killmail data (JSONB for flexibility)
    killmail_data = Column(JSONB, nullable=False)  # Complete killmail payload from ESI
    
    # Additional metadata
    attackers_count = Column(Integer, nullable=True)
    zkill_url = Column(String(500), nullable=True)  # zKillboard URL
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Indexes for efficient queries
    __table_args__ = (
        Index("idx_killmails_time_desc", "time", postgresql_ops={"time": "DESC"}),
        Index("idx_killmails_corporation_time", "victim_corporation_id", "time", postgresql_ops={"time": "DESC"}),
        Index("idx_killmails_system_time", "system_id", "time", postgresql_ops={"time": "DESC"}),
        Index("idx_killmails_value_desc", "value", postgresql_ops={"value": "DESC NULLS LAST"}),
        Index("idx_killmails_character_time", "victim_character_id", "time", postgresql_ops={"time": "DESC"}),
    )
    
    def __repr__(self):
        return f"<Killmail(id={self.id}, killmail_id={self.killmail_id}, time='{self.time}', value={self.value})>"

