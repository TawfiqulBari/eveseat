"""
Corporation sync tasks

Syncs corporation data from ESI: info, members, assets, structures
"""
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_
import logging
import asyncio

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.corporation import (
    Corporation, CorporationMember, CorporationAsset, CorporationStructure
)
from app.models.eve_token import EveToken
from app.models.character import Character
from app.services.esi_client import esi_client, ESIError, ESIRateLimitError
from app.services.type_cache import batch_get_type_info_cached
from app.core.encryption import encryption

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
def sync_corporation_data(self, corporation_id: int, character_id: int = None):
    """
    Sync corporation data from ESI
    
    Syncs:
    - Corporation information
    - Corporation members
    - Corporation assets
    - Corporation structures
    
    Args:
        corporation_id: EVE corporation ID
        character_id: Character ID with access token (optional, will find one if not provided)
    """
    db: Session = SessionLocal()
    
    try:
        # Find a token with corporation read scope
        now = datetime.now(timezone.utc)
        if character_id:
            token = db.query(EveToken).filter(
                and_(
                    EveToken.character_id == character_id,
                    EveToken.expires_at > now,
                    EveToken.scope.contains("esi-corporations.read_corporation_membership.v1"),
                )
            ).first()
        else:
            token = db.query(EveToken).filter(
                and_(
                    EveToken.expires_at > now,
                    EveToken.scope.contains("esi-corporations.read_corporation_membership.v1"),
                )
            ).first()
        
        if not token:
            logger.warning(f"No valid token found for corporation {corporation_id}")
            return {"success": False, "error": "No valid token found"}
        
        # Decrypt access token
        access_token = encryption.decrypt(token.access_token_encrypted)
        
        # Sync corporation info
        try:
            corp_info = run_async(
                esi_client.request(
                    "GET",
                    f"/corporations/{corporation_id}/",
                    access_token=access_token,
                )
            )
            
            # Update or create corporation
            corporation = db.query(Corporation).filter(
                Corporation.corporation_id == corporation_id
            ).first()
            
            if not corporation:
                corporation = Corporation(
                    corporation_id=corporation_id,
                    corporation_name=corp_info.get("name", ""),
                    ticker=corp_info.get("ticker"),
                    ceo_id=corp_info.get("ceo_id"),
                    alliance_id=corp_info.get("alliance_id"),
                    date_founded=datetime.fromisoformat(corp_info.get("date_founded", "").replace("Z", "+00:00")) if corp_info.get("date_founded") else None,
                    creator_id=corp_info.get("creator_id"),
                    member_count=corp_info.get("member_count"),
                    shares=corp_info.get("shares"),
                    tax_rate=corp_info.get("tax_rate"),
                    description=corp_info.get("description"),
                    url=corp_info.get("url"),
                    faction_id=corp_info.get("faction_id"),
                    home_station_id=corp_info.get("home_station_id"),
                    corporation_data=corp_info,
                    last_synced_at=datetime.now(timezone.utc),
                )
                db.add(corporation)
                db.flush()
            else:
                corporation.corporation_name = corp_info.get("name", "")
                corporation.ticker = corp_info.get("ticker")
                corporation.ceo_id = corp_info.get("ceo_id")
                corporation.alliance_id = corp_info.get("alliance_id")
                corporation.member_count = corp_info.get("member_count")
                corporation.shares = corp_info.get("shares")
                corporation.tax_rate = corp_info.get("tax_rate")
                corporation.description = corp_info.get("description")
                corporation.url = corp_info.get("url")
                corporation.faction_id = corp_info.get("faction_id")
                corporation.home_station_id = corp_info.get("home_station_id")
                corporation.corporation_data = corp_info
                corporation.last_synced_at = datetime.now(timezone.utc)
            
            db.commit()
            logger.info(f"Synced corporation info for {corporation_id}")
            
        except ESIError as e:
            logger.error(f"Failed to sync corporation info: {e}")
            db.rollback()
        
        # Sync corporation members (requires esi-corporations.read_corporation_membership.v1)
        try:
            members_data = run_async(
                esi_client.request(
                    "GET",
                    f"/corporations/{corporation_id}/members/",
                    access_token=access_token,
                )
            )
            
            # Get member roles
            for member_char_id in members_data:
                try:
                    roles_data = run_async(
                        esi_client.request(
                            "GET",
                            f"/corporations/{corporation_id}/members/{member_char_id}/roles/",
                            access_token=access_token,
                        )
                    )
                    
                    # Get character name (from ESI or our database)
                    character = db.query(Character).filter(
                        Character.character_id == member_char_id
                    ).first()
                    
                    member = db.query(CorporationMember).filter(
                        and_(
                            CorporationMember.corporation_id == corporation_id,
                            CorporationMember.character_id == member_char_id,
                        )
                    ).first()
                    
                    if not member:
                        member = CorporationMember(
                            corporation_id=corporation_id,
                            character_id=member_char_id,
                            character_name=character.character_name if character else None,
                            roles=roles_data.get("roles", []),
                            grantable_roles=roles_data.get("grantable_roles", []),
                            roles_at_hq=roles_data.get("roles_at_hq", []),
                            roles_at_base=roles_data.get("roles_at_base", []),
                            roles_at_other=roles_data.get("roles_at_other", []),
                            member_data=roles_data,
                            last_synced_at=datetime.now(timezone.utc),
                        )
                        db.add(member)
                    else:
                        member.roles = roles_data.get("roles", [])
                        member.grantable_roles = roles_data.get("grantable_roles", [])
                        member.roles_at_hq = roles_data.get("roles_at_hq", [])
                        member.roles_at_base = roles_data.get("roles_at_base", [])
                        member.roles_at_other = roles_data.get("roles_at_other", [])
                        member.member_data = roles_data
                        member.last_synced_at = datetime.now(timezone.utc)
                    
                except ESIError as e:
                    logger.warning(f"Failed to get roles for member {member_char_id}: {e}")
                    continue
            
            db.commit()
            logger.info(f"Synced {len(members_data)} corporation members")
            
        except ESIError as e:
            logger.warning(f"Failed to sync corporation members: {e}")
            db.rollback()
        
        # Sync corporation assets (requires esi-assets.read_corporation_assets.v1)
        try:
            assets_data = run_async(
                esi_client.request(
                    "GET",
                    f"/corporations/{corporation_id}/assets/",
                    access_token=access_token,
                )
            )
            
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
                    logger.info(f"Fetched type information for {len(type_info_map)} asset types (from cache or ESI)")
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
            
            # Clear existing assets
            db.query(CorporationAsset).filter(
                CorporationAsset.corporation_id == corporation_id
            ).delete()
            
            # Add new assets with type and location names
            for asset in assets_data:
                type_id = asset.get("type_id")
                location_id = asset.get("location_id")
                
                # Get type name
                type_name = None
                if type_id and type_id in type_info_map:
                    type_name = type_info_map[type_id].get("name")
                
                # Get location name
                location_name = None
                if location_id and location_id in location_info_map:
                    loc_info = location_info_map[location_id]
                    location_name = loc_info.get("name")
                
                corp_asset = CorporationAsset(
                    corporation_id=corporation_id,
                    type_id=type_id,
                    type_name=type_name,
                    quantity=asset.get("quantity", 1),
                    location_id=location_id,
                    location_type=asset.get("location_type"),
                    location_name=location_name,
                    is_singleton=asset.get("is_singleton", False),
                    item_id=asset.get("item_id"),
                    flag=asset.get("flag"),
                    asset_data=asset,
                    last_synced_at=datetime.now(timezone.utc),
                )
                db.add(corp_asset)
            
            db.commit()
            logger.info(f"Synced {len(assets_data)} corporation assets with type and location names")
            
        except ESIError as e:
            logger.warning(f"Failed to sync corporation assets: {e}")
            db.rollback()
        
        # Sync corporation structures (requires esi-corporations.read_structures.v1)
        try:
            structures_data = run_async(
                esi_client.request(
                    "GET",
                    f"/corporations/{corporation_id}/structures/",
                    access_token=access_token,
                )
            )
            
            for struct_data in structures_data:
                structure_id = struct_data.get("structure_id")
                
                structure = db.query(CorporationStructure).filter(
                    CorporationStructure.structure_id == structure_id
                ).first()
                
                if not structure:
                    structure = CorporationStructure(
                        corporation_id=corporation_id,
                        structure_id=structure_id,
                        structure_type_id=struct_data.get("type_id"),
                        system_id=struct_data.get("system_id"),
                        fuel_expires=datetime.fromisoformat(struct_data.get("fuel_expires", "").replace("Z", "+00:00")) if struct_data.get("fuel_expires") else None,
                        state=struct_data.get("state"),
                        state_timer_start=datetime.fromisoformat(struct_data.get("state_timer_start", "").replace("Z", "+00:00")) if struct_data.get("state_timer_start") else None,
                        state_timer_end=datetime.fromisoformat(struct_data.get("state_timer_end", "").replace("Z", "+00:00")) if struct_data.get("state_timer_end") else None,
                        unanchors_at=datetime.fromisoformat(struct_data.get("unanchors_at", "").replace("Z", "+00:00")) if struct_data.get("unanchors_at") else None,
                        reinforce_hour=struct_data.get("reinforce_hour"),
                        reinforce_weekday=struct_data.get("reinforce_weekday"),
                        services=struct_data.get("services", []),
                        structure_data=struct_data,
                        last_synced_at=datetime.now(timezone.utc),
                    )
                    db.add(structure)
                else:
                    structure.fuel_expires=datetime.fromisoformat(struct_data.get("fuel_expires", "").replace("Z", "+00:00")) if struct_data.get("fuel_expires") else None
                    structure.state=struct_data.get("state")
                    structure.state_timer_start=datetime.fromisoformat(struct_data.get("state_timer_start", "").replace("Z", "+00:00")) if struct_data.get("state_timer_start") else None
                    structure.state_timer_end=datetime.fromisoformat(struct_data.get("state_timer_end", "").replace("Z", "+00:00")) if struct_data.get("state_timer_end") else None
                    structure.unanchors_at=datetime.fromisoformat(struct_data.get("unanchors_at", "").replace("Z", "+00:00")) if struct_data.get("unanchors_at") else None
                    structure.reinforce_hour=struct_data.get("reinforce_hour")
                    structure.reinforce_weekday=struct_data.get("reinforce_weekday")
                    structure.services=struct_data.get("services", [])
                    structure.structure_data=struct_data
                    structure.last_synced_at=datetime.now(timezone.utc)
            
            db.commit()
            logger.info(f"Synced {len(structures_data)} corporation structures")
            
        except ESIError as e:
            logger.warning(f"Failed to sync corporation structures: {e}")
            db.rollback()
        
        return {
            "success": True,
            "corporation_id": corporation_id,
            "synced_at": datetime.now(timezone.utc).isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Error syncing corporation {corporation_id}: {e}")
        db.rollback()
        raise self.retry(exc=e)
    finally:
        db.close()


@celery_app.task
def sync_all_corporations():
    """
    Sync all corporations that users have access to
    
    Runs hourly via Celery Beat
    """
    db: Session = SessionLocal()
    synced_count = 0
    error_count = 0
    
    try:
        # Get all unique corporation IDs from characters
        corporations = db.query(Character.corporation_id).distinct().filter(
            Character.corporation_id.isnot(None)
        ).all()
        
        corporation_ids = [corp[0] for corp in corporations]
        
        logger.info(f"Found {len(corporation_ids)} corporations to sync")
        
        for corp_id in corporation_ids:
            try:
                # Find a character with access to this corporation
                character = db.query(Character).filter(
                    Character.corporation_id == corp_id
                ).first()
                
                if character:
                    result = sync_corporation_data.delay(corp_id, character.character_id)
                    synced_count += 1
                else:
                    # Try without character_id
                    result = sync_corporation_data.delay(corp_id)
                    synced_count += 1
                    
            except Exception as e:
                logger.error(f"Error queuing sync for corporation {corp_id}: {e}")
                error_count += 1
        
        logger.info(f"Queued {synced_count} corporation syncs, {error_count} errors")
        return {
            "queued": synced_count,
            "errors": error_count,
            "total": len(corporation_ids),
        }
        
    except Exception as e:
        logger.error(f"Error in sync_all_corporations: {e}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()

