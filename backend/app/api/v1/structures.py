"""
Structures API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.structure import Structure, StructureVulnerability, StructureService
from app.tasks.structure_sync import sync_corporation_structures

router = APIRouter()


# Pydantic models
class StructureVulnerabilityResponse(BaseModel):
    id: int
    day_of_week: int
    hour: int

    class Config:
        from_attributes = True


class StructureResponse(BaseModel):
    id: int
    structure_id: int
    name: Optional[str]
    type_id: int
    system_id: int
    position_x: Optional[float]
    position_y: Optional[float]
    position_z: Optional[float]
    state: Optional[str]
    state_timer_start: Optional[datetime]
    state_timer_end: Optional[datetime]
    unanchors_at: Optional[datetime]
    fuel_expires: Optional[datetime]
    next_reinforce_hour: Optional[int]
    next_reinforce_day: Optional[int]
    services: Optional[dict]
    synced_at: Optional[datetime]

    class Config:
        from_attributes = True


class StructureStatistics(BaseModel):
    total_structures: int
    online_structures: int
    low_fuel_structures: int  # Fuel expiring in < 7 days
    structures_by_type: dict  # {type_id: count}
    structures_by_system: dict  # {system_id: count}


@router.get("/", response_model=List[StructureResponse])
async def list_structures(
    corporation_id: Optional[int] = Query(None),
    system_id: Optional[int] = Query(None),
    state: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List corporation structures
    """
    query = db.query(Structure)

    if corporation_id:
        query = query.filter(Structure.corporation_id == corporation_id)

    if system_id:
        query = query.filter(Structure.system_id == system_id)

    if state:
        query = query.filter(Structure.state == state)

    structures = query.order_by(Structure.created_at.desc()).offset(offset).limit(limit).all()
    return structures


@router.get("/{structure_id}", response_model=StructureResponse)
async def get_structure(
    structure_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get structure details
    """
    structure = db.query(Structure).filter(Structure.id == structure_id).first()
    if not structure:
        raise HTTPException(status_code=404, detail="Structure not found")
    return structure


@router.get("/statistics/{corporation_id}", response_model=StructureStatistics)
async def get_structure_statistics(
    corporation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get structure statistics for a corporation
    """
    from datetime import timedelta
    from sqlalchemy import func

    structures = db.query(Structure).filter(
        Structure.corporation_id == corporation_id
    ).all()

    total_structures = len(structures)
    online_structures = len([s for s in structures if s.state == "online"])

    # Low fuel structures (< 7 days)
    now = datetime.utcnow()
    low_fuel_threshold = now + timedelta(days=7)
    low_fuel_structures = len([
        s for s in structures
        if s.fuel_expires and s.fuel_expires < low_fuel_threshold
    ])

    # By type
    structures_by_type = {}
    for structure in structures:
        type_id = str(structure.type_id)
        structures_by_type[type_id] = structures_by_type.get(type_id, 0) + 1

    # By system
    structures_by_system = {}
    for structure in structures:
        system_id = str(structure.system_id)
        structures_by_system[system_id] = structures_by_system.get(system_id, 0) + 1

    return {
        "total_structures": total_structures,
        "online_structures": online_structures,
        "low_fuel_structures": low_fuel_structures,
        "structures_by_type": structures_by_type,
        "structures_by_system": structures_by_system,
    }


@router.post("/sync/{corporation_id}")
async def trigger_structure_sync(
    corporation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Trigger structure sync for a corporation
    """
    sync_corporation_structures.delay(corporation_id)
    return {"message": "Structure sync started"}
