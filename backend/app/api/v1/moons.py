"""
Moon mining API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.moon import MoonExtraction, Moon, MiningLedger
from app.tasks.moon_sync import sync_moon_extractions, sync_mining_ledger

router = APIRouter()


# Pydantic models
class MoonExtractionResponse(BaseModel):
    id: int
    structure_id: int
    moon_id: int
    chunk_arrival_time: datetime
    extraction_start_time: datetime
    natural_decay_time: Optional[datetime]
    status: Optional[str]
    synced_at: Optional[datetime]

    class Config:
        from_attributes = True


class MoonResponse(BaseModel):
    id: int
    moon_id: int
    system_id: int
    name: Optional[str]
    composition: Optional[dict]
    estimated_value: Optional[int]
    last_scanned: Optional[datetime]

    class Config:
        from_attributes = True


class MiningLedgerResponse(BaseModel):
    id: int
    character_id: int
    date: datetime
    type_id: int
    quantity: int
    system_id: int

    class Config:
        from_attributes = True


class MoonExtractionStatistics(BaseModel):
    total_extractions: int
    active_extractions: int  # status = started
    ready_extractions: int  # status = ready
    upcoming_arrivals: int  # Arrivals in next 24 hours
    extractions_by_moon: dict  # {moon_id: count}


class MiningStatistics(BaseModel):
    total_miners: int
    total_quantity: int
    mining_by_character: dict  # {character_id: quantity}
    mining_by_type: dict  # {type_id: quantity}
    mining_by_system: dict  # {system_id: quantity}


@router.get("/extractions", response_model=List[MoonExtractionResponse])
async def list_extractions(
    corporation_id: Optional[int] = Query(None),
    moon_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List moon extractions
    """
    query = db.query(MoonExtraction)

    if corporation_id:
        query = query.filter(MoonExtraction.corporation_id == corporation_id)

    if moon_id:
        query = query.filter(MoonExtraction.moon_id == moon_id)

    if status:
        query = query.filter(MoonExtraction.status == status)

    extractions = query.order_by(MoonExtraction.chunk_arrival_time.desc()).offset(offset).limit(limit).all()
    return extractions


@router.get("/extractions/statistics/{corporation_id}", response_model=MoonExtractionStatistics)
async def get_extraction_statistics(
    corporation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get moon extraction statistics
    """
    from datetime import timedelta

    extractions = db.query(MoonExtraction).filter(
        MoonExtraction.corporation_id == corporation_id
    ).all()

    total_extractions = len(extractions)
    active_extractions = len([e for e in extractions if e.status == "started"])
    ready_extractions = len([e for e in extractions if e.status == "ready"])

    # Upcoming arrivals (next 24 hours)
    now = datetime.utcnow()
    upcoming_threshold = now + timedelta(hours=24)
    upcoming_arrivals = len([
        e for e in extractions
        if e.chunk_arrival_time and now < e.chunk_arrival_time < upcoming_threshold
    ])

    # By moon
    extractions_by_moon = {}
    for extraction in extractions:
        moon_id = str(extraction.moon_id)
        extractions_by_moon[moon_id] = extractions_by_moon.get(moon_id, 0) + 1

    return {
        "total_extractions": total_extractions,
        "active_extractions": active_extractions,
        "ready_extractions": ready_extractions,
        "upcoming_arrivals": upcoming_arrivals,
        "extractions_by_moon": extractions_by_moon,
    }


@router.get("/moons", response_model=List[MoonResponse])
async def list_moons(
    system_id: Optional[int] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List moons
    """
    query = db.query(Moon)

    if system_id:
        query = query.filter(Moon.system_id == system_id)

    moons = query.order_by(Moon.moon_id).offset(offset).limit(limit).all()
    return moons


@router.get("/ledger", response_model=List[MiningLedgerResponse])
async def list_mining_ledger(
    corporation_id: Optional[int] = Query(None),
    character_id: Optional[int] = Query(None),
    system_id: Optional[int] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List mining ledger entries
    """
    query = db.query(MiningLedger)

    if corporation_id:
        query = query.filter(MiningLedger.corporation_id == corporation_id)

    if character_id:
        query = query.filter(MiningLedger.character_id == character_id)

    if system_id:
        query = query.filter(MiningLedger.system_id == system_id)

    ledger = query.order_by(MiningLedger.date.desc()).offset(offset).limit(limit).all()
    return ledger


@router.get("/ledger/statistics/{corporation_id}", response_model=MiningStatistics)
async def get_mining_statistics(
    corporation_id: int,
    days: int = Query(30, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get mining statistics
    """
    from datetime import timedelta

    cutoff_date = datetime.utcnow() - timedelta(days=days)

    ledger_entries = db.query(MiningLedger).filter(
        MiningLedger.corporation_id == corporation_id,
        MiningLedger.date >= cutoff_date
    ).all()

    total_quantity = sum(entry.quantity for entry in ledger_entries)
    unique_miners = len(set(entry.character_id for entry in ledger_entries))

    # By character
    mining_by_character = {}
    for entry in ledger_entries:
        char_id = str(entry.character_id)
        mining_by_character[char_id] = mining_by_character.get(char_id, 0) + entry.quantity

    # By type
    mining_by_type = {}
    for entry in ledger_entries:
        type_id = str(entry.type_id)
        mining_by_type[type_id] = mining_by_type.get(type_id, 0) + entry.quantity

    # By system
    mining_by_system = {}
    for entry in ledger_entries:
        system_id = str(entry.system_id)
        mining_by_system[system_id] = mining_by_system.get(system_id, 0) + entry.quantity

    return {
        "total_miners": unique_miners,
        "total_quantity": total_quantity,
        "mining_by_character": mining_by_character,
        "mining_by_type": mining_by_type,
        "mining_by_system": mining_by_system,
    }


@router.post("/extractions/sync/{corporation_id}")
async def trigger_extraction_sync(
    corporation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Trigger moon extraction sync
    """
    sync_moon_extractions.delay(corporation_id)
    return {"message": "Moon extraction sync started"}


@router.post("/ledger/sync/{corporation_id}")
async def trigger_ledger_sync(
    corporation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Trigger mining ledger sync
    """
    sync_mining_ledger.delay(corporation_id)
    return {"message": "Mining ledger sync started"}
