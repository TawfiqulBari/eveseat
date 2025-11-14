"""
Skills API endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.character import Character
from app.models.skill import Skill, SkillQueue, SkillPlan
from app.tasks.skill_sync import sync_character_skills

router = APIRouter()


# Pydantic models
class SkillResponse(BaseModel):
    id: int
    skill_id: int
    active_skill_level: int
    trained_skill_level: int
    skillpoints_in_skill: int

    class Config:
        from_attributes = True


class SkillQueueResponse(BaseModel):
    id: int
    skill_id: int
    queue_position: int
    finished_level: int
    start_date: Optional[datetime]
    finish_date: Optional[datetime]
    training_start_sp: Optional[int]
    level_start_sp: Optional[int]
    level_end_sp: Optional[int]

    class Config:
        from_attributes = True


class SkillStatistics(BaseModel):
    total_skills: int
    total_sp: int
    skills_at_level_5: int
    skills_in_training: int
    queue_time_remaining: Optional[float]  # in hours


@router.get("/", response_model=List[SkillResponse])
async def list_skills(
    character_id: Optional[int] = Query(None),
    min_level: Optional[int] = Query(None, ge=0, le=5),
    limit: int = Query(1000, le=10000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List character skills
    """
    query = db.query(Skill).join(Character).filter(
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
        query = query.filter(Skill.character_id == character_id)

    if min_level is not None:
        query = query.filter(Skill.trained_skill_level >= min_level)

    skills = query.order_by(desc(Skill.skillpoints_in_skill)).limit(limit).offset(offset).all()
    return skills


@router.get("/queue/", response_model=List[SkillQueueResponse])
async def get_skill_queue(
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get character skill queue
    """
    char = db.query(Character).filter(
        and_(
            Character.id == character_id,
            Character.user_id == current_user.id,
        )
    ).first()

    if not char:
        raise HTTPException(status_code=403, detail="Character not found or unauthorized")

    queue = db.query(SkillQueue).filter(
        SkillQueue.character_id == character_id
    ).order_by(SkillQueue.queue_position).all()

    return queue


@router.get("/statistics/{character_id}", response_model=SkillStatistics)
async def get_skill_statistics(
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get skill statistics for a character
    """
    char = db.query(Character).filter(
        and_(
            Character.id == character_id,
            Character.user_id == current_user.id,
        )
    ).first()

    if not char:
        raise HTTPException(status_code=403, detail="Character not found or unauthorized")

    skills = db.query(Skill).filter(Skill.character_id == character_id).all()

    total_skills = len(skills)
    total_sp = sum(skill.skillpoints_in_skill for skill in skills)
    skills_at_level_5 = sum(1 for skill in skills if skill.trained_skill_level == 5)

    # Get queue info
    queue = db.query(SkillQueue).filter(
        SkillQueue.character_id == character_id
    ).order_by(SkillQueue.queue_position).all()

    skills_in_training = len(queue)
    queue_time_remaining = None

    if queue and queue[-1].finish_date:
        time_remaining = (queue[-1].finish_date - datetime.utcnow()).total_seconds()
        queue_time_remaining = time_remaining / 3600  # Convert to hours

    return SkillStatistics(
        total_skills=total_skills,
        total_sp=total_sp,
        skills_at_level_5=skills_at_level_5,
        skills_in_training=skills_in_training,
        queue_time_remaining=queue_time_remaining,
    )


@router.post("/sync/{character_id}")
async def trigger_skill_sync(
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Trigger skill sync for a character
    """
    char = db.query(Character).filter(
        and_(
            Character.id == character_id,
            Character.user_id == current_user.id,
        )
    ).first()

    if not char:
        raise HTTPException(status_code=403, detail="Character not found or unauthorized")

    sync_character_skills.delay(char.character_id)

    return {"status": "sync started", "character_id": character_id}
