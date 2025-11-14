"""
Market data backfill tasks

Backfills existing market orders with type names, location names, system names, and region names
"""
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_
import logging
import asyncio

from app.core.database import SessionLocal
from app.core.celery_app import celery_app
from app.models.market import MarketOrder
from app.services.esi_client import esi_client, ESIError
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
def backfill_market_order_names(self, batch_size: int = 100):
    """
    Backfill type names, location names, system names, and region names for existing market orders
    
    Args:
        batch_size: Number of orders to process per batch
    """
    db: Session = SessionLocal()
    updated_count = 0
    error_count = 0
    
    try:
        # Get orders missing type_name or location_name
        orders_to_update = db.query(MarketOrder).filter(
            and_(
                MarketOrder.is_active == True,
                # Update orders that are missing type_name OR location_name
                (
                    (MarketOrder.type_name.is_(None)) |
                    (MarketOrder.location_name.is_(None)) |
                    (MarketOrder.system_name.is_(None))
                )
            )
        ).limit(batch_size).all()
        
        if not orders_to_update:
            logger.info("No market orders need backfilling")
            return {
                "success": True,
                "updated": 0,
                "errors": 0,
                "message": "No orders need backfilling"
            }
        
        logger.info(f"Backfilling {len(orders_to_update)} market orders")
        
        # Collect unique type_ids and location_ids
        unique_type_ids = set()
        unique_location_ids = set()
        
        for order in orders_to_update:
            if order.type_id:
                unique_type_ids.add(order.type_id)
            if order.location_id:
                unique_location_ids.add(order.location_id)
        
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
                    location_info = run_async(esi_client.get_location_info(loc_id))
                    location_info_map[loc_id] = location_info
                except Exception as e:
                    logger.warning(f"Failed to fetch location info for {loc_id}: {e}")
                    location_info_map[loc_id] = {"name": f"Location {loc_id}"}
            logger.info(f"Fetched location information for {len(location_info_map)} locations")
        
        # Update orders
        for order in orders_to_update:
            try:
                # Update type name
                if order.type_id and order.type_id in type_info_map:
                    type_info = type_info_map[order.type_id]
                    order.type_name = type_info.get("name")
                
                # Update location name and system/region info
                if order.location_id and order.location_id in location_info_map:
                    loc_info = location_info_map[order.location_id]
                    order.location_name = loc_info.get("name")
                    
                    system_id_from_location = loc_info.get("system_id") or loc_info.get("solar_system_id")
                    if system_id_from_location:
                        order.system_id = system_id_from_location
                    if loc_info.get("system_name"):
                        order.system_name = loc_info.get("system_name")
                    if loc_info.get("region_name"):
                        order.region_name = loc_info.get("region_name")
                
                order.last_synced_at = datetime.now(timezone.utc)
                updated_count += 1
                
            except Exception as e:
                logger.warning(f"Failed to update order {order.order_id}: {e}")
                error_count += 1
                continue
        
        db.commit()
        logger.info(f"Backfilled {updated_count} market orders, {error_count} errors")
        
        return {
            "success": True,
            "updated": updated_count,
            "errors": error_count,
            "total_processed": len(orders_to_update),
        }
        
    except Exception as e:
        logger.error(f"Error backfilling market orders: {e}")
        db.rollback()
        raise self.retry(exc=e)
    finally:
        db.close()

