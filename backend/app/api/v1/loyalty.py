"""
Loyalty Points API endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.character import Character
from app.models.loyalty import LoyaltyPoint, LoyaltyOffer, LoyaltyTransaction
from app.tasks.loyalty_sync import sync_character_loyalty

router = APIRouter()


# Pydantic models
class LoyaltyPointResponse(BaseModel):
    id: int
    corporation_id: int
    loyalty_points: int

    class Config:
        from_attributes = True


class LoyaltyOfferResponse(BaseModel):
    id: int
    offer_id: int
    corporation_id: int
    type_id: int
    quantity: int
    lp_cost: int
    isk_cost: float
    required_items: Optional[str]

    class Config:
        from_attributes = True


class LoyaltyStatistics(BaseModel):
    total_lp: int
    total_corporations: int
    top_corporations: List[dict]


@router.get("/points/", response_model=List[LoyaltyPointResponse])
async def list_loyalty_points(
    character_id: Optional[int] = Query(None),
    corporation_id: Optional[int] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List character loyalty points
    """
    query = db.query(LoyaltyPoint).join(Character).filter(
        Character.user_id == current_user.id
    )

    if character_id:
        char = db.query(Character).filter(
            and_(
                Character.id == character_id,
                Character.user_id == current_user.id,
            )
        ).first()
        if not char:
            raise HTTPException(status_code=403, detail="Character not found or unauthorized")
        query = query.filter(LoyaltyPoint.character_id == character_id)

    if corporation_id:
        query = query.filter(LoyaltyPoint.corporation_id == corporation_id)

    lp = query.order_by(desc(LoyaltyPoint.loyalty_points)).limit(limit).offset(offset).all()
    return lp


@router.get("/offers/", response_model=List[LoyaltyOfferResponse])
async def list_loyalty_offers(
    corporation_id: Optional[int] = Query(None),
    type_id: Optional[int] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List loyalty point store offers
    """
    query = db.query(LoyaltyOffer)

    if corporation_id:
        query = query.filter(LoyaltyOffer.corporation_id == corporation_id)

    if type_id:
        query = query.filter(LoyaltyOffer.type_id == type_id)

    offers = query.order_by(LoyaltyOffer.lp_cost).limit(limit).offset(offset).all()
    return offers


@router.get("/offers/{offer_id}", response_model=LoyaltyOfferResponse)
async def get_loyalty_offer(
    offer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a specific loyalty offer
    """
    offer = db.query(LoyaltyOffer).filter(
        LoyaltyOffer.offer_id == offer_id
    ).first()

    if not offer:
        raise HTTPException(status_code=404, detail="Loyalty offer not found")

    return offer


@router.get("/statistics/{character_id}", response_model=LoyaltyStatistics)
async def get_loyalty_statistics(
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get loyalty point statistics for a character
    """
    # Verify character belongs to user
    char = db.query(Character).filter(
        and_(
            Character.id == character_id,
            Character.user_id == current_user.id,
        )
    ).first()

    if not char:
        raise HTTPException(status_code=403, detail="Character not found or unauthorized")

    lp_entries = db.query(LoyaltyPoint).filter(
        LoyaltyPoint.character_id == character_id
    ).all()

    total_lp = sum(entry.loyalty_points for entry in lp_entries)
    total_corporations = len(lp_entries)

    # Top corporations
    top_corps = sorted(
        [
            {
                "corporation_id": entry.corporation_id,
                "loyalty_points": entry.loyalty_points,
            }
            for entry in lp_entries
        ],
        key=lambda x: x["loyalty_points"],
        reverse=True,
    )[:5]

    return LoyaltyStatistics(
        total_lp=total_lp,
        total_corporations=total_corporations,
        top_corporations=top_corps,
    )


@router.post("/sync/{character_id}")
async def trigger_loyalty_sync(
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Trigger loyalty points sync for a character
    """
    # Verify character belongs to user
    char = db.query(Character).filter(
        and_(
            Character.id == character_id,
            Character.user_id == current_user.id,
        )
    ).first()

    if not char:
        raise HTTPException(status_code=403, detail="Character not found or unauthorized")

    # Trigger sync task
    sync_character_loyalty.delay(char.character_id)

    return {"status": "sync started", "character_id": character_id}
