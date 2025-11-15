"""
Faction Warfare API endpoints
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from pydantic import BaseModel

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.faction_warfare import FactionWarfareSystem, FactionWarfareStatistics
from app.tasks.faction_warfare_sync import sync_faction_warfare_data

router = APIRouter()


class FWSystemResponse(BaseModel):
    id: int
    solar_system_id: int
    occupier_faction_id: int
    owner_faction_id: int
    contested: str
    victory_points: int

    class Config:
        from_attributes = True


class FWStatisticsResponse(BaseModel):
    id: int
    faction_id: int
    kills_yesterday: int
    kills_last_week: int
    victory_points_yesterday: int
    pilots: int
    systems_controlled: int

    class Config:
        from_attributes = True


@router.get("/systems", response_model=List[FWSystemResponse])
async def list_fw_systems(
    faction_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List faction warfare systems"""
    query = db.query(FactionWarfareSystem)
    if faction_id:
        query = query.filter(FactionWarfareSystem.occupier_faction_id == faction_id)
    systems = query.all()
    return systems


@router.get("/statistics", response_model=List[FWStatisticsResponse])
async def get_fw_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get faction warfare statistics"""
    from datetime import timedelta
    recent_date = datetime.utcnow() - timedelta(days=1)
    stats = db.query(FactionWarfareStatistics).filter(
        FactionWarfareStatistics.date >= recent_date
    ).all()
    return stats


@router.post("/sync")
async def trigger_fw_sync(
    current_user: User = Depends(get_current_user),
):
    """Trigger faction warfare sync"""
    sync_faction_warfare_data.delay()
    return {"message": "Faction warfare sync started"}
