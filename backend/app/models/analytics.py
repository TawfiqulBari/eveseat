"""
Analytics models for market trends, profit/loss tracking, and ISK flow
"""
from sqlalchemy import Column, Integer, BigInteger, String, Float, DateTime, JSON, ForeignKey, Boolean, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

from app.core.database import Base


class MarketTrend(Base):
    """Market price trends over time"""
    __tablename__ = "market_trends"

    id = Column(Integer, primary_key=True, index=True)
    type_id = Column(Integer, nullable=False, index=True)
    region_id = Column(Integer, nullable=False, index=True)
    date = Column(DateTime(timezone=True), nullable=False, index=True)

    # Price statistics
    average_price = Column(Float)
    highest_price = Column(Float)
    lowest_price = Column(Float)
    median_price = Column(Float)
    volume = Column(BigInteger)
    order_count = Column(Integer)

    # Trend indicators
    price_change_percent = Column(Float)  # % change from previous period
    volume_change_percent = Column(Float)
    trend_direction = Column(String(20))  # 'up', 'down', 'stable'
    volatility_score = Column(Float)  # Price volatility indicator

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    synced_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index('ix_market_trends_type_date', 'type_id', 'date'),
        Index('ix_market_trends_region_date', 'region_id', 'date'),
    )


class ProfitLoss(Base):
    """Profit and loss tracking for characters"""
    __tablename__ = "profit_loss"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False, index=True)
    date = Column(DateTime(timezone=True), nullable=False, index=True)

    # Income sources
    bounty_income = Column(BigInteger, default=0)
    mission_income = Column(BigInteger, default=0)
    market_income = Column(BigInteger, default=0)
    contract_income = Column(BigInteger, default=0)
    industry_income = Column(BigInteger, default=0)
    other_income = Column(BigInteger, default=0)
    total_income = Column(BigInteger, default=0)

    # Expenses
    market_expenses = Column(BigInteger, default=0)
    contract_expenses = Column(BigInteger, default=0)
    industry_expenses = Column(BigInteger, default=0)
    ship_losses = Column(BigInteger, default=0)
    other_expenses = Column(BigInteger, default=0)
    total_expenses = Column(BigInteger, default=0)

    # Net profit/loss
    net_profit = Column(BigInteger, default=0)

    # Metadata
    transaction_count = Column(Integer, default=0)
    largest_income = Column(BigInteger, default=0)
    largest_expense = Column(BigInteger, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    character = relationship("Character", back_populates="profit_loss")

    __table_args__ = (
        Index('ix_profit_loss_char_date', 'character_id', 'date'),
    )


class IndustryProfitability(Base):
    """Industry job profitability calculations"""
    __tablename__ = "industry_profitability"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("industry_jobs.id"), nullable=True, index=True)

    # Product information
    product_type_id = Column(Integer, nullable=False, index=True)
    product_quantity = Column(Integer, nullable=False)
    blueprint_type_id = Column(Integer, nullable=False)

    # Cost breakdown
    material_cost = Column(BigInteger, default=0)
    installation_cost = Column(BigInteger, default=0)
    tax_cost = Column(BigInteger, default=0)
    time_cost = Column(BigInteger, default=0)  # Estimated based on time value
    total_cost = Column(BigInteger, default=0)

    # Revenue
    estimated_revenue = Column(BigInteger, default=0)  # Based on market price
    actual_revenue = Column(BigInteger, default=0)  # If sold

    # Profitability
    estimated_profit = Column(BigInteger, default=0)
    estimated_margin_percent = Column(Float, default=0)
    actual_profit = Column(BigInteger, default=0)
    actual_margin_percent = Column(Float, default=0)

    # Metadata
    job_type = Column(String(50))  # manufacturing, research_material, research_time, copying, invention
    run_count = Column(Integer, default=1)
    duration_seconds = Column(Integer)
    isk_per_hour = Column(BigInteger, default=0)

    calculated_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    character = relationship("Character", back_populates="industry_profitability")
    job = relationship("IndustryJob", backref="profitability")

    __table_args__ = (
        Index('ix_industry_prof_char_product', 'character_id', 'product_type_id'),
    )


