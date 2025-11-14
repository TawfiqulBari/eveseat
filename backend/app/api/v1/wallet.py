"""
Wallet API Endpoints

Handle character wallet journal and transactions
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func
from typing import List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import logging

from app.core.database import get_db
from app.models.user import User
from app.models.character import Character
from app.models.wallet import WalletJournal, WalletTransaction
from app.api.deps import get_current_user
from app.tasks.wallet_sync import sync_character_wallet
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic models
class WalletJournalResponse(BaseModel):
    id: int
    entry_id: int
    date: datetime
    ref_type: str
    amount: float
    balance: Optional[float] = None
    description: str
    first_party_id: Optional[int] = None
    second_party_id: Optional[int] = None

    class Config:
        from_attributes = True


class WalletTransactionResponse(BaseModel):
    id: int
    transaction_id: int
    date: datetime
    type_id: int
    quantity: int
    unit_price: float
    is_buy: bool
    client_id: int
    location_id: int

    class Config:
        from_attributes = True


@router.get("/balance/{character_id}")
async def get_wallet_balance(
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get current wallet balance for a character

    Returns the most recent balance from wallet journal
    """
    # Verify character ownership
    character = db.query(Character).filter(
        and_(
            Character.id == character_id,
            Character.user_id == current_user.id,
        )
    ).first()

    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found"
        )

    # Get most recent journal entry with balance
    latest_entry = db.query(WalletJournal).filter(
        and_(
            WalletJournal.character_id == character.id,
            WalletJournal.balance.isnot(None),
        )
    ).order_by(desc(WalletJournal.date)).first()

    if not latest_entry:
        return {"balance": 0.0, "as_of": None}

    return {
        "balance": float(latest_entry.balance),
        "as_of": latest_entry.date
    }


@router.get("/journal/", response_model=List[WalletJournalResponse])
async def list_wallet_journal(
    character_id: Optional[int] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    ref_type: Optional[str] = None,
    limit: int = Query(50, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List wallet journal entries for a character

    Query parameters:
    - character_id: Filter by character
    - from_date: Entries from this date onwards
    - to_date: Entries until this date
    - ref_type: Filter by transaction type
    - limit: Max results (default 50, max 500)
    - offset: Pagination offset
    """
    # Get character
    if character_id:
        character = db.query(Character).filter(
            and_(
                Character.id == character_id,
                Character.user_id == current_user.id,
            )
        ).first()
    else:
        character = db.query(Character).filter(
            Character.user_id == current_user.id
        ).first()

    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found"
        )

    # Build query
    query = db.query(WalletJournal).filter(WalletJournal.character_id == character.id)

    if from_date:
        query = query.filter(WalletJournal.date >= from_date)

    if to_date:
        query = query.filter(WalletJournal.date <= to_date)

    if ref_type:
        query = query.filter(WalletJournal.ref_type == ref_type)

    # Order by date descending
    query = query.order_by(desc(WalletJournal.date))

    # Pagination
    entries = query.offset(offset).limit(limit).all()

    return entries


@router.get("/transactions/", response_model=List[WalletTransactionResponse])
async def list_wallet_transactions(
    character_id: Optional[int] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    type_id: Optional[int] = None,
    is_buy: Optional[bool] = None,
    limit: int = Query(50, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List wallet market transactions for a character

    Query parameters:
    - character_id: Filter by character
    - from_date: Transactions from this date onwards
    - to_date: Transactions until this date
    - type_id: Filter by item type
    - is_buy: Filter by buy (true) or sell (false)
    - limit: Max results (default 50, max 500)
    - offset: Pagination offset
    """
    # Get character
    if character_id:
        character = db.query(Character).filter(
            and_(
                Character.id == character_id,
                Character.user_id == current_user.id,
            )
        ).first()
    else:
        character = db.query(Character).filter(
            Character.user_id == current_user.id
        ).first()

    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found"
        )

    # Build query
    query = db.query(WalletTransaction).filter(WalletTransaction.character_id == character.id)

    if from_date:
        query = query.filter(WalletTransaction.date >= from_date)

    if to_date:
        query = query.filter(WalletTransaction.date <= to_date)

    if type_id is not None:
        query = query.filter(WalletTransaction.type_id == type_id)

    if is_buy is not None:
        query = query.filter(WalletTransaction.is_buy == is_buy)

    # Order by date descending
    query = query.order_by(desc(WalletTransaction.date))

    # Pagination
    transactions = query.offset(offset).limit(limit).all()

    return transactions


@router.get("/statistics/{character_id}")
async def get_wallet_statistics(
    character_id: int,
    days: int = Query(30, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get wallet statistics for a character

    Returns income, expenses, and net change over the specified period
    """
    # Verify character ownership
    character = db.query(Character).filter(
        and_(
            Character.id == character_id,
            Character.user_id == current_user.id,
        )
    ).first()

    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found"
        )

    # Get date range
    from_date = datetime.utcnow() - timedelta(days=days)

    # Calculate total income (positive amounts)
    income = db.query(func.sum(WalletJournal.amount)).filter(
        and_(
            WalletJournal.character_id == character.id,
            WalletJournal.date >= from_date,
            WalletJournal.amount > 0,
        )
    ).scalar() or Decimal(0)

    # Calculate total expenses (negative amounts)
    expenses = db.query(func.sum(WalletJournal.amount)).filter(
        and_(
            WalletJournal.character_id == character.id,
            WalletJournal.date >= from_date,
            WalletJournal.amount < 0,
        )
    ).scalar() or Decimal(0)

    # Market transaction statistics
    market_buys = db.query(
        func.sum(WalletTransaction.quantity * WalletTransaction.unit_price)
    ).filter(
        and_(
            WalletTransaction.character_id == character.id,
            WalletTransaction.date >= from_date,
            WalletTransaction.is_buy == True,
        )
    ).scalar() or Decimal(0)

    market_sells = db.query(
        func.sum(WalletTransaction.quantity * WalletTransaction.unit_price)
    ).filter(
        and_(
            WalletTransaction.character_id == character.id,
            WalletTransaction.date >= from_date,
            WalletTransaction.is_buy == False,
        )
    ).scalar() or Decimal(0)

    return {
        "period_days": days,
        "total_income": float(income),
        "total_expenses": float(expenses),
        "net_change": float(income + expenses),  # expenses are negative
        "market_buys": float(market_buys),
        "market_sells": float(market_sells),
        "market_profit": float(market_sells - market_buys),
    }


@router.post("/sync/{character_id}")
async def trigger_wallet_sync(
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger manual wallet sync for a character"""
    # Verify character ownership
    character = db.query(Character).filter(
        and_(
            Character.id == character_id,
            Character.user_id == current_user.id,
        )
    ).first()

    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found"
        )

    # Queue sync task
    task = sync_character_wallet.delay(character.character_id)

    return {
        "success": True,
        "task_id": task.id,
        "message": "Wallet sync queued"
    }
