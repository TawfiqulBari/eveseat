"""
Wars API endpoints
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.war import War
from app.tasks.war_sync import sync_wars_data

router = APIRouter()


class WarResponse(BaseModel):
    id: int
    war_id: int
    aggressor_alliance_id: Optional[int]
    defender_alliance_id: Optional[int]
    aggressor_isk_destroyed: int
    defender_isk_destroyed: int
    declared: datetime
    is_active: bool
    mutual: bool

    class Config:
        from_attributes = True


@router.get("/", response_model=List[WarResponse])
async def list_wars(
    active_only: bool = Query(True),
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List wars"""
    query = db.query(War)
    if active_only:
        query = query.filter(War.is_active == True)
    wars = query.order_by(War.declared.desc()).limit(limit).all()
    return wars


@router.post("/sync")
async def trigger_wars_sync(
    current_user: User = Depends(get_current_user),
):
    """Trigger wars sync"""
    sync_wars_data.delay()
    return {"message": "Wars sync started"}
