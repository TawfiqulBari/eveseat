"""
Market sync tasks

Syncs market data from ESI for major trade hubs
"""
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_
import logging
import asyncio

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.market import MarketOrder, PriceHistory
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


# Major trade hub system IDs
TRADE_HUBS = {
    "Jita": 30000142,  # The Forge - Jita IV - Moon 4 - Caldari Navy Assembly Plant
    "Amarr": 30002187,  # Domain - Amarr VIII (Oris) - Emperor Family Academy
    "Dodixie": 30002659,  # Sinq Laison - Dodixie IX - Moon 20 - Federation Navy Assembly Plant
    "Rens": 30002510,  # Heimatar - Rens VI - Moon 8 - Brutor Tribe Treasury
    "Hek": 30002053,  # Metropolis - Hek VIII - Moon 12 - Boundless Creation Factory
}


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_market_orders(self, region_id: int, system_id: int = None):
    """
    Sync market orders from ESI for a region or system
    
    Args:
        region_id: EVE region ID
        system_id: Optional system ID (if None, syncs all systems in region)
    """
    db: Session = SessionLocal()
    synced_count = 0
    error_count = 0
    
    try:
        # ESI endpoint: GET /markets/{region_id}/orders/
        params = {}
        if system_id:
            params["type_id"] = system_id  # Actually, system_id filter might not be available
            # We'll sync all orders for the region
        
        try:
            orders_data = run_async(
                esi_client.request(
                    "GET",
                    f"/markets/{region_id}/orders/",
                    params=params,
                )
            )
            
            logger.info(f"Fetched {len(orders_data)} market orders for region {region_id}")
            
            # Collect unique type_ids and location_ids for batch fetching
            unique_type_ids = set()
            unique_location_ids = set()
            
            # Process orders - first pass: collect IDs
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
                    logger.info(f"Fetched type information for {len(type_info_map)} types (from cache or ESI)")
                except Exception as e:
                    logger.warning(f"Failed to batch fetch type info: {e}")
            
            # Batch fetch location information
            location_info_map = {}
            if unique_location_ids:
                logger.info(f"Fetching location information for {len(unique_location_ids)} unique locations")
                for loc_id in list(unique_location_ids):
                    try:
                        location_info = run_async(esi_client.get_location_info(loc_id))
                        location_info_map[loc_id] = location_info
                    except Exception as e:
                        logger.warning(f"Failed to fetch location info for {loc_id}: {e}")
                        location_info_map[loc_id] = {"name": f"Location {loc_id}"}
                logger.info(f"Fetched location information for {len(location_info_map)} locations")
            
            # Process orders - second pass: create/update with type and location names
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
                
                # Check if order already exists
                existing = db.query(MarketOrder).filter(
                    MarketOrder.order_id == order_id
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
            logger.info(f"Synced {synced_count} new market orders for region {region_id} with type and location names")
            
        except ESIRateLimitError as e:
            logger.warning(f"Rate limit hit for region {region_id}: {e}")
            raise self.retry(exc=e)
        except ESIError as e:
            logger.error(f"Failed to sync market orders for region {region_id}: {e}")
            error_count += 1
        
        return {
            "success": True,
            "region_id": region_id,
            "synced": synced_count,
            "errors": error_count,
        }
        
    except Exception as e:
        logger.error(f"Error syncing market orders for region {region_id}: {e}")
        db.rollback()
        raise self.retry(exc=e)
    finally:
        db.close()


@celery_app.task
def sync_trade_hub_markets():
    """
    Sync market data for all major trade hubs
    
    Runs every 10 minutes via Celery Beat
    """
    # Get region IDs for trade hubs
    # Jita is in The Forge (10000002)
    # Amarr is in Domain (10000043)
    # Dodixie is in Sinq Laison (10000032)
    # Rens is in Heimatar (10000030)
    # Hek is in Metropolis (10000042)
    
    trade_hub_regions = {
        "Jita": 10000002,  # The Forge
        "Amarr": 10000043,  # Domain
        "Dodixie": 10000032,  # Sinq Laison
        "Rens": 10000030,  # Heimatar
        "Hek": 10000042,  # Metropolis
    }
    
    synced_count = 0
    error_count = 0
    
    for hub_name, region_id in trade_hub_regions.items():
        try:
            result = sync_market_orders.delay(region_id)
            synced_count += 1
            logger.info(f"Queued market sync for {hub_name} (region {region_id})")
        except Exception as e:
            logger.error(f"Error queuing market sync for {hub_name}: {e}")
            error_count += 1
    
    logger.info(f"Queued {synced_count} market syncs, {error_count} errors")
    return {
        "queued": synced_count,
        "errors": error_count,
        "total": len(trade_hub_regions),
    }


@celery_app.task
def sync_price_history(type_id: int, region_id: int):
    """
    Sync price history for a specific item type in a region
    
    Args:
        type_id: Item type ID
        region_id: Region ID
    """
    db: Session = SessionLocal()
    
    try:
        # ESI endpoint: GET /markets/{region_id}/history/
        history_data = run_async(
            esi_client.request(
                "GET",
                f"/markets/{region_id}/history/",
                params={"type_id": type_id},
            )
        )
        
        # Process history data
        for day_data in history_data:
            date = datetime.fromisoformat(day_data.get("date", "").replace("Z", "+00:00"))
            
            # Check if already exists
            existing = db.query(PriceHistory).filter(
                and_(
                    PriceHistory.type_id == type_id,
                    PriceHistory.region_id == region_id,
                    PriceHistory.date == date,
                )
            ).first()
            
            if not existing:
                price_history = PriceHistory(
                    type_id=type_id,
                    region_id=region_id,
                    average_price=day_data.get("average"),
                    highest_price=day_data.get("highest"),
                    lowest_price=day_data.get("lowest"),
                    order_count=day_data.get("order_count"),
                    volume=day_data.get("volume"),
                    date=date,
                    price_data=day_data,
                )
                db.add(price_history)
        
        db.commit()
        logger.info(f"Synced price history for type {type_id} in region {region_id}")
        
        return {
            "success": True,
            "type_id": type_id,
            "region_id": region_id,
            "days_synced": len(history_data),
        }
        
    except ESIError as e:
        logger.error(f"Failed to sync price history: {e}")
        db.rollback()
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Error syncing price history: {e}")
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()

