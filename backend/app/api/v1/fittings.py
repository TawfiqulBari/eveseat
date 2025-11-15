"""
Fittings API endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from pydantic import BaseModel

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.character import Character
from app.models.fitting import Fitting
from app.tasks.fitting_sync import sync_character_fittings

router = APIRouter()


# Pydantic models
class FittingResponse(BaseModel):
    id: int
    fitting_id: int
    name: str
    description: Optional[str]
    ship_type_id: int
    items: list

    class Config:
        from_attributes = True


class FittingCreate(BaseModel):
    name: str
    description: Optional[str]
    ship_type_id: int
    items: list


@router.get("/", response_model=List[FittingResponse])
async def list_fittings(
    character_id: Optional[int] = Query(None),
    ship_type_id: Optional[int] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List character fittings
    """
    query = db.query(Fitting).join(Character).filter(
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
        query = query.filter(Fitting.character_id == character_id)

    if ship_type_id:
        query = query.filter(Fitting.ship_type_id == ship_type_id)

    fittings = query.order_by(desc(Fitting.created_at)).limit(limit).offset(offset).all()
    return fittings


@router.get("/{fitting_id}", response_model=FittingResponse)
async def get_fitting(
    fitting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a specific fitting
    """
    fitting = db.query(Fitting).join(Character).filter(
        and_(
            Fitting.id == fitting_id,
            Character.user_id == current_user.id,
        )
    ).first()

    if not fitting:
        raise HTTPException(status_code=404, detail="Fitting not found")

    return fitting


@router.delete("/{fitting_id}")
async def delete_fitting(
    fitting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a fitting
    """
    fitting = db.query(Fitting).join(Character).filter(
        and_(
            Fitting.id == fitting_id,
            Character.user_id == current_user.id,
        )
    ).first()

    if not fitting:
        raise HTTPException(status_code=404, detail="Fitting not found")

    db.delete(fitting)
    db.commit()

    return {"status": "deleted", "fitting_id": fitting_id}


@router.post("/sync/{character_id}")
async def trigger_fitting_sync(
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Trigger fitting sync for a character
    """
    char = db.query(Character).filter(
        and_(
            Character.id == character_id,
            Character.user_id == current_user.id,
        )
    ).first()

    if not char:
        raise HTTPException(status_code=403, detail="Character not found or unauthorized")

    sync_character_fittings.delay(char.character_id)

    return {"status": "sync started", "character_id": character_id}
