"""
Corporation endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
import logging

from app.core.database import get_db
from app.models.corporation import (
    Corporation, CorporationMember, CorporationAsset, CorporationStructure
)
from app.tasks.corporation_sync import sync_corporation_data

logger = logging.getLogger(__name__)

router = APIRouter()


class CorporationResponse(BaseModel):
    """Corporation response model"""
    id: int
    corporation_id: int
    corporation_name: str
    ticker: Optional[str]
    ceo_id: Optional[int]
    ceo_name: Optional[str]
    alliance_id: Optional[int]
    alliance_name: Optional[str]
    member_count: Optional[int]
    tax_rate: Optional[float]
    description: Optional[str]
    url: Optional[str]
    faction_id: Optional[int]
    home_station_id: Optional[int]
    last_synced_at: Optional[str]
    
    class Config:
        from_attributes = True


class CorporationMemberResponse(BaseModel):
    """Corporation member response model"""
    id: int
    character_id: int
    character_name: str
    start_date: Optional[str]
    roles: Optional[list]
    grantable_roles: Optional[list]
    roles_at_hq: Optional[list]
    roles_at_base: Optional[list]
    roles_at_other: Optional[list]
    last_synced_at: Optional[str]
    
    class Config:
        from_attributes = True


class CorporationAssetResponse(BaseModel):
    """Corporation asset response model"""
    id: int
    type_id: int
    type_name: Optional[str]
    quantity: int
    location_id: Optional[int]
    location_type: Optional[str]
    location_name: Optional[str]
    is_singleton: bool
    item_id: Optional[int]
    flag: Optional[str]
    last_synced_at: Optional[str]
    
    class Config:
        from_attributes = True


class CorporationStructureResponse(BaseModel):
    """Corporation structure response model"""
    id: int
    structure_id: int
    structure_type_id: Optional[int]
    structure_name: Optional[str]
    system_id: Optional[int]
    system_name: Optional[str]
    fuel_expires: Optional[str]
    state: Optional[str]
    state_timer_start: Optional[str]
    state_timer_end: Optional[str]
    unanchors_at: Optional[str]
    reinforce_hour: Optional[int]
    reinforce_weekday: Optional[int]
    services: Optional[list]
    last_synced_at: Optional[str]
    
    class Config:
        from_attributes = True


@router.get("/{corporation_id}", response_model=CorporationResponse)
async def get_corporation(
    corporation_id: int,
    force_sync: bool = Query(False, description="Force sync from ESI"),
    db: Session = Depends(get_db),
):
    """
    Get corporation information
    
    Args:
        corporation_id: EVE corporation ID
        force_sync: If True, triggers a sync from ESI before returning
        db: Database session
    """
    try:
        corporation = db.query(Corporation).filter(
            Corporation.corporation_id == corporation_id
        ).first()
        
        # If not found or force_sync, trigger sync
        if not corporation or force_sync:
            # Queue sync task
            sync_corporation_data.delay(corporation_id)
            
            if not corporation:
                raise HTTPException(
                    status_code=404,
                    detail="Corporation not found. Sync has been queued."
                )
        
        return corporation
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting corporation {corporation_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get corporation")


@router.get("/{corporation_id}/members", response_model=List[CorporationMemberResponse])
async def get_members(
    corporation_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """
    Get corporation members
    
    Args:
        corporation_id: EVE corporation ID
        skip: Number of records to skip
        limit: Number of records to return
        db: Database session
    """
    try:
        # Verify corporation exists
        corporation = db.query(Corporation).filter(
            Corporation.corporation_id == corporation_id
        ).first()
        
        if not corporation:
            raise HTTPException(status_code=404, detail="Corporation not found")
        
        members = db.query(CorporationMember).filter(
            CorporationMember.corporation_id == corporation_id
        ).offset(skip).limit(limit).all()
        
        total = db.query(CorporationMember).filter(
            CorporationMember.corporation_id == corporation_id
        ).count()
        
        return {
            "items": members,
            "total": total,
            "skip": skip,
            "limit": limit,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting corporation members: {e}")
        raise HTTPException(status_code=500, detail="Failed to get corporation members")


@router.get("/{corporation_id}/assets", response_model=List[CorporationAssetResponse])
async def get_assets(
    corporation_id: int,
    location_id: Optional[int] = Query(None, description="Filter by location ID"),
    type_id: Optional[int] = Query(None, description="Filter by type ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """
    Get corporation assets
    
    Args:
        corporation_id: EVE corporation ID
        location_id: Optional filter by location
        type_id: Optional filter by item type
        skip: Number of records to skip
        limit: Number of records to return
        db: Database session
    """
    try:
        # Verify corporation exists
        corporation = db.query(Corporation).filter(
            Corporation.corporation_id == corporation_id
        ).first()
        
        if not corporation:
            raise HTTPException(status_code=404, detail="Corporation not found")
        
        query = db.query(CorporationAsset).filter(
            CorporationAsset.corporation_id == corporation_id
        )
        
        if location_id:
            query = query.filter(CorporationAsset.location_id == location_id)
        
        if type_id:
            query = query.filter(CorporationAsset.type_id == type_id)
        
        assets = query.offset(skip).limit(limit).all()
        total = query.count()
        
        return {
            "items": assets,
            "total": total,
            "skip": skip,
            "limit": limit,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting corporation assets: {e}")
        raise HTTPException(status_code=500, detail="Failed to get corporation assets")


@router.get("/{corporation_id}/structures", response_model=List[CorporationStructureResponse])
async def get_structures(
    corporation_id: int,
    system_id: Optional[int] = Query(None, description="Filter by system ID"),
    state: Optional[str] = Query(None, description="Filter by structure state"),
    db: Session = Depends(get_db),
):
    """
    Get corporation structures
    
    Args:
        corporation_id: EVE corporation ID
        system_id: Optional filter by system
        state: Optional filter by structure state
        db: Database session
    """
    try:
        # Verify corporation exists
        corporation = db.query(Corporation).filter(
            Corporation.corporation_id == corporation_id
        ).first()
        
        if not corporation:
            raise HTTPException(status_code=404, detail="Corporation not found")
        
        query = db.query(CorporationStructure).filter(
            CorporationStructure.corporation_id == corporation_id
        )
        
        if system_id:
            query = query.filter(CorporationStructure.system_id == system_id)
        
        if state:
            query = query.filter(CorporationStructure.state == state)
        
        structures = query.all()
        
        return {
            "items": structures,
            "total": len(structures),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting corporation structures: {e}")
        raise HTTPException(status_code=500, detail="Failed to get corporation structures")


@router.post("/{corporation_id}/sync")
async def trigger_sync(
    corporation_id: int,
    db: Session = Depends(get_db),
):
    """
    Manually trigger corporation data sync from ESI
    
    Args:
        corporation_id: EVE corporation ID
        db: Database session
    """
    try:
        # Queue sync task
        task = sync_corporation_data.delay(corporation_id)
        
        return {
            "message": "Corporation sync queued",
            "corporation_id": corporation_id,
            "task_id": task.id,
        }
        
    except Exception as e:
        logger.error(f"Error queuing corporation sync: {e}")
        raise HTTPException(status_code=500, detail="Failed to queue corporation sync")
