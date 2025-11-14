"""
Market models for EVE Online market data
"""
from sqlalchemy import Column, Integer, BigInteger, Float, DateTime, String, Boolean, Index, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.core.database import Base


class MarketOrder(Base):
    """
    Market order model
    
    Stores market buy/sell orders from ESI
    """
    __tablename__ = "market_orders"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(BigInteger, unique=True, nullable=False, index=True)  # EVE order ID
    
    # Character ownership (for personal orders)
    character_id = Column(BigInteger, nullable=True, index=True)  # Character who owns this order
    
    # Order type
    type_id = Column(BigInteger, nullable=False, index=True)  # Item type ID
    type_name = Column(String(255), nullable=True)
    is_buy_order = Column(Boolean, nullable=False, index=True)  # True for buy, False for sell
    
    # Location
    location_id = Column(BigInteger, nullable=False, index=True)  # Station/system ID
    location_type = Column(String(50), nullable=True)  # "station", "structure", etc.
    location_name = Column(String(255), nullable=True)
    region_id = Column(BigInteger, nullable=True, index=True)
    region_name = Column(String(255), nullable=True)
    system_id = Column(BigInteger, nullable=True, index=True)
    system_name = Column(String(255), nullable=True)
    
    # Order details
    price = Column(Float, nullable=False, index=True)
    volume_total = Column(Integer, nullable=False)
    volume_remain = Column(Integer, nullable=False)
    min_volume = Column(Integer, nullable=True)
    duration = Column(Integer, nullable=True)  # Order duration in days
    issued = Column(DateTime(timezone=True), nullable=False, index=True)
    expires = Column(DateTime(timezone=True), nullable=True, index=True)
    
    # Order state
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    range_type = Column(String(50), nullable=True)  # "station", "region", "solarsystem", etc.
    range_value = Column(Integer, nullable=True)
    
    # Additional order data
    order_data = Column(JSONB, nullable=True)  # Additional ESI data
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    
    # Indexes for efficient queries
    __table_args__ = (
        Index("idx_market_orders_type_location", "type_id", "location_id", "is_buy_order"),
        Index("idx_market_orders_region_type", "region_id", "type_id", "is_buy_order"),
        Index("idx_market_orders_character", "character_id", "is_active"),
        Index("idx_market_orders_price", "price"),
        Index("idx_market_orders_expires", "expires"),
    )
    
    def __repr__(self):
        return f"<MarketOrder(id={self.id}, order_id={self.order_id}, type_id={self.type_id}, price={self.price})>"


class PriceHistory(Base):
    """
    Price history model
    
    Stores historical price data for items
    """
    __tablename__ = "price_history"
    
    id = Column(Integer, primary_key=True, index=True)
    type_id = Column(BigInteger, nullable=False, index=True)  # Item type ID
    type_name = Column(String(255), nullable=True)
    
    # Location
    region_id = Column(BigInteger, nullable=False, index=True)
    region_name = Column(String(255), nullable=True)
    
    # Price data
    average_price = Column(Float, nullable=True)
    highest_price = Column(Float, nullable=True)
    lowest_price = Column(Float, nullable=True)
    order_count = Column(Integer, nullable=True)
    volume = Column(BigInteger, nullable=True)
    
    # Date for this price snapshot
    date = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Additional price data
    price_data = Column(JSONB, nullable=True)  # Additional price metrics
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Indexes for efficient time-series queries
    __table_args__ = (
        Index("idx_price_history_type_region_date", "type_id", "region_id", "date", postgresql_ops={"date": "DESC"}),
        Index("idx_price_history_date_desc", "date", postgresql_ops={"date": "DESC"}),
    )
    
    def __repr__(self):
        return f"<PriceHistory(id={self.id}, type_id={self.type_id}, region_id={self.region_id}, date='{self.date}', avg_price={self.average_price})>"

