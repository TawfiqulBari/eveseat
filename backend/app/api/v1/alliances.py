"""
Alliances API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.alliance import Alliance, AllianceCorporation
from app.tasks.alliance_sync import sync_alliance_data

router = APIRouter()


# Pydantic models
class AllianceResponse(BaseModel):
    id: int
    alliance_id: int
    alliance_name: str
    ticker: Optional[str]
    executor_corporation_id: Optional[int]
    executor_corporation_name: Optional[str]
    date_founded: Optional[datetime]
    member_count: int
    corporation_count: int
    faction_id: Optional[int]

    class Config:
        from_attributes = True


class AllianceStatistics(BaseModel):
    total_alliances: int
    total_members: int
    largest_alliance_id: int
    largest_alliance_size: int


@router.get("/", response_model=List[AllianceResponse])
async def list_alliances(
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List alliances"""
    alliances = db.query(Alliance).order_by(Alliance.member_count.desc()).offset(offset).limit(limit).all()
    return alliances


@router.get("/{alliance_id}", response_model=AllianceResponse)
async def get_alliance(
    alliance_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get alliance details"""
    alliance = db.query(Alliance).filter(Alliance.alliance_id == alliance_id).first()
    if not alliance:
        raise HTTPException(status_code=404, detail="Alliance not found")
    return alliance


@router.get("/statistics/overview", response_model=AllianceStatistics)
async def get_alliance_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get alliance statistics"""
    from sqlalchemy import func

    total_alliances = db.query(func.count(Alliance.id)).scalar()
    total_members = db.query(func.sum(Alliance.member_count)).scalar() or 0

    largest = db.query(Alliance).order_by(Alliance.member_count.desc()).first()

    return {
        "total_alliances": total_alliances,
        "total_members": total_members,
        "largest_alliance_id": largest.alliance_id if largest else 0,
        "largest_alliance_size": largest.member_count if largest else 0
    }


@router.post("/sync/{alliance_id}")
async def trigger_alliance_sync(
    alliance_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger alliance sync"""
    sync_alliance_data.delay(alliance_id)
    return {"message": "Alliance sync started"}
