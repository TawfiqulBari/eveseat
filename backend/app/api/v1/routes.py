"""
Route planning endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Body, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel, Field
import logging

from app.core.database import get_db
from app.services.route_planner import RoutePlanner
from app.models.universe import System

logger = logging.getLogger(__name__)

router = APIRouter()


class RouteRequest(BaseModel):
    """Request model for route calculation"""
    start_system_id: int = Field(..., description="Starting system ID")
    end_system_id: int = Field(..., description="Destination system ID")
    waypoints: Optional[List[int]] = Field(None, description="Optional waypoints to visit in order")
    avoid_systems: Optional[List[int]] = Field(None, description="System IDs to avoid")
    avoid_regions: Optional[List[int]] = Field(None, description="Region IDs to avoid")
    prefer_safer: bool = Field(True, description="Prefer high-security systems")
    security_penalty: float = Field(2.0, ge=0.0, description="Penalty multiplier for low-security systems")
    max_jumps: Optional[int] = Field(None, ge=1, description="Maximum number of jumps allowed")


class RouteSystemInfo(BaseModel):
    """System information in route"""
    system_id: int
    system_name: str
    security_status: float
    security_class: Optional[str]
    region_id: int
    region_name: Optional[str]
    constellation_id: int
    constellation_name: Optional[str]
    x: Optional[float]
    y: Optional[float]
    z: Optional[float]
    
    class Config:
        from_attributes = True


class RouteResponse(BaseModel):
    """Response model for route calculation"""
    route: List[RouteSystemInfo]
    total_jumps: int
    estimated_time_seconds: int
    average_security: float
    route_length: int
    segments: Optional[List[dict]] = None
    error: Optional[str] = None


@router.post("/calculate", response_model=RouteResponse)
async def calculate_route(
    request: RouteRequest = Body(...),
    db: Session = Depends(get_db),
):
    """
    Calculate route between systems using A* pathfinding
    
    Supports:
    - Direct routes between two systems
    - Routes with waypoints
    - Avoid lists (systems/regions)
    - Security preference (prefer high-sec or fastest route)
    """
    try:
        planner = RoutePlanner(db)
        
        # Calculate route
        if request.waypoints and len(request.waypoints) > 0:
            # Route with waypoints
            full_waypoints = [request.start_system_id] + request.waypoints + [request.end_system_id]
            route_ids, metadata = planner.calculate_route_with_waypoints(
                waypoints=full_waypoints,
                avoid_systems=request.avoid_systems,
                avoid_regions=request.avoid_regions,
                prefer_safer=request.prefer_safer,
                security_penalty=request.security_penalty,
            )
        else:
            # Direct route
            route_ids, metadata = planner.calculate_route(
                start_system_id=request.start_system_id,
                end_system_id=request.end_system_id,
                avoid_systems=request.avoid_systems,
                avoid_regions=request.avoid_regions,
                prefer_safer=request.prefer_safer,
                security_penalty=request.security_penalty,
                max_jumps=request.max_jumps,
            )
        
        if not route_ids:
            raise HTTPException(
                status_code=404,
                detail=metadata.get("error", "No route found")
            )
        
        # Fetch system details for route
        systems = db.query(System).filter(
            System.system_id.in_(route_ids)
        ).all()
        
        # Create a map for quick lookup
        system_map = {s.system_id: s for s in systems}
        
        # Build route with system info in order
        route_systems = []
        for system_id in route_ids:
            system = system_map.get(system_id)
            if system:
                route_systems.append(RouteSystemInfo.model_validate(system))
            else:
                # System not found in DB, create minimal info
                route_systems.append(RouteSystemInfo(
                    system_id=system_id,
                    system_name=f"System {system_id}",
                    security_status=0.0,
                    security_class=None,
                    region_id=0,
                    region_name=None,
                    constellation_id=0,
                    constellation_name=None,
                    x=None,
                    y=None,
                    z=None,
                ))
        
        return RouteResponse(
            route=route_systems,
            total_jumps=metadata.get("total_jumps", 0),
            estimated_time_seconds=metadata.get("estimated_time_seconds", 0),
            average_security=metadata.get("average_security", 0.0),
            route_length=metadata.get("route_length", len(route_ids)),
            segments=metadata.get("segments"),
            error=metadata.get("error"),
        )
        
    except ValueError as e:
        logger.error(f"Route calculation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error calculating route: {e}")
        raise HTTPException(status_code=500, detail="Failed to calculate route")

