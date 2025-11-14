"""
Wallet models

EVE Online wallet transactions and journal
"""
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, BigInteger, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base


class WalletJournal(Base):
    """Character or corporation wallet journal entries"""

    __tablename__ = "wallet_journal"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=True, index=True)
    corporation_id = Column(Integer, ForeignKey("corporations.id"), nullable=True, index=True)

    # Journal entry data
    entry_id = Column(BigInteger, unique=True, index=True)
    date = Column(DateTime(timezone=True), index=True)
    ref_type = Column(String(100), index=True)  # Transaction type (bounty_prizes, market_escrow, etc.)
    amount = Column(Numeric(precision=20, scale=2))
    balance = Column(Numeric(precision=20, scale=2), nullable=True)
    description = Column(Text)

    # Context IDs
    context_id = Column(BigInteger, nullable=True)  # Related entity ID
    context_id_type = Column(String(50), nullable=True)  # Type of context_id (contract_id, market_transaction_id, etc.)

    # First and second party
    first_party_id = Column(BigInteger, nullable=True)
    second_party_id = Column(BigInteger, nullable=True)

    # Tax information
    tax = Column(Numeric(precision=20, scale=2), nullable=True)
    tax_receiver_id = Column(BigInteger, nullable=True)

    # Reason (optional description from user)
    reason = Column(String(500), nullable=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    character = relationship("Character", back_populates="wallet_journal")

    def __repr__(self):
        return f"<WalletJournal(entry_id={self.entry_id}, ref_type='{self.ref_type}', amount={self.amount})>"


class WalletTransaction(Base):
    """Character or corporation wallet market transactions"""

    __tablename__ = "wallet_transactions"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=True, index=True)
    corporation_id = Column(Integer, ForeignKey("corporations.id"), nullable=True, index=True)

    # Transaction data
    transaction_id = Column(BigInteger, unique=True, index=True)
    date = Column(DateTime(timezone=True), index=True)
    type_id = Column(Integer, index=True)  # Item type ID
    quantity = Column(BigInteger)
    unit_price = Column(Numeric(precision=20, scale=2))
    is_buy = Column(String(20), index=True)  # True = buy, False = sell

    # Client and location
    client_id = Column(BigInteger)
    location_id = Column(BigInteger)
    is_personal = Column(String(20), default=True)
    journal_ref_id = Column(BigInteger, nullable=True)  # Link to journal entry

    # Metadata
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    character = relationship("Character", back_populates="wallet_transactions")

    def __repr__(self):
        return f"<WalletTransaction(transaction_id={self.transaction_id}, type_id={self.type_id}, quantity={self.quantity})>"
