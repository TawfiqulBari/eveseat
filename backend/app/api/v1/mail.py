"""
Mail API Endpoints

Handle in-game mail: reading, sending, organizing
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from typing import List, Optional
from datetime import datetime
import logging

from app.core.database import get_db
from app.models.user import User
from app.models.character import Character
from app.models.mail import Mail, MailLabel, MailingList
from app.models.eve_token import EveToken
from app.api.deps import get_current_user
from app.services.esi_client import esi_client, ESIError
from app.tasks.mail_sync import sync_character_mail, send_mail_task
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic models
class MailResponse(BaseModel):
    mail_id: int
    character_id: int
    from_id: int
    subject: str
    body: Optional[str] = None
    timestamp: datetime
    is_read: bool
    recipients: List[dict] = []
    labels: List[int] = []

    class Config:
        from_attributes = True


class MailLabelResponse(BaseModel):
    id: int
    label_id: int
    name: str
    color: str
    unread_count: int

    class Config:
        from_attributes = True


class MailingListResponse(BaseModel):
    id: int
    mailing_list_id: int
    name: str

    class Config:
        from_attributes = True


class SendMailRequest(BaseModel):
    character_id: int
    subject: str
    body: str
    recipients: List[dict]  # [{recipient_id, recipient_type}]
    approved_cost: Optional[int] = None


class UpdateMailLabelsRequest(BaseModel):
    mail_ids: List[int]
    labels: List[int]


@router.get("/", response_model=List[MailResponse])
async def list_mails(
    character_id: Optional[int] = None,
    label_id: Optional[int] = None,
    is_read: Optional[bool] = None,
    limit: int = Query(50, le=100),
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List mails for a character

    Query parameters:
    - character_id: Filter by character (defaults to user's first character)
    - label_id: Filter by label ID
    - is_read: Filter by read/unread status
    - limit: Max results (default 50, max 100)
    - offset: Pagination offset
    """
    # Get character
    if character_id:
        character = db.query(Character).filter(
            and_(
                Character.id == character_id,
                Character.user_id == current_user.id,
            )
        ).first()
    else:
        # Get user's first character
        character = db.query(Character).filter(
            Character.user_id == current_user.id
        ).first()

    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found"
        )

    # Build query
    query = db.query(Mail).filter(Mail.character_id == character.id)

    if label_id is not None:
        query = query.filter(Mail.labels.contains([label_id]))

    if is_read is not None:
        query = query.filter(Mail.is_read == is_read)

    # Order by timestamp descending (newest first)
    query = query.order_by(desc(Mail.timestamp))

    # Pagination
    mails = query.offset(offset).limit(limit).all()

    return mails


@router.get("/{mail_id}", response_model=MailResponse)
async def get_mail(
    mail_id: int,
    character_id: Optional[int] = None,
    mark_read: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a specific mail by ID

    If mark_read is True (default), mark the mail as read
    """
    # Get mail
    mail = db.query(Mail).filter(Mail.mail_id == mail_id).first()

    if not mail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mail not found"
        )

    # Verify ownership
    character = db.query(Character).filter(Character.id == mail.character_id).first()
    if not character or character.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this mail"
        )

    # Mark as read
    if mark_read and not mail.is_read:
        mail.is_read = True
        db.commit()

    return mail


@router.post("/send")
async def send_mail(
    request: SendMailRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Send an in-game mail

    Queues a Celery task to send the mail via ESI
    """
    # Verify character ownership
    character = db.query(Character).filter(
        and_(
            Character.id == request.character_id,
            Character.user_id == current_user.id,
        )
    ).first()

    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found"
        )

    # Queue send mail task
    task = send_mail_task.delay(
        character_id=character.character_id,
        subject=request.subject,
        body=request.body,
        recipients=request.recipients,
        approved_cost=request.approved_cost,
    )

    return {
        "success": True,
        "task_id": task.id,
        "message": "Mail queued for sending"
    }


@router.delete("/{mail_id}")
async def delete_mail(
    mail_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a mail"""
    # Get mail
    mail = db.query(Mail).filter(Mail.mail_id == mail_id).first()

    if not mail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mail not found"
        )

    # Verify ownership
    character = db.query(Character).filter(Character.id == mail.character_id).first()
    if not character or character.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this mail"
        )

    # Delete from database
    db.delete(mail)
    db.commit()

    # TODO: Also delete from EVE via ESI

    return {"success": True, "message": "Mail deleted"}


@router.put("/labels")
async def update_mail_labels(
    request: UpdateMailLabelsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update labels for multiple mails"""
    # Get mails
    mails = db.query(Mail).filter(Mail.mail_id.in_(request.mail_ids)).all()

    if not mails:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No mails found"
        )

    # Verify ownership
    for mail in mails:
        character = db.query(Character).filter(Character.id == mail.character_id).first()
        if not character or character.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to modify these mails"
            )

        # Update labels
        mail.labels = request.labels

    db.commit()

    return {"success": True, "updated_count": len(mails)}


@router.get("/labels/", response_model=List[MailLabelResponse])
async def list_mail_labels(
    character_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List mail labels for a character"""
    # Get character
    if character_id:
        character = db.query(Character).filter(
            and_(
                Character.id == character_id,
                Character.user_id == current_user.id,
            )
        ).first()
    else:
        character = db.query(Character).filter(
            Character.user_id == current_user.id
        ).first()

    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found"
        )

    labels = db.query(MailLabel).filter(
        MailLabel.character_id == character.id
    ).all()

    return labels


@router.get("/lists/", response_model=List[MailingListResponse])
async def list_mailing_lists(
    character_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List mailing lists for a character"""
    # Get character
    if character_id:
        character = db.query(Character).filter(
            and_(
                Character.id == character_id,
                Character.user_id == current_user.id,
            )
        ).first()
    else:
        character = db.query(Character).filter(
            Character.user_id == current_user.id
        ).first()

    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found"
        )

    mailing_lists = db.query(MailingList).filter(
        MailingList.character_id == character.id
    ).all()

    return mailing_lists


@router.post("/sync/{character_id}")
async def trigger_mail_sync(
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger manual mail sync for a character"""
    # Verify character ownership
    character = db.query(Character).filter(
        and_(
            Character.id == character_id,
            Character.user_id == current_user.id,
        )
    ).first()

    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found"
        )

    # Queue sync task
    task = sync_character_mail.delay(character.character_id)

    return {
        "success": True,
        "task_id": task.id,
        "message": "Mail sync queued"
    }
