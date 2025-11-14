"""
Type cache service

Provides caching layer for EVE Online type information to reduce ESI API calls.
Checks database cache first before making ESI requests.
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
import logging

from app.core.database import SessionLocal
from app.models.universe import UniverseType
from app.services.esi_client import esi_client, ESIError

logger = logging.getLogger(__name__)

# Cache expiration: types are cached for 30 days (they rarely change)
CACHE_EXPIRY_DAYS = 30


def get_type_info_cached(type_id: int, db: Session = None) -> Optional[Dict[str, Any]]:
    """
    Get type information from cache or ESI
    
    Args:
        type_id: EVE type ID
        db: Optional database session (creates new one if not provided)
        
    Returns:
        Type information dictionary or None if not found
    """
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True
    
    try:
        # Check cache first
        cached_type = db.query(UniverseType).filter(
            UniverseType.type_id == type_id
        ).first()
        
        if cached_type:
            # Check if cache is still valid
            if cached_type.last_synced_at:
                now = datetime.now(timezone.utc)
                expires_at = cached_type.last_synced_at
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                cache_age = now - expires_at
                if cache_age < timedelta(days=CACHE_EXPIRY_DAYS):
                    # Cache is valid, return cached data
                    return {
                        "type_id": cached_type.type_id,
                        "name": cached_type.name,
                        "description": cached_type.description,
                        "group_id": cached_type.group_id,
                        "group_name": cached_type.group_name,
                        "category_id": cached_type.category_id,
                        "category_name": cached_type.category_name,
                        "mass": cached_type.mass,
                        "volume": cached_type.volume,
                        "capacity": cached_type.capacity,
                        "portion_size": cached_type.portion_size,
                        "published": cached_type.published,
                        "icon_id": cached_type.icon_id,
                        "icon_url": cached_type.icon_url or f"https://images.evetech.net/types/{cached_type.type_id}/icon",
                        "type_data": cached_type.type_data,
                    }
        
        # Cache miss or expired, fetch from ESI
        try:
            # Note: get_type_info is async, so we need to handle it properly
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            type_info = loop.run_until_complete(esi_client.get_type_info(type_id))
            
            # Fetch group and category names if available
            group_name = None
            category_name = None
            if type_info.get("group_id"):
                try:
                    group_info = loop.run_until_complete(esi_client.get_group_info(type_info.get("group_id")))
                    group_name = group_info.get("name")
                    # Also get category_id from group if not in type_info
                    if not type_info.get("category_id") and group_info.get("category_id"):
                        type_info["category_id"] = group_info.get("category_id")
                except ESIError:
                    pass
            
            if type_info.get("category_id"):
                try:
                    category_info = loop.run_until_complete(esi_client.get_category_info(type_info.get("category_id")))
                    category_name = category_info.get("name")
                except ESIError:
                    pass
            
            # Store in cache
            if cached_type:
                # Update existing
                cached_type.name = type_info.get("name", "")
                cached_type.description = type_info.get("description", "")
                cached_type.group_id = type_info.get("group_id")
                cached_type.group_name = group_name
                cached_type.category_id = type_info.get("category_id")
                cached_type.category_name = category_name
                cached_type.mass = type_info.get("mass")
                cached_type.volume = type_info.get("volume")
                cached_type.capacity = type_info.get("capacity")
                cached_type.portion_size = type_info.get("portion_size")
                cached_type.published = type_info.get("published", True)
                cached_type.icon_id = type_info.get("icon_id")
                cached_type.icon_url = f"https://images.evetech.net/types/{type_id}/icon"
                cached_type.type_data = type_info
                cached_type.last_synced_at = datetime.now(timezone.utc)
                cached_type.updated_at = datetime.now(timezone.utc)
            else:
                # Create new
                cached_type = UniverseType(
                    type_id=type_id,
                    name=type_info.get("name", ""),
                    description=type_info.get("description", ""),
                    group_id=type_info.get("group_id"),
                    group_name=group_name,
                    category_id=type_info.get("category_id"),
                    category_name=category_name,
                    mass=type_info.get("mass"),
                    volume=type_info.get("volume"),
                    capacity=type_info.get("capacity"),
                    portion_size=type_info.get("portion_size"),
                    published=type_info.get("published", True),
                    icon_id=type_info.get("icon_id"),
                    icon_url=f"https://images.evetech.net/types/{type_id}/icon",
                    type_data=type_info,
                    last_synced_at=datetime.now(timezone.utc),
                )
                db.add(cached_type)
            
            db.commit()
            
            # Return the fetched data
            return {
                "type_id": type_id,
                "name": cached_type.name,
                "description": cached_type.description,
                "group_id": cached_type.group_id,
                "category_id": cached_type.category_id,
                "mass": cached_type.mass,
                "volume": cached_type.volume,
                "capacity": cached_type.capacity,
                "portion_size": cached_type.portion_size,
                "published": cached_type.published,
                "icon_id": cached_type.icon_id,
                "icon_url": cached_type.icon_url,
                "type_data": cached_type.type_data,
            }
            
        except ESIError as e:
            logger.warning(f"Failed to fetch type info for {type_id} from ESI: {e}")
            # Return cached data even if expired, if available
            if cached_type:
                return {
                    "type_id": cached_type.type_id,
                    "name": cached_type.name,
                    "description": cached_type.description,
                    "group_id": cached_type.group_id,
                    "category_id": cached_type.category_id,
                    "icon_url": cached_type.icon_url or f"https://images.evetech.net/types/{cached_type.type_id}/icon",
                }
            return None
            
    finally:
        if should_close:
            db.close()


def batch_get_type_info_cached(type_ids: List[int], db: Session = None) -> Dict[int, Dict[str, Any]]:
    """
    Batch get type information from cache or ESI
    
    Args:
        type_ids: List of type IDs to fetch
        db: Optional database session
        
    Returns:
        Dictionary mapping type_id to type information
    """
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True
    
    try:
        results = {}
        uncached_ids = []
        
        # Check cache for all types
        for type_id in type_ids:
            cached_type = db.query(UniverseType).filter(
                UniverseType.type_id == type_id
            ).first()
            
            if cached_type and cached_type.last_synced_at:
                now = datetime.now(timezone.utc)
                expires_at = cached_type.last_synced_at
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                cache_age = now - expires_at
                if cache_age < timedelta(days=CACHE_EXPIRY_DAYS):
                    # Cache hit
                    results[type_id] = {
                        "type_id": cached_type.type_id,
                        "name": cached_type.name,
                        "description": cached_type.description,
                        "group_id": cached_type.group_id,
                        "category_id": cached_type.category_id,
                        "icon_url": cached_type.icon_url or f"https://images.evetech.net/types/{cached_type.type_id}/icon",
                    }
                    continue
            
            # Cache miss or expired
            uncached_ids.append(type_id)
        
        # Fetch uncached types from ESI
        if uncached_ids:
            logger.info(f"Fetching {len(uncached_ids)} types from ESI (cache miss)")
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Fetch each type (could be optimized with batch requests if ESI supports it)
            for type_id in uncached_ids:
                try:
                    type_info = loop.run_until_complete(esi_client.get_type_info(type_id))
                    
                    # Fetch group and category names if available
                    group_name = None
                    category_name = None
                    if type_info.get("group_id"):
                        try:
                            group_info = loop.run_until_complete(esi_client.get_group_info(type_info.get("group_id")))
                            group_name = group_info.get("name")
                            # Also get category_id from group if not in type_info
                            if not type_info.get("category_id") and group_info.get("category_id"):
                                type_info["category_id"] = group_info.get("category_id")
                        except ESIError:
                            pass
                    
                    if type_info.get("category_id"):
                        try:
                            category_info = loop.run_until_complete(esi_client.get_category_info(type_info.get("category_id")))
                            category_name = category_info.get("name")
                        except ESIError:
                            pass
                    
                    # Store in cache
                    cached_type = db.query(UniverseType).filter(
                        UniverseType.type_id == type_id
                    ).first()
                    
                    if cached_type:
                        cached_type.name = type_info.get("name", "")
                        cached_type.description = type_info.get("description", "")
                        cached_type.group_id = type_info.get("group_id")
                        cached_type.group_name = group_name
                        cached_type.category_id = type_info.get("category_id")
                        cached_type.category_name = category_name
                        cached_type.mass = type_info.get("mass")
                        cached_type.volume = type_info.get("volume")
                        cached_type.type_data = type_info
                        cached_type.last_synced_at = datetime.now(timezone.utc)
                        cached_type.updated_at = datetime.now(timezone.utc)
                    else:
                        cached_type = UniverseType(
                            type_id=type_id,
                            name=type_info.get("name", ""),
                            description=type_info.get("description", ""),
                            group_id=type_info.get("group_id"),
                            group_name=group_name,
                            category_id=type_info.get("category_id"),
                            category_name=category_name,
                            mass=type_info.get("mass"),
                            volume=type_info.get("volume"),
                            icon_url=f"https://images.evetech.net/types/{type_id}/icon",
                            type_data=type_info,
                            last_synced_at=datetime.now(timezone.utc),
                        )
                        db.add(cached_type)
                    
                    results[type_id] = {
                        "type_id": type_id,
                        "name": cached_type.name,
                        "description": cached_type.description,
                        "group_id": cached_type.group_id,
                        "group_name": cached_type.group_name,
                        "category_id": cached_type.category_id,
                        "category_name": cached_type.category_name,
                        "icon_url": cached_type.icon_url or f"https://images.evetech.net/types/{type_id}/icon",
                    }
                    
                except ESIError as e:
                    logger.warning(f"Failed to fetch type info for {type_id}: {e}")
                    # Try to return stale cache if available
                    cached_type = db.query(UniverseType).filter(
                        UniverseType.type_id == type_id
                    ).first()
                    if cached_type:
                        results[type_id] = {
                            "type_id": cached_type.type_id,
                            "name": cached_type.name,
                            "icon_url": cached_type.icon_url or f"https://images.evetech.net/types/{cached_type.type_id}/icon",
                        }
                    else:
                        results[type_id] = {"name": f"Type {type_id}", "type_id": type_id}
            
            db.commit()
        
        return results
        
    finally:
        if should_close:
            db.close()

