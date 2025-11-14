"""
Map endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime, timedelta
import logging

from app.core.database import get_db
from app.models.universe import System, SystemActivity

logger = logging.getLogger(__name__)

router = APIRouter()


class SystemResponse(BaseModel):
    """System response model"""
    id: int
    system_id: int
    system_name: str
    constellation_id: int
    constellation_name: Optional[str]
    region_id: int
    region_name: Optional[str]
    x: Optional[float]
    y: Optional[float]
    z: Optional[float]
    security_status: float
    security_class: Optional[str]
    system_type: Optional[str]
    
    class Config:
        from_attributes = True


class SystemActivityResponse(BaseModel):
    """System activity response model"""
    system_id: int
    system_name: Optional[str]
    kills_last_hour: int
    jumps_last_hour: int
    npc_kills_last_hour: int
    pod_kills_last_hour: int
    ship_kills_last_hour: int
    timestamp: datetime
    
    class Config:
        from_attributes = True


@router.get("/systems", response_model=List[SystemResponse])
async def get_systems(
    region_id: Optional[int] = Query(None, description="Filter by region ID"),
    constellation_id: Optional[int] = Query(None, description="Filter by constellation ID"),
    min_security: Optional[float] = Query(None, ge=-1.0, le=1.0, description="Minimum security status"),
    max_security: Optional[float] = Query(None, ge=-1.0, le=1.0, description="Maximum security status"),
    system_type: Optional[str] = Query(None, description="Filter by system type (e.g., 'k-space', 'w-space')"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(1000, ge=1, le=10000, description="Number of records to return"),
    db: Session = Depends(get_db),
):
    """
    Get universe systems with optional filters
    
    Supports filtering by:
    - Region
    - Constellation
    - Security status range
    - System type
    """
    try:
        query = db.query(System)
        
        # Apply filters
        if region_id:
            query = query.filter(System.region_id == region_id)
        
        if constellation_id:
            query = query.filter(System.constellation_id == constellation_id)
        
        if min_security is not None:
            query = query.filter(System.security_status >= min_security)
        
        if max_security is not None:
            query = query.filter(System.security_status <= max_security)
        
        if system_type:
            query = query.filter(System.system_type == system_type)
        
        # Apply pagination
        systems = query.offset(skip).limit(limit).all()
        
        return [SystemResponse.model_validate(s) for s in systems]
        
    except Exception as e:
        logger.error(f"Error getting systems: {e}")
        raise HTTPException(status_code=500, detail="Failed to get systems")


@router.get("/systems/{system_id}", response_model=SystemResponse)
async def get_system(
    system_id: int,
    db: Session = Depends(get_db),
):
    """
    Get a specific system by ID
    """
    try:
        system = db.query(System).filter(
            System.system_id == system_id
        ).first()
        
        if not system:
            raise HTTPException(status_code=404, detail="System not found")
        
        return SystemResponse.model_validate(system)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting system {system_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get system")


@router.get("/activity", response_model=List[SystemActivityResponse])
async def get_activity(
    system_id: Optional[int] = Query(None, description="Filter by system ID"),
    region_id: Optional[int] = Query(None, description="Filter by region ID"),
    hours: int = Query(24, ge=1, le=168, description="Number of hours to look back"),
    min_kills: Optional[int] = Query(None, ge=0, description="Minimum kills in last hour"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    db: Session = Depends(get_db),
):
    """
    Get system activity data
    
    Returns recent activity metrics for systems including:
    - Kills (player, NPC, pod, ship)
    - Jumps
    """
    try:
        # Calculate time threshold
        time_threshold = datetime.utcnow() - timedelta(hours=hours)
        
        query = db.query(SystemActivity).filter(
            SystemActivity.timestamp >= time_threshold
        )
        
        # Apply filters
        if system_id:
            query = query.filter(SystemActivity.system_id == system_id)
        
        if region_id:
            # Join with System to filter by region
            query = query.join(System, SystemActivity.system_id == System.system_id).filter(
                System.region_id == region_id
            )
        
        if min_kills is not None:
            query = query.filter(SystemActivity.kills_last_hour >= min_kills)
        
        # Order by timestamp descending (most recent first)
        query = query.order_by(desc(SystemActivity.timestamp))
        
        # Apply pagination
        activities = query.offset(skip).limit(limit).all()
        
        # Fetch system names for response
        system_ids = [a.system_id for a in activities]
        systems = db.query(System).filter(
            System.system_id.in_(system_ids)
        ).all()
        system_map = {s.system_id: s.system_name for s in systems}
        
        # Build response
        result = []
        for activity in activities:
            activity_dict = SystemActivityResponse.model_validate(activity).model_dump()
            activity_dict["system_name"] = system_map.get(activity.system_id)
            result.append(SystemActivityResponse(**activity_dict))
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting activity: {e}")
        raise HTTPException(status_code=500, detail="Failed to get activity")


@router.get("/activity/{system_id}", response_model=List[SystemActivityResponse])
async def get_system_activity(
    system_id: int,
    hours: int = Query(24, ge=1, le=168, description="Number of hours to look back"),
    db: Session = Depends(get_db),
):
    """
    Get activity history for a specific system
    """
    try:
        # Verify system exists
        system = db.query(System).filter(
            System.system_id == system_id
        ).first()
        
        if not system:
            raise HTTPException(status_code=404, detail="System not found")
        
        # Calculate time threshold
        time_threshold = datetime.utcnow() - timedelta(hours=hours)
        
        # Get activity records
        activities = db.query(SystemActivity).filter(
            and_(
                SystemActivity.system_id == system_id,
                SystemActivity.timestamp >= time_threshold
            )
        ).order_by(desc(SystemActivity.timestamp)).all()
        
        # Build response with system name
        result = []
        for activity in activities:
            activity_dict = SystemActivityResponse.model_validate(activity).model_dump()
            activity_dict["system_name"] = system.system_name
            result.append(SystemActivityResponse(**activity_dict))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting system activity {system_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get system activity")

