"""
Industry API endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc
from pydantic import BaseModel
from datetime import datetime, timedelta

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.character import Character
from app.models.industry import IndustryJob, IndustryFacility, IndustryActivity
from app.tasks.industry_sync import sync_character_industry

router = APIRouter()


# Pydantic models
class IndustryJobResponse(BaseModel):
    id: int
    job_id: int
    installer_id: int
    facility_id: int
    location_id: int
    activity_id: int
    blueprint_type_id: int
    product_type_id: Optional[int]
    runs: int
    cost: Optional[float]
    status: str
    start_date: datetime
    end_date: datetime
    completed_date: Optional[datetime]
    successful_runs: Optional[int]

    class Config:
        from_attributes = True


class IndustryFacilityResponse(BaseModel):
    id: int
    facility_id: int
    owner_id: int
    solar_system_id: int
    type_id: Optional[int]
    name: Optional[str]
    bonuses: Optional[dict]
    tax: Optional[float]

    class Config:
        from_attributes = True


class IndustryStatistics(BaseModel):
    total_jobs: int
    active_jobs: int
    completed_jobs: int
    total_runs: int
    total_cost: float
    by_activity: dict


@router.get("/jobs/", response_model=List[IndustryJobResponse])
async def list_industry_jobs(
    character_id: Optional[int] = Query(None),
    activity_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List industry jobs
    """
    query = db.query(IndustryJob).join(Character).filter(
        Character.user_id == current_user.id
    )

    if character_id:
        # Verify character belongs to user
        char = db.query(Character).filter(
            and_(
                Character.id == character_id,
                Character.user_id == current_user.id,
            )
        ).first()
        if not char:
            raise HTTPException(status_code=403, detail="Character not found or unauthorized")
        query = query.filter(IndustryJob.character_id == character_id)

    if activity_id:
        query = query.filter(IndustryJob.activity_id == activity_id)

    if status:
        query = query.filter(IndustryJob.status == status)

    jobs = query.order_by(desc(IndustryJob.start_date)).limit(limit).offset(offset).all()
    return jobs


@router.get("/jobs/{job_id}", response_model=IndustryJobResponse)
async def get_industry_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a specific industry job
    """
    job = db.query(IndustryJob).join(Character).filter(
        and_(
            IndustryJob.job_id == job_id,
            Character.user_id == current_user.id,
        )
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="Industry job not found")

    return job


@router.get("/facilities/", response_model=List[IndustryFacilityResponse])
async def list_facilities(
    character_id: Optional[int] = Query(None),
    solar_system_id: Optional[int] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List industry facilities
    """
    query = db.query(IndustryFacility).join(Character).filter(
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
        query = query.filter(IndustryFacility.character_id == character_id)

    if solar_system_id:
        query = query.filter(IndustryFacility.solar_system_id == solar_system_id)

    facilities = query.order_by(IndustryFacility.name).limit(limit).offset(offset).all()
    return facilities


@router.get("/statistics/{character_id}", response_model=IndustryStatistics)
async def get_industry_statistics(
    character_id: int,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get industry statistics for a character
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

    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # Get jobs in date range
    jobs = db.query(IndustryJob).filter(
        and_(
            IndustryJob.character_id == character_id,
            IndustryJob.start_date >= start_date,
        )
    ).all()

    # Calculate statistics
    total_jobs = len(jobs)
    active_jobs = sum(1 for j in jobs if j.status == "active")
    completed_jobs = sum(1 for j in jobs if j.status in ["delivered", "ready"])
    total_runs = sum(j.runs for j in jobs)
    total_cost = sum(float(j.cost) if j.cost else 0 for j in jobs)

    # By activity
    by_activity = {}
    for job in jobs:
        activity_name = get_activity_name(job.activity_id)
        if activity_name not in by_activity:
            by_activity[activity_name] = {
                "jobs": 0,
                "runs": 0,
                "cost": 0,
            }
        by_activity[activity_name]["jobs"] += 1
        by_activity[activity_name]["runs"] += job.runs
        by_activity[activity_name]["cost"] += float(job.cost) if job.cost else 0

    return IndustryStatistics(
        total_jobs=total_jobs,
        active_jobs=active_jobs,
        completed_jobs=completed_jobs,
        total_runs=total_runs,
        total_cost=total_cost,
        by_activity=by_activity,
    )


@router.post("/sync/{character_id}")
async def trigger_industry_sync(
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Trigger industry sync for a character
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
    sync_character_industry.delay(char.character_id)

    return {"status": "sync started", "character_id": character_id}


def get_activity_name(activity_id: int) -> str:
    """Map activity ID to name"""
    activity_map = {
        1: "Manufacturing",
        3: "TE Research",
        4: "ME Research",
        5: "Copying",
        8: "Invention",
        9: "Reverse Engineering",
    }
    return activity_map.get(activity_id, f"Activity {activity_id}")
