"""
Loyalty Points models
"""
from sqlalchemy import Column, Integer, BigInteger, String, DateTime, ForeignKey, DECIMAL
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class LoyaltyPoint(Base):
    """Character loyalty points with corporations"""
    __tablename__ = "loyalty_points"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False, index=True)
    corporation_id = Column(BigInteger, nullable=False, index=True)

    # LP amount
    loyalty_points = Column(Integer, nullable=False, default=0)

    # Metadata
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    character = relationship("Character", back_populates="loyalty_points")


class LoyaltyOffer(Base):
    """LP store offers (static data from ESI)"""
    __tablename__ = "loyalty_offers"

    id = Column(Integer, primary_key=True, index=True)
    offer_id = Column(Integer, unique=True, nullable=False, index=True)
    corporation_id = Column(BigInteger, nullable=False, index=True)

    # Offer details
    type_id = Column(Integer, nullable=False)  # Item being offered
    quantity = Column(Integer, default=1)

    # Cost
    lp_cost = Column(Integer, nullable=False)
    isk_cost = Column(DECIMAL(precision=20, scale=2), default=0)

    # Required items (store as comma-separated: "type_id:quantity,type_id:quantity")
    required_items = Column(String(500))

    # Metadata
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class LoyaltyTransaction(Base):
    """Track LP transactions for analytics"""
    __tablename__ = "loyalty_transactions"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False, index=True)
    corporation_id = Column(BigInteger, nullable=False, index=True)

    # Transaction details
    transaction_type = Column(String(50), nullable=False)  # earned, spent
    amount = Column(Integer, nullable=False)
    balance_after = Column(Integer)

    # Source/reason
    source = Column(String(255))  # mission, offer_id, etc.
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    character = relationship("Character")
