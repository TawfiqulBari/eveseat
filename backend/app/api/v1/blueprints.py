"""
Blueprints API endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.character import Character
from app.models.blueprint import Blueprint, BlueprintResearch
from app.tasks.blueprint_sync import sync_character_blueprints

router = APIRouter()


# Pydantic models
class BlueprintResponse(BaseModel):
    id: int
    item_id: int
    type_id: int
    location_id: int
    location_flag: str
    quantity: int
    time_efficiency: int
    material_efficiency: int
    runs: int

    class Config:
        from_attributes = True


class BlueprintStatistics(BaseModel):
    total_blueprints: int
    bpos: int  # Blueprint Originals
    bpcs: int  # Blueprint Copies
    avg_me: float
    avg_te: float
    fully_researched: int


@router.get("/", response_model=List[BlueprintResponse])
async def list_blueprints(
    character_id: Optional[int] = Query(None),
    location_id: Optional[int] = Query(None),
    is_original: Optional[bool] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List character blueprints
    """
    query = db.query(Blueprint).join(Character).filter(
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
        query = query.filter(Blueprint.character_id == character_id)

    if location_id:
        query = query.filter(Blueprint.location_id == location_id)

    if is_original is not None:
        if is_original:
            query = query.filter(Blueprint.runs == -1)  # BPO
        else:
            query = query.filter(Blueprint.runs > -1)  # BPC

    blueprints = query.order_by(desc(Blueprint.created_at)).limit(limit).offset(offset).all()
    return blueprints


@router.get("/{blueprint_id}", response_model=BlueprintResponse)
async def get_blueprint(
    blueprint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a specific blueprint
    """
    blueprint = db.query(Blueprint).join(Character).filter(
        and_(
            Blueprint.id == blueprint_id,
            Character.user_id == current_user.id,
        )
    ).first()

    if not blueprint:
        raise HTTPException(status_code=404, detail="Blueprint not found")

    return blueprint


@router.get("/statistics/{character_id}", response_model=BlueprintStatistics)
async def get_blueprint_statistics(
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get blueprint statistics for a character
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

    blueprints = db.query(Blueprint).filter(
        Blueprint.character_id == character_id
    ).all()

    total_blueprints = len(blueprints)
    bpos = sum(1 for bp in blueprints if bp.runs == -1)
    bpcs = sum(1 for bp in blueprints if bp.runs > -1)

    if total_blueprints > 0:
        avg_me = sum(bp.material_efficiency for bp in blueprints) / total_blueprints
        avg_te = sum(bp.time_efficiency for bp in blueprints) / total_blueprints
    else:
        avg_me = 0
        avg_te = 0

    # Fully researched: ME 10, TE 20
    fully_researched = sum(
        1 for bp in blueprints
        if bp.material_efficiency == 10 and bp.time_efficiency == 20
    )

    return BlueprintStatistics(
        total_blueprints=total_blueprints,
        bpos=bpos,
        bpcs=bpcs,
        avg_me=round(avg_me, 2),
        avg_te=round(avg_te, 2),
        fully_researched=fully_researched,
    )


@router.post("/sync/{character_id}")
async def trigger_blueprint_sync(
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Trigger blueprint sync for a character
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
    sync_character_blueprints.delay(char.character_id)

    return {"status": "sync started", "character_id": character_id}
