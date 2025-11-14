"""
EVE Token model - stores encrypted OAuth tokens from EVE Online SSO
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class EveToken(Base):
    """
    EVE Token model - stores encrypted OAuth tokens for EVE Online ESI API access
    
    Tokens are encrypted using Fernet encryption before storage.
    """
    __tablename__ = "eve_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    character_id = Column(Integer, nullable=False, index=True)  # EVE character ID
    character_name = Column(String(255), nullable=False)
    
    # Encrypted tokens (stored as base64 strings)
    access_token_encrypted = Column(Text, nullable=False)
    refresh_token_encrypted = Column(Text, nullable=False)
    
    # Token metadata
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    token_type = Column(String(50), default="Bearer", nullable=False)
    scope = Column(Text, nullable=True)  # Space-separated list of scopes
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_refreshed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="eve_tokens")
    character = relationship("Character", foreign_keys=[character_id], primaryjoin="EveToken.character_id == Character.character_id", uselist=False)
    
    # Indexes for efficient queries
    __table_args__ = (
        Index("idx_eve_tokens_user_character", "user_id", "character_id"),
        Index("idx_eve_tokens_expires_at", "expires_at"),
    )
    
    def __repr__(self):
        return f"<EveToken(id={self.id}, character_id={self.character_id}, character_name='{self.character_name}')>"

