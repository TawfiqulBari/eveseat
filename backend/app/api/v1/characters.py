"""
Character endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
import logging

from app.core.database import get_db
from app.models.character import Character
from app.models.user import User

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
