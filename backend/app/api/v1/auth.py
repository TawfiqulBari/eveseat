"""
Authentication endpoints for EVE Online SSO
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
import logging

from app.core.database import get_db
from app.core.config import settings
from app.core.security import limiter
from app.services.esi_client import esi_client, ESIError, ESITokenError
from app.core.encryption import encryption
from app.models.user import User
from app.models.eve_token import EveToken
from app.models.character import Character

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/login")
@limiter.limit("10/minute")
async def login(request: Request, state: Optional[str] = None):
    """
    Initiate EVE SSO login with OAuth 2.0 + PKCE
    
    Args:
        state: Optional state parameter for CSRF protection
        
    Returns:
        Redirect to EVE SSO authorization page
    """
    try:
        auth_url, code_verifier = esi_client.get_authorization_url(state=state)
        return RedirectResponse(url=auth_url)
    except Exception as e:
        logger.error(f"Login initiation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to initiate login")


@router.get("/callback")
@limiter.limit("20/minute")
async def callback(
    request: Request,
    code: str = Query(..., description="Authorization code from EVE SSO"),
    state: Optional[str] = Query(None, description="State parameter for CSRF protection"),
    db: Session = Depends(get_db),
):
    """
    Handle EVE SSO OAuth callback
    
    Exchanges authorization code for access token, creates/updates user and character,
    and stores encrypted tokens.
    
    Args:
        code: Authorization code from EVE SSO
        state: State parameter (should match the one used in login)
        db: Database session
        
    Returns:
        Redirect to frontend with success message or error
    """
    try:
        # Retrieve PKCE code verifier
        code_verifier = esi_client.get_pkce_verifier(state or "")
        if not code_verifier:
            logger.error(f"PKCE verifier not found for state: {state}")
            return RedirectResponse(
                url=f"{settings.ALLOWED_ORIGINS}/auth/callback?error=invalid_state"
            )
        
        # Exchange code for token
        token_response = await esi_client.exchange_code_for_token(
            code=code,
            code_verifier=code_verifier,
            state=state,
        )
        
        access_token = token_response.get("access_token")
        refresh_token = token_response.get("refresh_token")
        expires_in = token_response.get("expires_in", 1200)  # Default 20 minutes
        token_type = token_response.get("token_type", "Bearer")
        scope = token_response.get("scope", "")
        
        # Verify token and get character info
        character_info = await esi_client.verify_token(access_token)
        character_id = character_info.get("CharacterID")
        character_name = character_info.get("CharacterName")
        
        if not character_id or not character_name:
            raise ESITokenError("Invalid token response - missing character information")
        
        # Get full character details from ESI
        char_details = await esi_client.get_character_info(character_id, access_token)
        
        # Calculate expiration time
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        
        # Encrypt tokens before storage
        encrypted_access = encryption.encrypt(access_token)
        encrypted_refresh = encryption.encrypt(refresh_token)
        
        # Find or create user
        # For now, we'll create a user based on character name
        # In a real app, you might want to use EVE account email or other identifier
        user = db.query(User).filter(
            User.email == f"{character_id}@eveonline.local"  # Placeholder email
        ).first()
        
        if not user:
            user = User(
                email=f"{character_id}@eveonline.local",
                username=character_name,
                is_active=True,
            )
            db.add(user)
            db.flush()
        
        # Find or create character
        character = db.query(Character).filter(
            Character.character_id == character_id
        ).first()
        
        if not character:
            character = Character(
                user_id=user.id,
                character_id=character_id,
                character_name=character_name,
                corporation_id=char_details.get("corporation_id"),
                corporation_name=char_details.get("corporation_name"),
                alliance_id=char_details.get("alliance_id"),
                alliance_name=char_details.get("alliance_name"),
                security_status=str(char_details.get("security_status", "")),
                birthday=datetime.fromisoformat(char_details.get("birthday", "").replace("Z", "+00:00")) if char_details.get("birthday") else None,
                gender=char_details.get("gender"),
                race_id=char_details.get("race_id"),
                bloodline_id=char_details.get("bloodline_id"),
                ancestry_id=char_details.get("ancestry_id"),
                character_data=char_details,
                last_synced_at=datetime.utcnow(),
            )
            db.add(character)
            db.flush()
        else:
            # Update character info
            character.character_name = character_name
            character.corporation_id = char_details.get("corporation_id")
            character.corporation_name = char_details.get("corporation_name")
            character.alliance_id = char_details.get("alliance_id")
            character.alliance_name = char_details.get("alliance_name")
            character.security_status = str(char_details.get("security_status", ""))
            character.character_data = char_details
            character.last_synced_at = datetime.utcnow()
        
        # Find or create/update token
        eve_token = db.query(EveToken).filter(
            EveToken.user_id == user.id,
            EveToken.character_id == character_id
        ).first()
        
        if not eve_token:
            eve_token = EveToken(
                user_id=user.id,
                character_id=character_id,
                character_name=character_name,
                access_token_encrypted=encrypted_access,
                refresh_token_encrypted=encrypted_refresh,
                expires_at=expires_at,
                token_type=token_type,
                scope=scope,
            )
            db.add(eve_token)
        else:
            # Update existing token
            eve_token.access_token_encrypted = encrypted_access
            eve_token.refresh_token_encrypted = encrypted_refresh
            eve_token.expires_at = expires_at
            eve_token.token_type = token_type
            eve_token.scope = scope
            eve_token.last_refreshed_at = datetime.utcnow()
        
        db.commit()
        
        # Redirect to frontend with success
        return RedirectResponse(
            url=f"{settings.ALLOWED_ORIGINS}/auth/callback?success=true&character_id={character_id}"
        )
        
    except ESITokenError as e:
        logger.error(f"Token error in callback: {e}")
        return RedirectResponse(
            url=f"{settings.ALLOWED_ORIGINS}/auth/callback?error=token_error"
        )
    except Exception as e:
        logger.error(f"Callback error: {e}")
        db.rollback()
        return RedirectResponse(
            url=f"{settings.ALLOWED_ORIGINS}/auth/callback?error=server_error"
        )


@router.post("/logout")
async def logout(
    character_id: int = Query(..., description="Character ID to logout"),
    db: Session = Depends(get_db),
):
    """
    Logout user - invalidate tokens for a character
    
    Args:
        character_id: EVE character ID
        db: Database session
        
    Returns:
        Success message
    """
    try:
        # Find and delete token
        eve_token = db.query(EveToken).filter(
            EveToken.character_id == character_id
        ).first()
        
        if eve_token:
            db.delete(eve_token)
            db.commit()
        
        return {"message": "Logged out successfully", "character_id": character_id}
    except Exception as e:
        logger.error(f"Logout error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Logout failed")


@router.post("/refresh")
async def refresh_token(
    character_id: int = Query(..., description="Character ID to refresh token for"),
    db: Session = Depends(get_db),
):
    """
    Manually refresh access token for a character
    
    Args:
        character_id: EVE character ID
        db: Database session
        
    Returns:
        Success message with new expiration time
    """
    try:
        # Find token
        eve_token = db.query(EveToken).filter(
            EveToken.character_id == character_id
        ).first()
        
        if not eve_token:
            raise HTTPException(status_code=404, detail="Token not found")
        
        # Refresh token
        token_response = await esi_client.refresh_access_token(
            eve_token.refresh_token_encrypted
        )
        
        access_token = token_response.get("access_token")
        refresh_token = token_response.get("refresh_token")
        expires_in = token_response.get("expires_in", 1200)
        
        # Encrypt new tokens
        encrypted_access = encryption.encrypt(access_token)
        encrypted_refresh = encryption.encrypt(refresh_token)
        
        # Update token
        eve_token.access_token_encrypted = encrypted_access
        eve_token.refresh_token_encrypted = encrypted_refresh
        eve_token.expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        eve_token.last_refreshed_at = datetime.utcnow()
        
        db.commit()
        
        return {
            "message": "Token refreshed successfully",
            "character_id": character_id,
            "expires_at": eve_token.expires_at.isoformat(),
        }
        
    except ESITokenError as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(status_code=401, detail="Token refresh failed")
    except Exception as e:
        logger.error(f"Refresh error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Token refresh failed")


@router.get("/me")
async def get_current_user(
    character_id: int = Query(..., description="Character ID"),
    db: Session = Depends(get_db),
):
    """
    Get current authenticated user information
    
    Args:
        character_id: EVE character ID
        db: Database session
        
    Returns:
        User and character information
    """
    try:
        character = db.query(Character).filter(
            Character.character_id == character_id
        ).first()
        
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")
        
        eve_token = db.query(EveToken).filter(
            EveToken.character_id == character_id
        ).first()
        
        if not eve_token:
            raise HTTPException(status_code=404, detail="Token not found")
        
        # Check if token is expired
        is_expired = eve_token.expires_at < datetime.utcnow()
        
        return {
            "user": {
                "id": character.user.id,
                "username": character.user.username,
                "email": character.user.email,
            },
            "character": {
                "character_id": character.character_id,
                "character_name": character.character_name,
                "corporation_id": character.corporation_id,
                "corporation_name": character.corporation_name,
                "alliance_id": character.alliance_id,
                "alliance_name": character.alliance_name,
                "security_status": character.security_status,
            },
            "token": {
                "expires_at": eve_token.expires_at.isoformat(),
                "is_expired": is_expired,
                "last_refreshed_at": eve_token.last_refreshed_at.isoformat() if eve_token.last_refreshed_at else None,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user information")
