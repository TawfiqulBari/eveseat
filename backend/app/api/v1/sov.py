"""
Sovereignty API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.sovereignty import SystemSovereignty, SovereigntyStructure, SovereigntyCampaign
from app.tasks.sovereignty_sync import sync_sovereignty_data

router = APIRouter()


# Pydantic models
class SystemSovereigntyResponse(BaseModel):
    id: int
    system_id: int
    alliance_id: Optional[int]
    corporation_id: Optional[int]
    faction_id: Optional[int]
    ihub_vulnerability_timer: Optional[float]
    tcu_vulnerability_timer: Optional[float]
    synced_at: Optional[datetime]

    class Config:
        from_attributes = True


class SovereigntyStructureResponse(BaseModel):
    id: int
    structure_id: int
    system_id: int
    structure_type_id: int
    alliance_id: int
    vulnerable_start_time: Optional[datetime]
    vulnerable_end_time: Optional[datetime]
    vulnerability_occupancy_level: Optional[float]
    synced_at: Optional[datetime]

    class Config:
        from_attributes = True


class SovereigntyCampaignResponse(BaseModel):
    id: int
    campaign_id: int
    system_id: int
    constellation_id: int
    structure_id: int
    event_type: str
    defender_id: Optional[int]
    defender_score: float
    attackers_score: float
    start_time: datetime
    synced_at: Optional[datetime]

    class Config:
        from_attributes = True


class SovereigntyStatistics(BaseModel):
    total_systems: int
    systems_by_alliance: dict  # {alliance_id: count}
    systems_by_faction: dict  # {faction_id: count}
    vulnerable_structures: int
    active_campaigns: int


@router.get("/systems", response_model=List[SystemSovereigntyResponse])
async def list_system_sovereignty(
    alliance_id: Optional[int] = Query(None),
    corporation_id: Optional[int] = Query(None),
    faction_id: Optional[int] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List system sovereignty
    """
    query = db.query(SystemSovereignty)

    if alliance_id:
        query = query.filter(SystemSovereignty.alliance_id == alliance_id)

    if corporation_id:
        query = query.filter(SystemSovereignty.corporation_id == corporation_id)

    if faction_id:
        query = query.filter(SystemSovereignty.faction_id == faction_id)

    systems = query.order_by(SystemSovereignty.system_id).offset(offset).limit(limit).all()
    return systems


@router.get("/systems/{system_id}", response_model=SystemSovereigntyResponse)
async def get_system_sovereignty(
    system_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get sovereignty for a specific system
    """
    sov = db.query(SystemSovereignty).filter(SystemSovereignty.system_id == system_id).first()
    if not sov:
        raise HTTPException(status_code=404, detail="Sovereignty data not found")
    return sov


@router.get("/structures", response_model=List[SovereigntyStructureResponse])
async def list_sovereignty_structures(
    alliance_id: Optional[int] = Query(None),
    system_id: Optional[int] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List sovereignty structures (TCU, IHUB)
    """
    query = db.query(SovereigntyStructure)

    if alliance_id:
        query = query.filter(SovereigntyStructure.alliance_id == alliance_id)

    if system_id:
        query = query.filter(SovereigntyStructure.system_id == system_id)

    structures = query.order_by(SovereigntyStructure.system_id).offset(offset).limit(limit).all()
    return structures


@router.get("/campaigns", response_model=List[SovereigntyCampaignResponse])
async def list_sovereignty_campaigns(
    system_id: Optional[int] = Query(None),
    defender_id: Optional[int] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List active sovereignty campaigns
    """
    query = db.query(SovereigntyCampaign)

    if system_id:
        query = query.filter(SovereigntyCampaign.system_id == system_id)

    if defender_id:
        query = query.filter(SovereigntyCampaign.defender_id == defender_id)

    campaigns = query.order_by(SovereigntyCampaign.start_time.desc()).offset(offset).limit(limit).all()
    return campaigns


@router.get("/statistics", response_model=SovereigntyStatistics)
async def get_sovereignty_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get sovereignty statistics
    """
    systems = db.query(SystemSovereignty).all()
    structures = db.query(SovereigntyStructure).all()
    campaigns = db.query(SovereigntyCampaign).all()

    total_systems = len(systems)

    # By alliance
    systems_by_alliance = {}
    for system in systems:
        if system.alliance_id:
            alliance_id = str(system.alliance_id)
            systems_by_alliance[alliance_id] = systems_by_alliance.get(alliance_id, 0) + 1

    # By faction
    systems_by_faction = {}
    for system in systems:
        if system.faction_id:
            faction_id = str(system.faction_id)
            systems_by_faction[faction_id] = systems_by_faction.get(faction_id, 0) + 1

    # Vulnerable structures
    now = datetime.utcnow()
    vulnerable_structures = len([
        s for s in structures
        if s.vulnerable_start_time and s.vulnerable_end_time
        and s.vulnerable_start_time <= now <= s.vulnerable_end_time
    ])

    active_campaigns = len(campaigns)

    return {
        "total_systems": total_systems,
        "systems_by_alliance": systems_by_alliance,
        "systems_by_faction": systems_by_faction,
        "vulnerable_structures": vulnerable_structures,
        "active_campaigns": active_campaigns,
    }


@router.post("/sync")
async def trigger_sovereignty_sync(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Trigger sovereignty data sync
    """
    sync_sovereignty_data.delay()
    return {"message": "Sovereignty sync started"}
