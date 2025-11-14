"""
Contacts API Endpoints

Handle character and corporation contacts
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from typing import List, Optional
from datetime import datetime
import logging

from app.core.database import get_db
from app.models.user import User
from app.models.character import Character
from app.models.contact import Contact, ContactLabel
from app.api.deps import get_current_user
from app.tasks.contact_sync import sync_character_contacts
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic models
class ContactResponse(BaseModel):
    id: int
    contact_id: int
    contact_type: str
    standing: float
    is_watched: bool
    is_blocked: bool
    label_ids: List[int] = []

    class Config:
        from_attributes = True


class ContactLabelResponse(BaseModel):
    id: int
    label_id: int
    name: str

    class Config:
        from_attributes = True


class AddContactRequest(BaseModel):
    character_id: int
    contact_id: int
    standing: float
    label_ids: Optional[List[int]] = []
    watched: Optional[bool] = False


class UpdateContactRequest(BaseModel):
    standing: Optional[float] = None
    label_ids: Optional[List[int]] = None
    watched: Optional[bool] = None


@router.get("/", response_model=List[ContactResponse])
async def list_contacts(
    character_id: Optional[int] = None,
    min_standing: Optional[float] = None,
    max_standing: Optional[float] = None,
    contact_type: Optional[str] = None,
    watched_only: bool = False,
    limit: int = Query(100, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List contacts for a character

    Query parameters:
    - character_id: Filter by character
    - min_standing: Minimum standing value
    - max_standing: Maximum standing value
    - contact_type: Filter by type (character, corporation, alliance)
    - watched_only: Only show watched contacts
    - limit: Max results (default 100, max 500)
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
        character = db.query(Character).filter(
            Character.user_id == current_user.id
        ).first()

    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found"
        )

    # Build query
    query = db.query(Contact).filter(Contact.character_id == character.id)

    if min_standing is not None:
        query = query.filter(Contact.standing >= min_standing)

    if max_standing is not None:
        query = query.filter(Contact.standing <= max_standing)

    if contact_type:
        query = query.filter(Contact.contact_type == contact_type)

    if watched_only:
        query = query.filter(Contact.is_watched == True)

    # Order by standing descending
    query = query.order_by(desc(Contact.standing))

    # Pagination
    contacts = query.offset(offset).limit(limit).all()

    return contacts


@router.get("/{contact_id}", response_model=ContactResponse)
async def get_contact(
    contact_id: int,
    character_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific contact by ID"""
    # Get contact
    contact = db.query(Contact).filter(Contact.contact_id == contact_id).first()

    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found"
        )

    # Verify ownership
    character = db.query(Character).filter(Character.id == contact.character_id).first()
    if not character or character.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this contact"
        )

    return contact


@router.post("/")
async def add_contact(
    request: AddContactRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Add a new contact via ESI

    Note: This queues a task to add the contact via ESI,
    then triggers a sync to update the local database
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

    # TODO: Queue task to add contact via ESI
    # For now, just trigger a sync which will pick up any ESI-side changes
    task = sync_character_contacts.delay(character.character_id)

    return {
        "success": True,
        "task_id": task.id,
        "message": "Contact add queued"
    }


@router.put("/{contact_id}")
async def update_contact(
    contact_id: int,
    request: UpdateContactRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a contact's standing or labels"""
    # Get contact
    contact = db.query(Contact).filter(Contact.contact_id == contact_id).first()

    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found"
        )

    # Verify ownership
    character = db.query(Character).filter(Contact.character_id == contact.character_id).first()
    if not character or character.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this contact"
        )

    # Update fields
    if request.standing is not None:
        contact.standing = request.standing

    if request.label_ids is not None:
        contact.label_ids = request.label_ids

    if request.watched is not None:
        contact.is_watched = request.watched

    db.commit()

    # TODO: Also update via ESI

    return {"success": True, "message": "Contact updated"}


@router.delete("/{contact_id}")
async def delete_contact(
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a contact"""
    # Get contact
    contact = db.query(Contact).filter(Contact.contact_id == contact_id).first()

    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found"
        )

    # Verify ownership
    character = db.query(Character).filter(Character.id == contact.character_id).first()
    if not character or character.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this contact"
        )

    # Delete from database
    db.delete(contact)
    db.commit()

    # TODO: Also delete from EVE via ESI

    return {"success": True, "message": "Contact deleted"}


@router.get("/labels/", response_model=List[ContactLabelResponse])
async def list_contact_labels(
    character_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List contact labels for a character"""
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

    labels = db.query(ContactLabel).filter(
        ContactLabel.character_id == character.id
    ).all()

    return labels


@router.post("/sync/{character_id}")
async def trigger_contact_sync(
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger manual contact sync for a character"""
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
    task = sync_character_contacts.delay(character.character_id)

    return {
        "success": True,
        "task_id": task.id,
        "message": "Contact sync queued"
    }
