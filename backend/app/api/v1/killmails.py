"""
Killmail endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from typing import Optional, List
from datetime import datetime, timedelta
from pydantic import BaseModel
import json
import logging

from app.core.database import get_db
from app.models.killmail import Killmail
from app.models.character import Character

logger = logging.getLogger(__name__)

router = APIRouter()


class KillmailResponse(BaseModel):
    """Killmail response model"""
    id: int
    killmail_id: int
    time: datetime
    system_id: Optional[int]
    system_name: Optional[str]
    victim_character_id: Optional[int]
    victim_character_name: Optional[str]
    victim_corporation_id: Optional[int]
    victim_corporation_name: Optional[str]
    victim_alliance_id: Optional[int]
    victim_alliance_name: Optional[str]
    victim_ship_type_id: Optional[int]
    victim_ship_type_name: Optional[str]
    value: Optional[int]
    attackers_count: Optional[int]
    zkill_url: Optional[str]
    
    class Config:
        from_attributes = True


class KillmailDetailResponse(KillmailResponse):
    """Detailed killmail response with full data"""
    killmail_data: dict
    
    class Config:
        from_attributes = True


@router.get("/")
async def list_killmails(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of records to return"),
    character_id: Optional[int] = Query(None, description="Filter by victim character ID"),
    corporation_id: Optional[int] = Query(None, description="Filter by victim corporation ID"),
    alliance_id: Optional[int] = Query(None, description="Filter by victim alliance ID"),
    system_id: Optional[int] = Query(None, description="Filter by system ID"),
    ship_type_id: Optional[int] = Query(None, description="Filter by ship type ID"),
    min_value: Optional[int] = Query(None, ge=0, description="Minimum killmail value"),
    max_value: Optional[int] = Query(None, ge=0, description="Maximum killmail value"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    db: Session = Depends(get_db),
):
    """
    List killmails with filters
    
    Supports filtering by:
    - Character, corporation, alliance
    - System
    - Ship type
    - Value range
    - Date range
    """
    try:
        query = db.query(Killmail)
        
        # Apply filters
        if character_id:
            query = query.filter(Killmail.victim_character_id == character_id)
        
        if corporation_id:
            query = query.filter(Killmail.victim_corporation_id == corporation_id)
        
        if alliance_id:
            query = query.filter(Killmail.victim_alliance_id == alliance_id)
        
        if system_id:
            query = query.filter(Killmail.system_id == system_id)
        
        if ship_type_id:
            query = query.filter(Killmail.victim_ship_type_id == ship_type_id)
        
        if min_value is not None:
            query = query.filter(Killmail.value >= min_value)
        
        if max_value is not None:
            query = query.filter(Killmail.value <= max_value)
        
        if start_date:
            query = query.filter(Killmail.time >= start_date)
        
        if end_date:
            query = query.filter(Killmail.time <= end_date)
        
        # Order by time descending (most recent first)
        query = query.order_by(desc(Killmail.time))
        
        # Apply pagination
        killmails = query.offset(skip).limit(limit).all()
        
        # Get total count for pagination metadata
        total = query.count()
        
        return {
            "items": [KillmailResponse.model_validate(km) for km in killmails],
            "total": total,
            "skip": skip,
            "limit": limit,
        }
        
    except Exception as e:
        logger.error(f"Error listing killmails: {e}")
        raise HTTPException(status_code=500, detail="Failed to list killmails")


@router.get("/{killmail_id}", response_model=KillmailDetailResponse)
async def get_killmail(
    killmail_id: int,
    db: Session = Depends(get_db),
):
    """
    Get killmail details by ID
    
    Returns full killmail data including attackers, items, etc.
    """
    try:
        killmail = db.query(Killmail).filter(
            Killmail.killmail_id == killmail_id
        ).first()
        
        if not killmail:
            raise HTTPException(status_code=404, detail="Killmail not found")
        
        return killmail
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting killmail {killmail_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get killmail")


@router.websocket("/feed")
async def killmail_feed(websocket: WebSocket):
    """
    WebSocket endpoint for real-time killmail feed
    
    Clients can subscribe to receive killmail updates as they are synced
    """
    await websocket.accept()
    
    try:
        # Subscribe to Redis pub/sub for killmail updates
        import redis
        from app.core.config import settings
        
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        pubsub = redis_client.pubsub()
        pubsub.subscribe("killmails:new")
        
        logger.info("Client connected to killmail feed")
        
        # Send initial message
        await websocket.send_json({
            "type": "connected",
            "message": "Subscribed to killmail feed",
        })
        
        # Listen for killmail updates
        for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    killmail_data = json.loads(message["data"])
                    await websocket.send_json({
                        "type": "killmail",
                        "data": killmail_data,
                    })
                except json.JSONDecodeError:
                    logger.warning("Invalid JSON in killmail feed message")
                except Exception as e:
                    logger.error(f"Error sending killmail update: {e}")
            
    except WebSocketDisconnect:
        logger.info("Client disconnected from killmail feed")
        pubsub.unsubscribe("killmails:new")
        pubsub.close()
    except Exception as e:
        logger.error(f"Error in killmail feed WebSocket: {e}")
        try:
            await websocket.close()
        except:
            pass


@router.get("/stats/summary")
async def get_killmail_stats(
    character_id: Optional[int] = Query(None),
    corporation_id: Optional[int] = Query(None),
    alliance_id: Optional[int] = Query(None),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db),
):
    """
    Get killmail statistics summary
    
    Returns aggregated statistics for the specified filters
    """
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        query = db.query(Killmail).filter(
            and_(
                Killmail.time >= start_date,
                Killmail.time <= end_date,
            )
        )
        
        # Apply filters
        if character_id:
            query = query.filter(Killmail.victim_character_id == character_id)
        
        if corporation_id:
            query = query.filter(Killmail.victim_corporation_id == corporation_id)
        
        if alliance_id:
            query = query.filter(Killmail.victim_alliance_id == alliance_id)
        
        killmails = query.all()
        
        # Calculate statistics
        total_kills = len(killmails)
        total_value = sum(km.value or 0 for km in killmails)
        avg_value = total_value / total_kills if total_kills > 0 else 0
        
        # Group by system
        system_counts = {}
        for km in killmails:
            if km.system_id:
                system_counts[km.system_id] = system_counts.get(km.system_id, 0) + 1
        
        # Group by ship type
        ship_type_counts = {}
        for km in killmails:
            if km.victim_ship_type_id:
                ship_type_counts[km.victim_ship_type_id] = ship_type_counts.get(km.victim_ship_type_id, 0) + 1
        
        return {
            "period_days": days,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "total_kills": total_kills,
            "total_value": total_value,
            "average_value": avg_value,
            "top_systems": sorted(
                [{"system_id": sid, "count": count} for sid, count in system_counts.items()],
                key=lambda x: x["count"],
                reverse=True
            )[:10],
            "top_ship_types": sorted(
                [{"ship_type_id": stid, "count": count} for stid, count in ship_type_counts.items()],
                key=lambda x: x["count"],
                reverse=True
            )[:10],
        }
        
    except Exception as e:
        logger.error(f"Error getting killmail stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get killmail statistics")
