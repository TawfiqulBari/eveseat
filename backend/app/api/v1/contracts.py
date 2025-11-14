"""
Contracts API Endpoints

Handle character and corporation contracts
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from typing import List, Optional
from datetime import datetime
import logging

from app.core.database import get_db
from app.models.user import User
from app.models.character import Character
from app.models.contract import Contract, ContractItem, ContractBid
from app.api.deps import get_current_user
from app.tasks.contract_sync import sync_character_contracts
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic models
class ContractItemResponse(BaseModel):
    id: int
    type_id: int
    quantity: int
    is_included: bool
    is_singleton: bool

    class Config:
        from_attributes = True


class ContractResponse(BaseModel):
    id: int
    contract_id: int
    issuer_id: int
    type: str
    availability: str
    status: str
    price: Optional[float] = None
    reward: Optional[float] = None
    collateral: Optional[float] = None
    volume: Optional[float] = None
    date_issued: datetime
    date_expired: datetime
    start_location_id: Optional[int] = None
    end_location_id: Optional[int] = None

    class Config:
        from_attributes = True


class ContractDetailResponse(ContractResponse):
    items: List[ContractItemResponse] = []

    class Config:
        from_attributes = True


@router.get("/", response_model=List[ContractResponse])
async def list_contracts(
    character_id: Optional[int] = None,
    contract_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List contracts for a character

    Query parameters:
    - character_id: Filter by character
    - contract_type: Filter by type (item_exchange, auction, courier, loan)
    - status: Filter by status (outstanding, in_progress, finished, etc.)
    - limit: Max results (default 50, max 200)
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
    query = db.query(Contract).filter(Contract.character_id == character.id)

    if contract_type:
        query = query.filter(Contract.type == contract_type)

    if status:
        query = query.filter(Contract.status == status)

    # Order by date issued descending
    query = query.order_by(desc(Contract.date_issued))

    # Pagination
    contracts = query.offset(offset).limit(limit).all()

    return contracts


@router.get("/{contract_id}", response_model=ContractDetailResponse)
async def get_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific contract with items"""
    # Get contract
    contract = db.query(Contract).filter(Contract.contract_id == contract_id).first()

    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found"
        )

    # Verify ownership
    character = db.query(Character).filter(Character.id == contract.character_id).first()
    if not character or character.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this contract"
        )

    return contract


@router.get("/{contract_id}/items", response_model=List[ContractItemResponse])
async def get_contract_items(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get items in a contract"""
    # Get contract
    contract = db.query(Contract).filter(Contract.contract_id == contract_id).first()

    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found"
        )

    # Verify ownership
    character = db.query(Character).filter(Character.id == contract.character_id).first()
    if not character or character.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this contract"
        )

    # Get items
    items = db.query(ContractItem).filter(
        ContractItem.contract_id == contract_id
    ).all()

    return items


@router.post("/sync/{character_id}")
async def trigger_contract_sync(
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger manual contract sync for a character"""
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
    task = sync_character_contracts.delay(character.character_id)

    return {
        "success": True,
        "task_id": task.id,
        "message": "Contract sync queued"
    }


@router.get("/statistics/{character_id}")
async def get_contract_statistics(
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get contract statistics for a character"""
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

    # Get statistics
    total = db.query(Contract).filter(Contract.character_id == character.id).count()
    outstanding = db.query(Contract).filter(
        and_(
            Contract.character_id == character.id,
            Contract.status == "outstanding",
        )
    ).count()
    in_progress = db.query(Contract).filter(
        and_(
            Contract.character_id == character.id,
            Contract.status == "in_progress",
        )
    ).count()
    finished = db.query(Contract).filter(
        and_(
            Contract.character_id == character.id,
            Contract.status.in_(["finished", "finished_issuer", "finished_contractor"]),
        )
    ).count()

    return {
        "total": total,
        "outstanding": outstanding,
        "in_progress": in_progress,
        "finished": finished,
    }
