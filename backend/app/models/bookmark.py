"""
Bookmark models for location bookmarks
"""
from sqlalchemy import Column, Integer, BigInteger, String, DateTime, ForeignKey, Float, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

from app.core.database import Base


class Bookmark(Base):
    """Character bookmark model"""
    __tablename__ = "bookmarks"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False, index=True)
    bookmark_id = Column(BigInteger, unique=True, nullable=False, index=True)

    # Bookmark details
    label = Column(String(255), nullable=False)
    notes = Column(Text)
    created = Column(DateTime(timezone=True), nullable=False)

    # Location
    location_id = Column(BigInteger, nullable=False, index=True)
    creator_id = Column(BigInteger)

    # Folder
    folder_id = Column(Integer, ForeignKey("bookmark_folders.id"), index=True)

    # Coordinates (if applicable)
    # Format: {"x": 123.45, "y": 678.90, "z": -111.22}
    coordinates = Column(JSONB)

    # Item (if bookmark is for a specific item)
    item_id = Column(BigInteger)
    item_type_id = Column(Integer)

    # Metadata
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    character = relationship("Character", back_populates="bookmarks")
    folder = relationship("BookmarkFolder", back_populates="bookmarks")


class BookmarkFolder(Base):
    """Bookmark folder model"""
    __tablename__ = "bookmark_folders"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False, index=True)
    folder_id = Column(BigInteger, unique=True, nullable=False, index=True)

    # Folder details
    name = Column(String(255), nullable=False)

    # Metadata
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    character = relationship("Character", back_populates="bookmark_folders")
    bookmarks = relationship("Bookmark", back_populates="folder", cascade="all, delete-orphan")