class ISKFlow(Base):
    """ISK income and expense flow tracking"""
    __tablename__ = "isk_flow"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False, index=True)
    transaction_id = Column(BigInteger, index=True)  # Reference to wallet transaction/journal
    date = Column(DateTime(timezone=True), nullable=False, index=True)

    # Transaction details
    amount = Column(BigInteger, nullable=False)
    flow_type = Column(String(20), nullable=False, index=True)  # 'income' or 'expense'
    category = Column(String(50), nullable=False, index=True)  # e.g., 'bounty', 'market_sale', 'ship_loss'
    subcategory = Column(String(50))  # More specific categorization

    # Related entity information
    related_type_id = Column(Integer)  # Item type if applicable
    related_location_id = Column(BigInteger)  # Location if applicable
    counterparty_id = Column(Integer)  # Character/Corp/Alliance involved

    # Description and metadata
    description = Column(String(500))
    ref_type = Column(String(100))  # ESI ref_type from journal
    is_recurring = Column(Boolean, default=False)
    tags = Column(JSON)  # User-defined tags for categorization

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    character = relationship("Character", back_populates="isk_flow")

    __table_args__ = (
        Index('ix_isk_flow_char_date', 'character_id', 'date'),
        Index('ix_isk_flow_category', 'category', 'date'),
    )


class PortfolioSnapshot(Base):
    """Daily portfolio snapshots for net worth tracking"""
    __tablename__ = "portfolio_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False, index=True)
    snapshot_date = Column(DateTime(timezone=True), nullable=False, index=True)

    # Wallet
    wallet_balance = Column(BigInteger, default=0)

    # Assets
    ship_value = Column(BigInteger, default=0)
    module_value = Column(BigInteger, default=0)
    blueprint_value = Column(BigInteger, default=0)
    mineral_value = Column(BigInteger, default=0)
    other_assets_value = Column(BigInteger, default=0)
    total_assets_value = Column(BigInteger, default=0)

    # Market
    sell_orders_value = Column(BigInteger, default=0)
    buy_orders_escrow = Column(BigInteger, default=0)

    # Total net worth
    total_net_worth = Column(BigInteger, default=0)

    # Changes from previous snapshot
    net_worth_change = Column(BigInteger, default=0)
    net_worth_change_percent = Column(Float, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    character = relationship("Character", back_populates="portfolio_snapshots")

    __table_args__ = (
        Index('ix_portfolio_char_date', 'character_id', 'snapshot_date'),
    )


class TradingOpportunity(Base):
    """Trading opportunities detected by market analysis"""
    __tablename__ = "trading_opportunities"

    id = Column(Integer, primary_key=True, index=True)
    type_id = Column(Integer, nullable=False, index=True)

    # Location details
    buy_location_id = Column(BigInteger, nullable=False)
    buy_region_id = Column(Integer, nullable=False)
    sell_location_id = Column(BigInteger, nullable=False)
    sell_region_id = Column(Integer, nullable=False)

    # Prices
    buy_price = Column(Float, nullable=False)
    sell_price = Column(Float, nullable=False)

    # Opportunity metrics
    profit_per_unit = Column(Float, nullable=False)
    profit_margin_percent = Column(Float, nullable=False)
    potential_volume = Column(Integer, nullable=False)
    total_profit_potential = Column(BigInteger, nullable=False)

    # Requirements
    required_capital = Column(BigInteger, nullable=False)
    jumps = Column(Integer)  # Distance between locations
    cargo_volume = Column(Float)  # m3 per unit

    # Risk factors
    competition_score = Column(Float)  # How many other orders exist
    volatility_score = Column(Float)  # Price stability
    risk_level = Column(String(20))  # 'low', 'medium', 'high'

    # Status
    is_active = Column(Boolean, default=True)
    detected_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))

    __table_args__ = (
        Index('ix_trading_opp_profit', 'profit_margin_percent', 'is_active'),
        Index('ix_trading_opp_type', 'type_id', 'is_active'),
    )
