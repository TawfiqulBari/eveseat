"""
Incursions API endpoints
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.incursion import Incursion
from app.tasks.incursion_sync import sync_incursions_data

router = APIRouter()


class IncursionResponse(BaseModel):
    id: int
    constellation_id: int
    state: str
    influence: float
    staging_solar_system_id: Optional[int]
    has_boss: bool
    is_active: bool

    class Config:
        from_attributes = True


@router.get("/", response_model=List[IncursionResponse])
async def list_incursions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List active incursions"""
    incursions = db.query(Incursion).filter(Incursion.is_active == True).all()
    return incursions


@router.post("/sync")
async def trigger_incursions_sync(
    current_user: User = Depends(get_current_user),
):
    """Trigger incursions sync"""
    sync_incursions_data.delay()
    return {"message": "Incursions sync started"}
