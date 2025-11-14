"""
Character sync tasks

Syncs personal character data from ESI: assets, market orders, wallet, skills, etc.
"""
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_
import logging
import asyncio

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.character import Character
from app.models.eve_token import EveToken
from app.models.market import MarketOrder
from app.services.esi_client import esi_client, ESIError, ESIRateLimitError
from app.services.type_cache import batch_get_type_info_cached

logger = logging.getLogger(__name__)


def run_async(coro):
    """Helper to run async functions in sync context"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_character_assets(self, character_id: int):
    """
    Sync character assets from ESI
    
    Args:
        character_id: EVE character ID
    """
    db: Session = SessionLocal()
    
    try:
        # Find valid token
        now = datetime.now(timezone.utc)
        token = db.query(EveToken).filter(
            and_(
                EveToken.character_id == character_id,
                EveToken.expires_at > now,
                EveToken.scope.contains("esi-assets.read_assets.v1"),
            )
        ).first()
        
        if not token:
            logger.warning(f"No valid token found for character {character_id}")
            return {"success": False, "error": "No valid token found"}
        
        access_token = token.get_access_token()
        
        # Fetch character assets
        assets_data = run_async(
            esi_client.request(
                "GET",
                f"/characters/{character_id}/assets/",
                access_token=access_token,
            )
        )
        
        logger.info(f"Fetched {len(assets_data)} assets for character {character_id}")
        
        # Collect unique type_ids and location_ids for batch fetching
        unique_type_ids = set()
        unique_location_ids = set()
        
        for asset in assets_data:
            type_id = asset.get("type_id")
            location_id = asset.get("location_id")
            if type_id:
                unique_type_ids.add(type_id)
            if location_id:
                unique_location_ids.add(location_id)
        
        # Batch fetch type information (using cache)
        type_info_map = {}
        if unique_type_ids:
            logger.info(f"Fetching type information for {len(unique_type_ids)} unique asset types")
            try:
                type_info_map = batch_get_type_info_cached(list(unique_type_ids), db)
                logger.info(f"Fetched type information for {len(type_info_map)} asset types")
            except Exception as e:
                logger.warning(f"Failed to batch fetch asset type info: {e}")
        
        # Batch fetch location information
        location_info_map = {}
        if unique_location_ids:
            logger.info(f"Fetching location information for {len(unique_location_ids)} unique asset locations")
            for loc_id in list(unique_location_ids):
                try:
                    # Use access_token for structure lookups
                    location_info = run_async(esi_client.get_location_info(loc_id, access_token))
                    location_info_map[loc_id] = location_info
                except Exception as e:
                    logger.warning(f"Failed to fetch location info for {loc_id}: {e}")
                    location_info_map[loc_id] = {"name": f"Location {loc_id}"}
            logger.info(f"Fetched location information for {len(location_info_map)} asset locations")
        
        # Store assets in character_data JSON field for now
        # TODO: Create a CharacterAsset model if needed
        character = db.query(Character).filter(
            Character.character_id == character_id
        ).first()
        
        if character:
            # Enhance assets with type and location names
            enhanced_assets = []
            for asset in assets_data:
                type_id = asset.get("type_id")
                location_id = asset.get("location_id")
                
                enhanced_asset = asset.copy()
                if type_id and type_id in type_info_map:
                    enhanced_asset["type_name"] = type_info_map[type_id].get("name")
                    enhanced_asset["type_icon_url"] = f"https://images.evetech.net/types/{type_id}/icon"
                
                if location_id and location_id in location_info_map:
                    loc_info = location_info_map[location_id]
                    enhanced_asset["location_name"] = loc_info.get("name")
                    enhanced_asset["system_id"] = loc_info.get("system_id") or loc_info.get("solar_system_id")
                    enhanced_asset["system_name"] = loc_info.get("system_name")
                    enhanced_asset["region_name"] = loc_info.get("region_name")
                
                enhanced_assets.append(enhanced_asset)
            
            # Store in character_data
            if not character.character_data:
                character.character_data = {}
            character.character_data["assets"] = enhanced_assets
            character.character_data["assets_synced_at"] = datetime.now(timezone.utc).isoformat()
            character.last_synced_at = datetime.now(timezone.utc)
            
            db.commit()
            logger.info(f"Synced {len(enhanced_assets)} character assets for character {character_id}")
        
        return {
            "success": True,
            "character_id": character_id,
            "assets_count": len(assets_data),
            "synced_at": datetime.now(timezone.utc).isoformat(),
        }
        
    except ESIError as e:
        logger.error(f"Failed to sync character assets for {character_id}: {e}")
        db.rollback()
        raise self.retry(exc=e)
    except Exception as e:
        logger.error(f"Error syncing character assets for {character_id}: {e}")
        db.rollback()
        raise self.retry(exc=e)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_character_market_orders(self, character_id: int):
    """
    Sync character's personal market orders from ESI
    
    Args:
        character_id: EVE character ID
    """
    db: Session = SessionLocal()
    synced_count = 0
    error_count = 0
    
    try:
        # Find valid token
        now = datetime.now(timezone.utc)
        token = db.query(EveToken).filter(
            and_(
                EveToken.character_id == character_id,
                EveToken.expires_at > now,
                EveToken.scope.contains("esi-markets.read_character_orders.v1"),
            )
        ).first()
        
        if not token:
            logger.warning(f"No valid token found for character {character_id}")
            return {"success": False, "error": "No valid token found"}
        
        access_token = token.get_access_token()
        
        # Fetch character market orders
        orders_data = run_async(
            esi_client.request(
                "GET",
                f"/characters/{character_id}/orders/",
                access_token=access_token,
            )
        )
        
        logger.info(f"Fetched {len(orders_data)} market orders for character {character_id}")
        
        # Collect unique type_ids and location_ids for batch fetching
        unique_type_ids = set()
        unique_location_ids = set()
        
        orders_to_process = []
        for order_data in orders_data:
            order_id = order_data.get("order_id")
            if not order_id:
                continue
            
            type_id = order_data.get("type_id")
            location_id = order_data.get("location_id")
            if type_id:
                unique_type_ids.add(type_id)
            if location_id:
                unique_location_ids.add(location_id)
            orders_to_process.append(order_data)
        
        # Batch fetch type information (using cache)
        type_info_map = {}
        if unique_type_ids:
            logger.info(f"Fetching type information for {len(unique_type_ids)} unique types")
            try:
                type_info_map = batch_get_type_info_cached(list(unique_type_ids), db)
                logger.info(f"Fetched type information for {len(type_info_map)} types")
            except Exception as e:
                logger.warning(f"Failed to batch fetch type info: {e}")
        
        # Batch fetch location information
        location_info_map = {}
        if unique_location_ids:
            logger.info(f"Fetching location information for {len(unique_location_ids)} unique locations")
            for loc_id in list(unique_location_ids):
                try:
                    location_info = run_async(esi_client.get_location_info(loc_id, access_token))
                    location_info_map[loc_id] = location_info
                except Exception as e:
                    logger.warning(f"Failed to fetch location info for {loc_id}: {e}")
                    location_info_map[loc_id] = {"name": f"Location {loc_id}"}
            logger.info(f"Fetched location information for {len(location_info_map)} locations")
        
        # Process orders - create/update with type and location names
        for order_data in orders_to_process:
            order_id = order_data.get("order_id")
            type_id = order_data.get("type_id")
            location_id = order_data.get("location_id")
            
            # Get type name
            type_name = None
            if type_id and type_id in type_info_map:
                type_name = type_info_map[type_id].get("name")
            
            # Get location name and system/region info
            location_name = None
            system_id_from_location = None
            system_name = None
            region_name = None
            if location_id and location_id in location_info_map:
                loc_info = location_info_map[location_id]
                location_name = loc_info.get("name")
                system_id_from_location = loc_info.get("system_id") or loc_info.get("solar_system_id")
                system_name = loc_info.get("system_name")
                region_name = loc_info.get("region_name")
            
            # Get region_id from order data or location
            region_id = order_data.get("region_id")
            if not region_id and system_id_from_location:
                # Try to get region from system
                try:
                    system_info = run_async(esi_client.get_system_info(system_id_from_location))
                    region_id = system_info.get("region_id")
                except:
                    pass
            
            # Check if order already exists
            existing = db.query(MarketOrder).filter(
                and_(
                    MarketOrder.order_id == order_id,
                    MarketOrder.character_id == character_id,
                )
            ).first()
            
            if existing:
                # Update existing order
                existing.price = order_data.get("price", 0)
                existing.volume_total = order_data.get("volume_total", 0)
                existing.volume_remain = order_data.get("volume_remain", 0)
                existing.min_volume = order_data.get("min_volume")
                existing.duration = order_data.get("duration")
                existing.issued = datetime.fromisoformat(order_data.get("issued", "").replace("Z", "+00:00")) if order_data.get("issued") else None
                existing.expires = datetime.fromisoformat(order_data.get("expires", "").replace("Z", "+00:00")) if order_data.get("expires") else None
                existing.is_active = order_data.get("is_active", True)
                existing.range_type = order_data.get("range") if isinstance(order_data.get("range"), str) else None
                existing.range_value = order_data.get("range") if isinstance(order_data.get("range"), int) else None
                existing.order_data = order_data
                existing.last_synced_at = datetime.now(timezone.utc)
                # Update type and location names
                if type_name:
                    existing.type_name = type_name
                if location_name:
                    existing.location_name = location_name
                if system_id_from_location:
                    existing.system_id = system_id_from_location
                if system_name:
                    existing.system_name = system_name
                if region_name:
                    existing.region_name = region_name
            else:
                # Create new order
                order = MarketOrder(
                    order_id=order_id,
                    character_id=character_id,
                    type_id=type_id,
                    type_name=type_name,
                    is_buy_order=order_data.get("is_buy_order", False),
                    location_id=location_id,
                    location_type=order_data.get("location_type"),
                    location_name=location_name,
                    region_id=region_id,
                    region_name=region_name,
                    system_id=system_id_from_location,
                    system_name=system_name,
                    price=order_data.get("price", 0),
                    volume_total=order_data.get("volume_total", 0),
                    volume_remain=order_data.get("volume_remain", 0),
                    min_volume=order_data.get("min_volume"),
                    duration=order_data.get("duration"),
                    issued=datetime.fromisoformat(order_data.get("issued", "").replace("Z", "+00:00")) if order_data.get("issued") else None,
                    expires=datetime.fromisoformat(order_data.get("expires", "").replace("Z", "+00:00")) if order_data.get("expires") else None,
                    is_active=order_data.get("is_active", True),
                    range_type=order_data.get("range") if isinstance(order_data.get("range"), str) else None,
                    range_value=order_data.get("range") if isinstance(order_data.get("range"), int) else None,
                    order_data=order_data,
                    last_synced_at=datetime.now(timezone.utc),
                )
                db.add(order)
                synced_count += 1
        
        db.commit()
        logger.info(f"Synced {synced_count} new market orders for character {character_id} with type and location names")
        
        return {
            "success": True,
            "character_id": character_id,
            "synced": synced_count,
            "errors": error_count,
        }
        
    except ESIRateLimitError as e:
        logger.warning(f"Rate limit hit for character {character_id}: {e}")
        raise self.retry(exc=e)
    except ESIError as e:
        logger.error(f"Failed to sync market orders for character {character_id}: {e}")
        error_count += 1
        raise self.retry(exc=e)
    except Exception as e:
        logger.error(f"Error syncing market orders for character {character_id}: {e}")
        db.rollback()
        raise self.retry(exc=e)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_character_details(self, character_id: int):
    """
    Sync detailed character information from ESI
    
    Fetches: contacts, standings, titles, blueprints, loyalty, medals, fatigue,
    opportunities, notifications, mail, calendar, chat channels, FW stats,
    wallet, location, online status, ship type, skill queue, skills
    
    Args:
        character_id: EVE character ID
    """
    db: Session = SessionLocal()
    
    try:
        # Find valid token
        now = datetime.now(timezone.utc)
        token = db.query(EveToken).filter(
            and_(
                EveToken.character_id == character_id,
                EveToken.expires_at > now,
            )
        ).first()
        
        if not token:
            logger.warning(f"No valid token found for character {character_id}")
            return {"success": False, "error": "No valid token found"}
        
        access_token = token.get_access_token()
        character = db.query(Character).filter(
            Character.character_id == character_id
        ).first()
        
        if not character:
            logger.warning(f"Character {character_id} not found in database")
            return {"success": False, "error": "Character not found"}
        
        character_details = {}
        
        # Fetch character info
        try:
            char_info = run_async(esi_client.get_character_info(character_id, access_token))
            character_details["character_info"] = char_info
            # Update character model
            if char_info.get("corporation_id"):
                character.corporation_id = char_info.get("corporation_id")
            if char_info.get("alliance_id"):
                character.alliance_id = char_info.get("alliance_id")
            if char_info.get("security_status") is not None:
                character.security_status = str(char_info.get("security_status"))
        except ESIError as e:
            logger.warning(f"Failed to fetch character info: {e}")
        
        # Fetch corporation name if we have corporation_id
        if character.corporation_id:
            try:
                corp_info = run_async(
                    esi_client.request(
                        "GET",
                        f"/corporations/{character.corporation_id}/",
                    )
                )
                character.corporation_name = corp_info.get("name")
                character_details["corporation_info"] = corp_info
            except ESIError as e:
                logger.warning(f"Failed to fetch corporation info: {e}")
        
        # Fetch alliance name if we have alliance_id
        if character.alliance_id:
            try:
                alliance_info = run_async(
                    esi_client.request(
                        "GET",
                        f"/alliances/{character.alliance_id}/",
                    )
                )
                character.alliance_name = alliance_info.get("name")
                character_details["alliance_info"] = alliance_info
            except ESIError as e:
                logger.warning(f"Failed to fetch alliance info: {e}")
        
        # Note: Removed contacts and standings as those scopes may not be valid
        
        # Fetch wallet balance
        if "esi-characters.read_wallet.v1" in token.scope:
            try:
                wallet_balance = run_async(
                    esi_client.request(
                        "GET",
                        f"/characters/{character_id}/wallet/",
                        access_token=access_token,
                    )
                )
                character_details["wallet_balance"] = wallet_balance
            except ESIError as e:
                logger.warning(f"Failed to fetch wallet balance: {e}")
        
        # Fetch location
        if "esi-location.read_location.v1" in token.scope:
            try:
                location = run_async(
                    esi_client.request(
                        "GET",
                        f"/characters/{character_id}/location/",
                        access_token=access_token,
                    )
                )
                character_details["location"] = location
            except ESIError as e:
                logger.warning(f"Failed to fetch location: {e}")
        
        # Fetch ship type
        if "esi-characters.read_ship_type.v1" in token.scope:
            try:
                ship = run_async(
                    esi_client.request(
                        "GET",
                        f"/characters/{character_id}/ship/",
                        access_token=access_token,
                    )
                )
                character_details["ship"] = ship
            except ESIError as e:
                logger.warning(f"Failed to fetch ship: {e}")
        
        # Fetch skill queue
        if "esi-characters.read_skillqueue.v1" in token.scope:
            try:
                skill_queue = run_async(
                    esi_client.request(
                        "GET",
                        f"/characters/{character_id}/skillqueue/",
                        access_token=access_token,
                    )
                )
                character_details["skill_queue"] = skill_queue
            except ESIError as e:
                logger.warning(f"Failed to fetch skill queue: {e}")
        
        # Fetch skills
        if "esi-characters.read_skills.v1" in token.scope:
            try:
                skills = run_async(
                    esi_client.request(
                        "GET",
                        f"/characters/{character_id}/skills/",
                        access_token=access_token,
                    )
                )
                character_details["skills"] = skills
            except ESIError as e:
                logger.warning(f"Failed to fetch skills: {e}")
        
        # Store all details in character_data
        if not character.character_data:
            character.character_data = {}
        character.character_data.update(character_details)
        character.character_data["details_synced_at"] = datetime.now(timezone.utc).isoformat()
        character.last_synced_at = datetime.now(timezone.utc)
        
        db.commit()
        logger.info(f"Synced detailed character information for {character_id}")
        
        return {
            "success": True,
            "character_id": character_id,
            "synced_at": datetime.now(timezone.utc).isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Error syncing character details for {character_id}: {e}")
        db.rollback()
        raise self.retry(exc=e)
    finally:
        db.close()

