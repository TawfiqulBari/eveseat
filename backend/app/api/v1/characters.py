"""
Character endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import logging

from app.core.database import get_db
from app.models.character import Character
from app.models.user import User
from app.models.market import MarketOrder
from app.tasks.character_sync import (
    sync_character_assets,
    sync_character_market_orders,
    sync_character_details,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class CharacterResponse(BaseModel):
    """Character response model"""
    id: int
    character_id: int
    character_name: str
    corporation_id: Optional[int]
    corporation_name: Optional[str]
    alliance_id: Optional[int]
    alliance_name: Optional[str]
    security_status: Optional[str]
    birthday: Optional[str]
    gender: Optional[str]
    race_id: Optional[int]
    bloodline_id: Optional[int]
    ancestry_id: Optional[int]
    last_synced_at: Optional[str]
    
    class Config:
        from_attributes = True


@router.get("/", response_model=List[CharacterResponse])
async def list_characters(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    corporation_id: Optional[int] = Query(None, description="Filter by corporation ID"),
    alliance_id: Optional[int] = Query(None, description="Filter by alliance ID"),
    db: Session = Depends(get_db),
):
    """
    List characters with optional filters
    
    Args:
        user_id: Filter by user ID
        corporation_id: Filter by corporation ID
        alliance_id: Filter by alliance ID
        db: Database session
    """
    try:
        query = db.query(Character)
        
        if user_id:
            query = query.filter(Character.user_id == user_id)
        
        if corporation_id:
            query = query.filter(Character.corporation_id == corporation_id)
        
        if alliance_id:
            query = query.filter(Character.alliance_id == alliance_id)
        
        characters = query.all()
        
        return characters
        
    except Exception as e:
        logger.error(f"Error listing characters: {e}")
        raise HTTPException(status_code=500, detail="Failed to list characters")


@router.get("/{character_id}", response_model=CharacterResponse)
async def get_character(
    character_id: int,
    db: Session = Depends(get_db),
):
    """
    Get character details
    
    Args:
        character_id: EVE character ID
        db: Database session
    """
    try:
        character = db.query(Character).filter(
            Character.character_id == character_id
        ).first()
        
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")
        
        return character
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting character {character_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get character")


@router.get("/{character_id}/assets")
async def get_character_assets(
    character_id: int,
    db: Session = Depends(get_db),
):
    """
    Get character assets
    
    Args:
        character_id: EVE character ID
        db: Database session
    """
    try:
        character = db.query(Character).filter(
            Character.character_id == character_id
        ).first()
        
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")
        
        # Get assets from character_data
        assets = []
        if character.character_data and "assets" in character.character_data:
            assets = character.character_data["assets"]
        
        return {
            "character_id": character_id,
            "assets": assets,
            "count": len(assets),
            "synced_at": character.character_data.get("assets_synced_at") if character.character_data else None,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting character assets for {character_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get character assets")


@router.get("/{character_id}/market-orders")
async def get_character_market_orders(
    character_id: int,
    is_buy_order: Optional[bool] = Query(None, description="Filter by order type (true=buy, false=sell)"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """
    Get character's personal market orders
    
    Args:
        character_id: EVE character ID
        is_buy_order: Filter by order type
        is_active: Filter by active status
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session
    """
    try:
        query = db.query(MarketOrder).filter(
            MarketOrder.character_id == character_id
        )
        
        if is_buy_order is not None:
            query = query.filter(MarketOrder.is_buy_order == is_buy_order)
        
        if is_active is not None:
            query = query.filter(MarketOrder.is_active == is_active)
        
        orders = query.order_by(MarketOrder.issued.desc()).offset(skip).limit(limit).all()
        total = query.count()
        
        # Convert to response format
        order_responses = []
        for order in orders:
            order_dict = {
                "id": order.id,
                "order_id": order.order_id,
                "character_id": order.character_id,
                "type_id": order.type_id,
                "type_name": order.type_name,
                "type_icon_url": f"https://images.evetech.net/types/{order.type_id}/icon" if order.type_id else None,
                "is_buy_order": order.is_buy_order,
                "location_id": order.location_id,
                "location_name": order.location_name,
                "region_id": order.region_id,
                "region_name": order.region_name,
                "system_id": order.system_id,
                "system_name": order.system_name,
                "price": order.price,
                "volume_total": order.volume_total,
                "volume_remain": order.volume_remain,
                "min_volume": order.min_volume,
                "duration": order.duration,
                "issued": order.issued.isoformat() if order.issued else None,
                "expires": order.expires.isoformat() if order.expires else None,
                "is_active": order.is_active,
                "range_type": order.range_type,
                "range_value": order.range_value,
            }
            order_responses.append(order_dict)
        
        return {
            "items": order_responses,
            "total": total,
            "skip": skip,
            "limit": limit,
        }
        
    except Exception as e:
        logger.error(f"Error getting character market orders for {character_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get character market orders")


@router.get("/{character_id}/details")
async def get_character_details(
    character_id: int,
    db: Session = Depends(get_db),
):
    """
    Get detailed character information
    
    Args:
        character_id: EVE character ID
        db: Database session
    """
    try:
        character = db.query(Character).filter(
            Character.character_id == character_id
        ).first()
        
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")
        
        # Get details from character_data
        details = character.character_data or {}
        
        return {
            "character_id": character_id,
            "character_name": character.character_name,
            "corporation_id": character.corporation_id,
            "corporation_name": character.corporation_name,
            "alliance_id": character.alliance_id,
            "alliance_name": character.alliance_name,
            "security_status": character.security_status,
            "details": details,
            "synced_at": details.get("details_synced_at") if details else None,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting character details for {character_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get character details")


@router.post("/{character_id}/sync/assets")
async def trigger_sync_assets(
    character_id: int,
    db: Session = Depends(get_db),
):
    """
    Trigger sync of character assets
    
    Args:
        character_id: EVE character ID
        db: Database session
    """
    try:
        character = db.query(Character).filter(
            Character.character_id == character_id
        ).first()
        
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")
        
        task = sync_character_assets.delay(character_id)
        return {
            "message": "Character assets sync queued",
            "task_id": task.id,
            "character_id": character_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error queuing character assets sync: {e}")
        raise HTTPException(status_code=500, detail="Failed to queue character assets sync")


@router.post("/{character_id}/sync/market-orders")
async def trigger_sync_market_orders(
    character_id: int,
    db: Session = Depends(get_db),
):
    """
    Trigger sync of character market orders
    
    Args:
        character_id: EVE character ID
        db: Database session
    """
    try:
        character = db.query(Character).filter(
            Character.character_id == character_id
        ).first()
        
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")
        
        task = sync_character_market_orders.delay(character_id)
        return {
            "message": "Character market orders sync queued",
            "task_id": task.id,
            "character_id": character_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error queuing character market orders sync: {e}")
        raise HTTPException(status_code=500, detail="Failed to queue character market orders sync")


@router.post("/{character_id}/sync/details")
async def trigger_sync_details(
    character_id: int,
    db: Session = Depends(get_db),
):
    """
    Trigger sync of character details
    
    Args:
        character_id: EVE character ID
        db: Database session
    """
    try:
        character = db.query(Character).filter(
            Character.character_id == character_id
        ).first()
        
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")
        
        task = sync_character_details.delay(character_id)
        return {
            "message": "Character details sync queued",
            "task_id": task.id,
            "character_id": character_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error queuing character details sync: {e}")
        raise HTTPException(status_code=500, detail="Failed to queue character details sync")
