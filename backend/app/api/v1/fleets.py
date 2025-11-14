"""
Fleet endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
import logging

from app.core.database import get_db
from app.models.fleet import Fleet, FleetMember, Doctrine
from app.models.eve_token import EveToken
from app.core.encryption import encryption
from app.services.esi_client import esi_client, ESIError
import asyncio

logger = logging.getLogger(__name__)

router = APIRouter()


class FleetResponse(BaseModel):
    """Fleet response model"""
    id: int
    fleet_id: int
    commander_character_id: int
    commander_character_name: Optional[str]
    fleet_name: Optional[str]
    is_free_move: bool
    is_registered: bool
    is_voice_enabled: bool
    motd: Optional[str]
    doctrine_id: Optional[int]
    last_synced_at: Optional[str]
    
    class Config:
        from_attributes = True


class FleetMemberResponse(BaseModel):
    """Fleet member response model"""
    id: int
    character_id: int
    character_name: Optional[str]
    ship_type_id: Optional[int]
    ship_type_name: Optional[str]
    solar_system_id: Optional[int]
    solar_system_name: Optional[str]
    station_id: Optional[int]
    station_name: Optional[str]
    wing_id: Optional[int]
    squad_id: Optional[int]
    role: Optional[str]
    role_name: Optional[str]
    takes_fleet_warp: bool
    last_synced_at: Optional[str]
    
    class Config:
        from_attributes = True


class DoctrineResponse(BaseModel):
    """Doctrine response model"""
    id: int
    doctrine_name: str
    doctrine_description: Optional[str]
    doctrine_definition: dict
    is_active: bool
    created_by_character_id: Optional[int]
    created_by_character_name: Optional[str]
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


class DoctrineCheckRequest(BaseModel):
    """Doctrine check request model"""
    doctrine_id: int


class DoctrineCheckResponse(BaseModel):
    """Doctrine check response model"""
    fleet_id: int
    doctrine_id: int
    compliance: dict
    members_compliant: List[dict]
    members_non_compliant: List[dict]


def run_async(coro):
    """Helper to run async functions in sync context"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


@router.get("/", response_model=List[FleetResponse])
async def list_fleets(
    character_id: int = Query(..., description="Character ID with fleet access"),
    db: Session = Depends(get_db),
):
    """
    List fleets for a character
    
    Args:
        character_id: EVE character ID
        db: Database session
    """
    try:
        # Get access token for character
        token = db.query(EveToken).filter(
            EveToken.character_id == character_id
        ).first()
        
        if not token:
            raise HTTPException(status_code=404, detail="Token not found")
        
        # Decrypt access token
        access_token = encryption.decrypt(token.access_token_encrypted)
        
        # Fetch fleet from ESI
        try:
            fleet_data = run_async(
                esi_client.request(
                    "GET",
                    f"/characters/{character_id}/fleet/",
                    access_token=access_token,
                )
            )
            
            fleet_id = fleet_data.get("fleet_id")
            
            if not fleet_id:
                return []
            
            # Get or create fleet in database
            fleet = db.query(Fleet).filter(
                Fleet.fleet_id == fleet_id
            ).first()
            
            if not fleet:
                # Create fleet record
                fleet = Fleet(
                    fleet_id=fleet_id,
                    commander_character_id=character_id,
                    fleet_data=fleet_data,
                    last_synced_at=datetime.utcnow(),
                )
                db.add(fleet)
                db.commit()
            
            return [fleet]
            
        except ESIError as e:
            if "404" in str(e):
                # Character is not in a fleet
                return []
            raise HTTPException(status_code=500, detail=f"Failed to fetch fleet: {e}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing fleets: {e}")
        raise HTTPException(status_code=500, detail="Failed to list fleets")


