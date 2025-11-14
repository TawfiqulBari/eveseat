"""
Planetary Interaction API endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.character import Character
from app.models.planetary import Planet, PlanetPin, PlanetRoute, PlanetExtraction
from app.tasks.planetary_sync import sync_character_planets

router = APIRouter()


# Pydantic models
class PlanetResponse(BaseModel):
    id: int
    planet_id: int
    solar_system_id: int
    planet_type: str
    upgrade_level: int
    num_pins: int
    last_update: Optional[datetime]

    class Config:
        from_attributes = True


class PlanetPinResponse(BaseModel):
    id: int
    pin_id: int
    type_id: int
    schematic_id: Optional[int]
    latitude: Optional[float]
    longitude: Optional[float]
    install_time: Optional[datetime]
    expiry_time: Optional[datetime]
    product_type_id: Optional[int]
    contents: Optional[dict]

    class Config:
        from_attributes = True


class PlanetDetailResponse(BaseModel):
    planet: PlanetResponse
    pins: List[PlanetPinResponse]
    extractions: List[dict]


class PlanetStatistics(BaseModel):
    total_planets: int
    active_extractors: int
    expiring_soon: int  # < 24 hours
    total_pins: int
    by_planet_type: dict


@router.get("/", response_model=List[PlanetResponse])
async def list_planets(
    character_id: Optional[int] = Query(None),
    solar_system_id: Optional[int] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List character planets
    """
    query = db.query(Planet).join(Character).filter(
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
        query = query.filter(Planet.character_id == character_id)

    if solar_system_id:
        query = query.filter(Planet.solar_system_id == solar_system_id)

    planets = query.limit(limit).offset(offset).all()
    return planets


@router.get("/{planet_id}", response_model=PlanetDetailResponse)
async def get_planet(
    planet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get planet details with pins and extractions
    """
    planet = db.query(Planet).join(Character).filter(
        and_(
            Planet.planet_id == planet_id,
            Character.user_id == current_user.id,
        )
    ).first()

    if not planet:
        raise HTTPException(status_code=404, detail="Planet not found")

    pins = db.query(PlanetPin).filter(PlanetPin.planet_id == planet.id).all()

    extractions = db.query(PlanetExtraction).filter(
        PlanetExtraction.planet_id == planet.planet_id
    ).all()

    extraction_data = [
        {
            "pin_id": ext.pin_id,
            "product_type_id": ext.product_type_id,
            "expiry_time": ext.expiry_time,
            "status": ext.status,
        }
        for ext in extractions
    ]

    return PlanetDetailResponse(
        planet=planet,
        pins=pins,
        extractions=extraction_data,
    )


@router.get("/statistics/{character_id}", response_model=PlanetStatistics)
async def get_planet_statistics(
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get planetary interaction statistics
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

    planets = db.query(Planet).filter(Planet.character_id == character_id).all()

    total_planets = len(planets)
    total_pins = sum(p.num_pins for p in planets)

    # Get active extractions
    extractions = db.query(PlanetExtraction).filter(
        and_(
            PlanetExtraction.character_id == character_id,
            PlanetExtraction.status == "active",
        )
    ).all()

    active_extractors = len(extractions)

    # Expiring soon (< 24 hours)
    now = datetime.utcnow()
    expiring_soon = sum(
        1 for ext in extractions
        if ext.expiry_time and (ext.expiry_time - now).total_seconds() < 86400
    )

    # By planet type
    by_planet_type = {}
    for planet in planets:
        ptype = planet.planet_type
        if ptype not in by_planet_type:
            by_planet_type[ptype] = 0
        by_planet_type[ptype] += 1

    return PlanetStatistics(
        total_planets=total_planets,
        active_extractors=active_extractors,
        expiring_soon=expiring_soon,
        total_pins=total_pins,
        by_planet_type=by_planet_type,
    )


@router.post("/sync/{character_id}")
async def trigger_planetary_sync(
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Trigger planetary interaction sync for a character
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
    sync_character_planets.delay(char.character_id)

    return {"status": "sync started", "character_id": character_id}
