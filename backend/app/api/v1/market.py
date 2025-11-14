"""
Market endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from typing import Optional, List
from datetime import datetime, timedelta
from pydantic import BaseModel
import logging

from app.core.database import get_db
from app.models.market import MarketOrder, PriceHistory
from app.tasks.market_sync import sync_market_orders, sync_price_history

logger = logging.getLogger(__name__)

router = APIRouter()


class MarketOrderResponse(BaseModel):
    """Market order response model"""
    id: int
    order_id: int
    type_id: int
    type_name: Optional[str]
    is_buy_order: bool
    location_id: int
    location_type: Optional[str]
    location_name: Optional[str]
    region_id: Optional[int]
    region_name: Optional[str]
    system_id: Optional[int]
    system_name: Optional[str]
    price: float
    volume_total: int
    volume_remain: int
    min_volume: Optional[int]
    duration: Optional[int]
    issued: datetime
    expires: Optional[datetime]
    is_active: bool
    range_type: Optional[str]
    range_value: Optional[int]
    
    class Config:
        from_attributes = True


class PriceHistoryResponse(BaseModel):
    """Price history response model"""
    id: int
    type_id: int
    type_name: Optional[str]
    region_id: int
    region_name: Optional[str]
    average_price: Optional[float]
    highest_price: Optional[float]
    lowest_price: Optional[float]
    order_count: Optional[int]
    volume: Optional[int]
    date: datetime
    
    class Config:
        from_attributes = True


@router.get("/orders")
async def get_orders(
    region_id: Optional[int] = Query(None, description="Filter by region ID"),
    system_id: Optional[int] = Query(None, description="Filter by system ID"),
    type_id: Optional[int] = Query(None, description="Filter by item type ID"),
    is_buy_order: Optional[bool] = Query(None, description="Filter by order type (true=buy, false=sell)"),
    location_id: Optional[int] = Query(None, description="Filter by location ID"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """
    Get market orders with filters
    
    Supports filtering by region, system, type, order type, location, and price range
    """
    try:
        query = db.query(MarketOrder).filter(MarketOrder.is_active == True)
        
        # Apply filters
        if region_id:
            query = query.filter(MarketOrder.region_id == region_id)
        
        if system_id:
            query = query.filter(MarketOrder.system_id == system_id)
        
        if type_id:
            query = query.filter(MarketOrder.type_id == type_id)
        
        if is_buy_order is not None:
            query = query.filter(MarketOrder.is_buy_order == is_buy_order)
        
        if location_id:
            query = query.filter(MarketOrder.location_id == location_id)
        
        if min_price is not None:
            query = query.filter(MarketOrder.price >= min_price)
        
        if max_price is not None:
            query = query.filter(MarketOrder.price <= max_price)
        
        # Order by price (ascending for buy orders, descending for sell orders)
        if is_buy_order:
            query = query.order_by(desc(MarketOrder.price))
        else:
            query = query.order_by(MarketOrder.price)
        
        orders = query.offset(skip).limit(limit).all()
        total = query.count()
        
        return {
            "items": orders,
            "total": total,
            "skip": skip,
            "limit": limit,
        }
        
    except Exception as e:
        logger.error(f"Error getting market orders: {e}")
        raise HTTPException(status_code=500, detail="Failed to get market orders")


@router.get("/prices/{type_id}")
async def get_prices(
    type_id: int,
    region_id: Optional[int] = Query(None, description="Filter by region ID"),
    system_id: Optional[int] = Query(None, description="Filter by system ID"),
    db: Session = Depends(get_db),
):
    """
    Get current market prices for an item type
    
    Returns best buy and sell orders
    """
    try:
        query = db.query(MarketOrder).filter(
            and_(
                MarketOrder.type_id == type_id,
                MarketOrder.is_active == True,
            )
        )
        
        if region_id:
            query = query.filter(MarketOrder.region_id == region_id)
        
        if system_id:
            query = query.filter(MarketOrder.system_id == system_id)
        
        # Get best buy order (highest price)
        best_buy = query.filter(MarketOrder.is_buy_order == True).order_by(
            desc(MarketOrder.price)
        ).first()
        
        # Get best sell order (lowest price)
        best_sell = query.filter(MarketOrder.is_buy_order == False).order_by(
            MarketOrder.price
        ).first()
        
        # Get all orders for statistics
        all_orders = query.all()
        buy_orders = [o for o in all_orders if o.is_buy_order]
        sell_orders = [o for o in all_orders if not o.is_buy_order]
        
        return {
            "type_id": type_id,
            "region_id": region_id,
            "system_id": system_id,
            "best_buy": {
                "price": best_buy.price if best_buy else None,
                "volume_remain": best_buy.volume_remain if best_buy else None,
                "location_id": best_buy.location_id if best_buy else None,
            },
            "best_sell": {
                "price": best_sell.price if best_sell else None,
                "volume_remain": best_sell.volume_remain if best_sell else None,
                "location_id": best_sell.location_id if best_sell else None,
            },
            "statistics": {
                "total_orders": len(all_orders),
                "buy_orders": len(buy_orders),
                "sell_orders": len(sell_orders),
                "average_buy_price": sum(o.price for o in buy_orders) / len(buy_orders) if buy_orders else None,
                "average_sell_price": sum(o.price for o in sell_orders) / len(sell_orders) if sell_orders else None,
                "total_buy_volume": sum(o.volume_remain for o in buy_orders),
                "total_sell_volume": sum(o.volume_remain for o in sell_orders),
            },
        }
        
    except Exception as e:
        logger.error(f"Error getting prices for type {type_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get prices")


@router.get("/history/{type_id}")
async def get_history(
    type_id: int,
    region_id: int = Query(..., description="Region ID"),
    days: int = Query(30, ge=1, le=365, description="Number of days of history"),
    db: Session = Depends(get_db),
):
    """
    Get price history for an item type in a region
    
    Args:
        type_id: Item type ID
        region_id: Region ID
        days: Number of days of history to return
        db: Database session
    """
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        history = db.query(PriceHistory).filter(
            and_(
                PriceHistory.type_id == type_id,
                PriceHistory.region_id == region_id,
                PriceHistory.date >= start_date,
                PriceHistory.date <= end_date,
            )
        ).order_by(PriceHistory.date).all()
        
        # If no history, trigger sync
        if not history:
            sync_price_history.delay(type_id, region_id)
            return {
                "message": "No price history found. Sync has been queued.",
                "type_id": type_id,
                "region_id": region_id,
                "items": [],
            }
        
        return {
            "type_id": type_id,
            "region_id": region_id,
            "days": days,
            "items": history,
            "total": len(history),
        }
        
    except Exception as e:
        logger.error(f"Error getting price history: {e}")
        raise HTTPException(status_code=500, detail="Failed to get price history")


@router.get("/compare")
async def compare_prices(
    type_id: int = Query(..., description="Item type ID"),
    region_ids: Optional[str] = Query(None, description="Comma-separated region IDs"),
    db: Session = Depends(get_db),
):
    """
    Compare prices across multiple regions
    
    Args:
        type_id: Item type ID
        region_ids: Comma-separated list of region IDs (defaults to major trade hubs)
        db: Database session
    """
    try:
        # Default to major trade hub regions
        if not region_ids:
            region_ids_list = [10000002, 10000043, 10000032, 10000030, 10000042]  # Jita, Amarr, Dodixie, Rens, Hek
        else:
            region_ids_list = [int(r.strip()) for r in region_ids.split(",")]
        
        comparison = []
        
        for region_id in region_ids_list:
            # Get best prices
            best_buy = db.query(MarketOrder).filter(
                and_(
                    MarketOrder.type_id == type_id,
                    MarketOrder.region_id == region_id,
                    MarketOrder.is_buy_order == True,
                    MarketOrder.is_active == True,
                )
            ).order_by(desc(MarketOrder.price)).first()
            
            best_sell = db.query(MarketOrder).filter(
                and_(
                    MarketOrder.type_id == type_id,
                    MarketOrder.region_id == region_id,
                    MarketOrder.is_buy_order == False,
                    MarketOrder.is_active == True,
                )
            ).order_by(MarketOrder.price).first()
            
            comparison.append({
                "region_id": region_id,
                "best_buy_price": best_buy.price if best_buy else None,
                "best_sell_price": best_sell.price if best_sell else None,
                "spread": (best_sell.price - best_buy.price) if (best_buy and best_sell) else None,
            })
        
        return {
            "type_id": type_id,
            "comparison": comparison,
        }
        
    except Exception as e:
        logger.error(f"Error comparing prices: {e}")
        raise HTTPException(status_code=500, detail="Failed to compare prices")
