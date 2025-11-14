"""
Clones API endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.character import Character
from app.models.clone import Clone, ActiveImplant
from app.tasks.clone_sync import sync_character_clones

router = APIRouter()


# Pydantic models
class CloneResponse(BaseModel):
    id: int
    jump_clone_id: int
    name: Optional[str]
    location_id: int
    location_type: Optional[str]
    implants: list

    class Config:
        from_attributes = True


class ActiveImplantResponse(BaseModel):
    id: int
    type_id: int
    name: Optional[str]
    slot: Optional[int]

    class Config:
        from_attributes = True


class CloneStatistics(BaseModel):
    total_jump_clones: int
    clones_with_implants: int
    active_implants: int
    total_implant_value: Optional[float]


@router.get("/", response_model=List[CloneResponse])
async def list_clones(
    character_id: Optional[int] = Query(None),
    location_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List jump clones
    """
    query = db.query(Clone).join(Character).filter(
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
        query = query.filter(Clone.character_id == character_id)

    if location_id:
        query = query.filter(Clone.location_id == location_id)

    clones = query.all()
    return clones


@router.get("/active-implants/", response_model=List[ActiveImplantResponse])
async def get_active_implants(
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get active implants in current clone
    """
    char = db.query(Character).filter(
        and_(
            Character.id == character_id,
            Character.user_id == current_user.id,
        )
    ).first()

    if not char:
        raise HTTPException(status_code=403, detail="Character not found or unauthorized")

    implants = db.query(ActiveImplant).filter(
        ActiveImplant.character_id == character_id
    ).order_by(ActiveImplant.slot).all()

    return implants


@router.get("/statistics/{character_id}", response_model=CloneStatistics)
async def get_clone_statistics(
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get clone statistics
    """
    char = db.query(Character).filter(
        and_(
            Character.id == character_id,
            Character.user_id == current_user.id,
        )
    ).first()

    if not char:
        raise HTTPException(status_code=403, detail="Character not found or unauthorized")

    clones = db.query(Clone).filter(Clone.character_id == character_id).all()
    active_implants = db.query(ActiveImplant).filter(
        ActiveImplant.character_id == character_id
    ).all()

    total_jump_clones = len(clones)
    clones_with_implants = sum(1 for clone in clones if clone.implants)
    active_implant_count = len(active_implants)

    return CloneStatistics(
        total_jump_clones=total_jump_clones,
        clones_with_implants=clones_with_implants,
        active_implants=active_implant_count,
        total_implant_value=None,  # Would need market data to calculate
    )


@router.post("/sync/{character_id}")
async def trigger_clone_sync(
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Trigger clone sync for a character
    """
    char = db.query(Character).filter(
        and_(
            Character.id == character_id,
            Character.user_id == current_user.id,
        )
    ).first()

    if not char:
        raise HTTPException(status_code=403, detail="Character not found or unauthorized")

    sync_character_clones.delay(char.character_id)

    return {"status": "sync started", "character_id": character_id}