@router.get("/{fleet_id}", response_model=FleetResponse)
async def get_fleet(
    fleet_id: int,
    character_id: int = Query(..., description="Character ID with fleet access"),
    db: Session = Depends(get_db),
):
    """
    Get fleet details
    
    Args:
        fleet_id: EVE fleet ID
        character_id: Character ID with access to the fleet
        db: Database session
    """
    try:
        fleet = db.query(Fleet).filter(
            Fleet.fleet_id == fleet_id
        ).first()
        
        if not fleet:
            raise HTTPException(status_code=404, detail="Fleet not found")
        
        # Get access token
        token = db.query(EveToken).filter(
            EveToken.character_id == character_id
        ).first()
        
        if not token:
            raise HTTPException(status_code=404, detail="Token not found")
        
        # Decrypt access token
        access_token = encryption.decrypt(token.access_token_encrypted)
        
        # Fetch latest fleet data from ESI
        try:
            fleet_data = run_async(
                esi_client.request(
                    "GET",
                    f"/fleets/{fleet_id}/",
                    access_token=access_token,
                )
            )
            
            # Update fleet
            fleet.fleet_name = fleet_data.get("name")
            fleet.is_free_move = fleet_data.get("is_free_move", False)
            fleet.is_registered = fleet_data.get("is_registered", False)
            fleet.is_voice_enabled = fleet_data.get("is_voice_enabled", False)
            fleet.motd = fleet_data.get("motd")
            fleet.fleet_data = fleet_data
            fleet.last_synced_at = datetime.utcnow()
            
            db.commit()
            
        except ESIError as e:
            logger.warning(f"Failed to sync fleet data: {e}")
        
        return fleet
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting fleet {fleet_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get fleet")


@router.get("/{fleet_id}/members", response_model=List[FleetMemberResponse])
async def get_fleet_members(
    fleet_id: int,
    character_id: int = Query(..., description="Character ID with fleet access"),
    db: Session = Depends(get_db),
):
    """
    Get fleet members
    
    Args:
        fleet_id: EVE fleet ID
        character_id: Character ID with access to the fleet
        db: Database session
    """
    try:
        # Get access token
        token = db.query(EveToken).filter(
            EveToken.character_id == character_id
        ).first()
        
        if not token:
            raise HTTPException(status_code=404, detail="Token not found")
        
        # Decrypt access token
        access_token = encryption.decrypt(token.access_token_encrypted)
        
        # Fetch fleet members from ESI
        try:
            members_data = run_async(
                esi_client.request(
                    "GET",
                    f"/fleets/{fleet_id}/members/",
                    access_token=access_token,
                )
            )
            
            # Update fleet members in database
            # Clear existing members
            db.query(FleetMember).filter(
                FleetMember.fleet_id == fleet_id
            ).delete()
            
            # Add new members
            for member_data in members_data:
                member = FleetMember(
                    fleet_id=fleet_id,
                    character_id=member_data.get("character_id"),
                    ship_type_id=member_data.get("ship_type_id"),
                    solar_system_id=member_data.get("solar_system_id"),
                    station_id=member_data.get("station_id"),
                    wing_id=member_data.get("wing_id"),
                    squad_id=member_data.get("squad_id"),
                    role=member_data.get("role"),
                    role_name=member_data.get("role_name"),
                    takes_fleet_warp=member_data.get("takes_fleet_warp", True),
                    member_data=member_data,
                    last_synced_at=datetime.utcnow(),
                )
                db.add(member)
            
            db.commit()
            
            # Return members
            members = db.query(FleetMember).filter(
                FleetMember.fleet_id == fleet_id
            ).all()
            
            return members
            
        except ESIError as e:
            logger.error(f"Failed to fetch fleet members: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to fetch fleet members: {e}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting fleet members: {e}")
        raise HTTPException(status_code=500, detail="Failed to get fleet members")


@router.post("/{fleet_id}/doctrine-check", response_model=DoctrineCheckResponse)
async def check_doctrine_compliance(
    fleet_id: int,
    request: DoctrineCheckRequest = Body(...),
    character_id: int = Query(..., description="Character ID with fleet access"),
    db: Session = Depends(get_db),
):
    """
    Check fleet compliance with a doctrine
    
    Args:
        fleet_id: EVE fleet ID
        request: Doctrine check request with doctrine_id
        character_id: Character ID with access to the fleet
        db: Database session
    """
    try:
        # Get fleet
        fleet = db.query(Fleet).filter(
            Fleet.fleet_id == fleet_id
        ).first()
        
        if not fleet:
            raise HTTPException(status_code=404, detail="Fleet not found")
        
        # Get doctrine
        doctrine = db.query(Doctrine).filter(
            Doctrine.id == request.doctrine_id
        ).first()
        
        if not doctrine:
            raise HTTPException(status_code=404, detail="Doctrine not found")
        
        # Get fleet members
        members = db.query(FleetMember).filter(
            FleetMember.fleet_id == fleet_id
        ).all()
        
        # Check compliance
        doctrine_def = doctrine.doctrine_definition
        required_ships = doctrine_def.get("ships", [])
        required_ship_types = {ship.get("type_id") for ship in required_ships if ship.get("type_id")}
        
        members_compliant = []
        members_non_compliant = []
        
        for member in members:
            is_compliant = member.ship_type_id in required_ship_types if member.ship_type_id else False
            
            member_info = {
                "character_id": member.character_id,
                "character_name": member.character_name,
                "ship_type_id": member.ship_type_id,
                "ship_type_name": member.ship_type_name,
                "is_compliant": is_compliant,
            }
            
            if is_compliant:
                members_compliant.append(member_info)
            else:
                members_non_compliant.append(member_info)
        
        compliance_rate = len(members_compliant) / len(members) if members else 0
        
        return {
            "fleet_id": fleet_id,
            "doctrine_id": request.doctrine_id,
            "compliance": {
                "total_members": len(members),
                "compliant": len(members_compliant),
                "non_compliant": len(members_non_compliant),
                "compliance_rate": compliance_rate,
            },
            "members_compliant": members_compliant,
            "members_non_compliant": members_non_compliant,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking doctrine compliance: {e}")
        raise HTTPException(status_code=500, detail="Failed to check doctrine compliance")


@router.get("/doctrines", response_model=List[DoctrineResponse])
async def list_doctrines(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db),
):
    """
    List all doctrines
    
    Args:
        is_active: Optional filter by active status
        db: Database session
    """
    try:
        query = db.query(Doctrine)
        
        if is_active is not None:
            query = query.filter(Doctrine.is_active == is_active)
        
        doctrines = query.all()
        
        return doctrines
        
    except Exception as e:
        logger.error(f"Error listing doctrines: {e}")
        raise HTTPException(status_code=500, detail="Failed to list doctrines")


@router.post("/doctrines", response_model=DoctrineResponse)
async def create_doctrine(
    doctrine_name: str = Body(...),
    doctrine_description: Optional[str] = Body(None),
    doctrine_definition: dict = Body(...),
    character_id: int = Query(..., description="Character ID creating the doctrine"),
    db: Session = Depends(get_db),
):
    """
    Create a new doctrine
    
    Args:
        doctrine_name: Name of the doctrine
        doctrine_description: Optional description
        doctrine_definition: Doctrine definition (ships, roles, etc.)
        character_id: Character ID creating the doctrine
        db: Database session
    """
    try:
        # Get character name
        from app.models.character import Character
        character = db.query(Character).filter(
            Character.character_id == character_id
        ).first()
        
        doctrine = Doctrine(
            doctrine_name=doctrine_name,
            doctrine_description=doctrine_description,
            doctrine_definition=doctrine_definition,
            is_active=True,
            created_by_character_id=character_id,
            created_by_character_name=character.character_name if character else None,
        )
        
        db.add(doctrine)
        db.commit()
        db.refresh(doctrine)
        
        return doctrine
        
    except Exception as e:
        logger.error(f"Error creating doctrine: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create doctrine")
