"""
Contract models

EVE Online contracts system
"""
from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, ForeignKey, BigInteger, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base


class Contract(Base):
    """Character or corporation contracts"""

    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=True, index=True)
    corporation_id = Column(Integer, ForeignKey("corporations.id"), nullable=True, index=True)

    # Contract data from ESI
    contract_id = Column(BigInteger, unique=True, index=True)
    issuer_id = Column(BigInteger)
    issuer_corporation_id = Column(BigInteger)
    assignee_id = Column(BigInteger)  # Can be character, corp, or alliance
    acceptor_id = Column(BigInteger, nullable=True)  # Who accepted the contract

    # Contract type and availability
    type = Column(String(50))  # item_exchange, auction, courier, loan
    availability = Column(String(50))  # public, personal, corporation, alliance
    status = Column(String(50), index=True)  # outstanding, in_progress, finished_issuer, finished_contractor, finished, cancelled, rejected, failed, deleted, reversed

    # Title and description
    title = Column(String(255), nullable=True)
    for_corporation = Column(Boolean, default=False)

    # Pricing
    price = Column(Numeric(precision=20, scale=2), nullable=True)
    reward = Column(Numeric(precision=20, scale=2), nullable=True)
    collateral = Column(Numeric(precision=20, scale=2), nullable=True)
    buyout = Column(Numeric(precision=20, scale=2), nullable=True)  # For auctions
    volume = Column(Float, nullable=True)  # m3

    # Dates
    date_issued = Column(DateTime(timezone=True), index=True)
    date_expired = Column(DateTime(timezone=True), index=True)
    date_accepted = Column(DateTime(timezone=True), nullable=True)
    date_completed = Column(DateTime(timezone=True), nullable=True)
    days_to_complete = Column(Integer, nullable=True)  # For courier contracts

    # Location
    start_location_id = Column(BigInteger, nullable=True)
    end_location_id = Column(BigInteger, nullable=True)  # For courier contracts

    # Metadata
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    character = relationship("Character", back_populates="contracts", foreign_keys=[character_id])
    items = relationship("ContractItem", back_populates="contract", cascade="all, delete-orphan")
    bids = relationship("ContractBid", back_populates="contract", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Contract(contract_id={self.contract_id}, type='{self.type}', status='{self.status}')>"


class ContractItem(Base):
    """Items in a contract"""

    __tablename__ = "contract_items"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(BigInteger, ForeignKey("contracts.contract_id"), nullable=False, index=True)
    record_id = Column(BigInteger)  # ESI record ID
    type_id = Column(Integer)
    quantity = Column(BigInteger)
    is_included = Column(Boolean, default=True)  # True = included, False = requested
    is_singleton = Column(Boolean, default=False)  # Blueprint copy or not
    raw_quantity = Column(Integer, nullable=True)  # For blueprints (runs)

    # Metadata
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    contract = relationship("Contract", back_populates="items")

    def __repr__(self):
        return f"<ContractItem(type_id={self.type_id}, quantity={self.quantity}, included={self.is_included})>"


class ContractBid(Base):
    """Bids on auction contracts"""

    __tablename__ = "contract_bids"

    id = Column(Integer, primary_key=True, index=True)
    bid_id = Column(BigInteger, unique=True, index=True)
    contract_id = Column(BigInteger, ForeignKey("contracts.contract_id"), nullable=False, index=True)
    bidder_id = Column(BigInteger)
    amount = Column(Numeric(precision=20, scale=2))
    date_bid = Column(DateTime(timezone=True), index=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    contract = relationship("Contract", back_populates="bids")

    def __repr__(self):
        return f"<ContractBid(bid_id={self.bid_id}, amount={self.amount})>"
