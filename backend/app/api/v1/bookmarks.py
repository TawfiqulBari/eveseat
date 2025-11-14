"""
Bookmarks API endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.character import Character
from app.models.bookmark import Bookmark, BookmarkFolder
from app.tasks.bookmark_sync import sync_character_bookmarks

router = APIRouter()


# Pydantic models
class BookmarkFolderResponse(BaseModel):
    id: int
    folder_id: int
    name: str

    class Config:
        from_attributes = True


class BookmarkResponse(BaseModel):
    id: int
    bookmark_id: int
    label: str
    notes: Optional[str]
    created: datetime
    location_id: int
    creator_id: Optional[int]
    folder_id: Optional[int]
    coordinates: Optional[dict]
    item_id: Optional[int]
    item_type_id: Optional[int]

    class Config:
        from_attributes = True


class BookmarkStatistics(BaseModel):
    total_bookmarks: int
    total_folders: int
    bookmarks_by_folder: dict


@router.get("/folders/", response_model=List[BookmarkFolderResponse])
async def list_bookmark_folders(
    character_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List bookmark folders
    """
    query = db.query(BookmarkFolder).join(Character).filter(
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
        query = query.filter(BookmarkFolder.character_id == character_id)

    folders = query.order_by(BookmarkFolder.name).all()
    return folders


@router.get("/", response_model=List[BookmarkResponse])
async def list_bookmarks(
    character_id: Optional[int] = Query(None),
    folder_id: Optional[int] = Query(None),
    location_id: Optional[int] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List bookmarks
    """
    query = db.query(Bookmark).join(Character).filter(
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
        query = query.filter(Bookmark.character_id == character_id)

    if folder_id:
        query = query.filter(Bookmark.folder_id == folder_id)

    if location_id:
        query = query.filter(Bookmark.location_id == location_id)

    bookmarks = query.order_by(desc(Bookmark.created)).limit(limit).offset(offset).all()
    return bookmarks


@router.get("/{bookmark_id}", response_model=BookmarkResponse)
async def get_bookmark(
    bookmark_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a specific bookmark
    """
    bookmark = db.query(Bookmark).join(Character).filter(
        and_(
            Bookmark.id == bookmark_id,
            Character.user_id == current_user.id,
        )
    ).first()

    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    return bookmark


@router.delete("/{bookmark_id}")
async def delete_bookmark(
    bookmark_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a bookmark
    """
    bookmark = db.query(Bookmark).join(Character).filter(
        and_(
            Bookmark.id == bookmark_id,
            Character.user_id == current_user.id,
        )
    ).first()

    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    db.delete(bookmark)
    db.commit()

    return {"status": "deleted", "bookmark_id": bookmark_id}


@router.get("/statistics/{character_id}", response_model=BookmarkStatistics)
async def get_bookmark_statistics(
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get bookmark statistics
    """
    char = db.query(Character).filter(
        and_(
            Character.id == character_id,
            Character.user_id == current_user.id,
        )
    ).first()

    if not char:
        raise HTTPException(status_code=403, detail="Character not found or unauthorized")

    bookmarks = db.query(Bookmark).filter(Bookmark.character_id == character_id).all()
    folders = db.query(BookmarkFolder).filter(BookmarkFolder.character_id == character_id).all()

    # Count bookmarks by folder
    bookmarks_by_folder = {}
    for bookmark in bookmarks:
        folder_name = "Uncategorized"
        if bookmark.folder_id:
            folder = next((f for f in folders if f.id == bookmark.folder_id), None)
            if folder:
                folder_name = folder.name

        if folder_name not in bookmarks_by_folder:
            bookmarks_by_folder[folder_name] = 0
        bookmarks_by_folder[folder_name] += 1

    return BookmarkStatistics(
        total_bookmarks=len(bookmarks),
        total_folders=len(folders),
        bookmarks_by_folder=bookmarks_by_folder,
    )


@router.post("/sync/{character_id}")
async def trigger_bookmark_sync(
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Trigger bookmark sync for a character
    """
    char = db.query(Character).filter(
        and_(
            Character.id == character_id,
            Character.user_id == current_user.id,
        )
    ).first()

    if not char:
        raise HTTPException(status_code=403, detail="Character not found or unauthorized")

    sync_character_bookmarks.delay(char.character_id)

    return {"status": "sync started", "character_id": character_id}
