"""
API Dependencies

Common dependencies used across API endpoints
"""
from fastapi import Depends, HTTPException, Header, Query, status
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.core.database import get_db
from app.models.user import User
from app.models.character import Character
from app.models.eve_token import EveToken

logger = logging.getLogger(__name__)


async def get_current_user(
    character_id: Optional[int] = Query(None, description="Character ID for authentication"),
    x_character_id: Optional[str] = Header(None, alias="X-Character-ID"),
    db: Session = Depends(get_db),
) -> User:
    """
    Get current authenticated user based on character ID

    This dependency validates that:
    1. A character ID is provided (via query param or header)
    2. The character exists in the database
    3. The character has an active EVE token

    Args:
        character_id: Character ID from query parameter
        x_character_id: Character ID from X-Character-ID header
        db: Database session

    Returns:
        User object associated with the character

    Raises:
        HTTPException: If authentication fails
    """
    # Get character ID from query param or header
    char_id = character_id or (int(x_character_id) if x_character_id else None)

    if not char_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: character_id must be provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Find character
    character = db.query(Character).filter(
        Character.character_id == char_id
    ).first()

    if not character:
        logger.warning(f"Authentication failed: character {char_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found. Please authenticate via EVE SSO.",
        )

    # Verify character has an active token
    eve_token = db.query(EveToken).filter(
        EveToken.character_id == char_id
    ).first()

    if not eve_token:
        logger.warning(f"Authentication failed: no token found for character {char_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No valid authentication token found. Please re-authenticate.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user
    user = db.query(User).filter(User.id == character.user_id).first()

    if not user:
        logger.error(f"Data integrity error: user not found for character {char_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User account error. Please contact support.",
        )

    if not user.is_active:
        logger.warning(f"Authentication failed: user {user.id} is not active")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive.",
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current active user (alias for get_current_user)

    This is an additional dependency that can be used when you want
    to be explicit about requiring an active user.

    Args:
        current_user: User from get_current_user dependency

    Returns:
        Active user object
    """
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current user and verify they have admin privileges

    Args:
        current_user: User from get_current_user dependency

    Returns:
        Admin user object

    Raises:
        HTTPException: If user is not an admin
    """
    if not current_user.is_admin:
        logger.warning(f"Authorization failed: user {current_user.id} is not an admin")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required.",
        )

    return current_user
