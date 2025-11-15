"""
Analytics API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.analytics import (
    MarketTrend, ProfitLoss, IndustryProfitability,
    ISKFlow, PortfolioSnapshot, TradingOpportunity
)
from app.tasks.analytics_sync import (
    calculate_profit_loss, calculate_industry_profitability,
    aggregate_isk_flow, calculate_market_trends, find_trading_opportunities,
    create_portfolio_snapshot
)

router = APIRouter()


# Pydantic models
class MarketTrendResponse(BaseModel):
    id: int
    type_id: int
    region_id: int
    date: datetime
    average_price: Optional[float]
    highest_price: Optional[float]
    lowest_price: Optional[float]
    median_price: Optional[float]
    volume: Optional[int]
    price_change_percent: Optional[float]
    trend_direction: Optional[str]

    class Config:
        from_attributes = True


class ProfitLossResponse(BaseModel):
    id: int
    character_id: int
    date: datetime
    total_income: int
    total_expenses: int
    net_profit: int
    bounty_income: int
    mission_income: int
    market_income: int
    contract_income: int
    industry_income: int
    market_expenses: int
    ship_losses: int

    class Config:
        from_attributes = True


class IndustryProfitabilityResponse(BaseModel):
    id: int
    character_id: int
    product_type_id: int
    product_quantity: int
    blueprint_type_id: int
    total_cost: int
    estimated_revenue: int
    estimated_profit: int
    estimated_margin_percent: float
    job_type: Optional[str]
    isk_per_hour: int

    class Config:
        from_attributes = True


class ISKFlowResponse(BaseModel):
    id: int
    character_id: int
    date: datetime
    amount: int
    flow_type: str
    category: str
    description: Optional[str]

    class Config:
        from_attributes = True


class PortfolioSnapshotResponse(BaseModel):
    id: int
    character_id: int
    snapshot_date: datetime
    wallet_balance: int
    total_assets_value: int
    total_net_worth: int
    net_worth_change: int
    net_worth_change_percent: float

    class Config:
        from_attributes = True


class TradingOpportunityResponse(BaseModel):
    id: int
    type_id: int
    buy_location_id: int
    sell_location_id: int
    buy_price: float
    sell_price: float
    profit_per_unit: float
    profit_margin_percent: float
    potential_volume: int
    required_capital: int
    jumps: Optional[int]
    risk_level: Optional[str]

    class Config:
        from_attributes = True


class ProfitLossSummary(BaseModel):
    total_income: int
    total_expenses: int
    net_profit: int
    income_by_source: Dict[str, int]
    expenses_by_source: Dict[str, int]
    daily_average: int
    best_day: Optional[datetime]
    best_day_profit: int


class MarketTrendSummary(BaseModel):
    type_id: int
    current_price: float
    price_change_7d: float
    price_change_30d: float
    volume_7d: int
    volume_30d: int
    trend_direction: str
    volatility: str


class IndustryProfitabilitySummary(BaseModel):
    total_jobs: int
    profitable_jobs: int
    total_profit: int
    average_margin: float
    best_product_type_id: int
    best_product_margin: float


# ============= Profit/Loss Endpoints =============

@router.get("/profit-loss", response_model=List[ProfitLossResponse])
async def list_profit_loss(
    character_id: int,
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List profit/loss records for a character
    """
    query = db.query(ProfitLoss).filter(ProfitLoss.character_id == character_id)

    if start_date:
        query = query.filter(ProfitLoss.date >= start_date)
    if end_date:
        query = query.filter(ProfitLoss.date <= end_date)

    records = query.order_by(ProfitLoss.date.desc()).offset(offset).limit(limit).all()
    return records


@router.get("/profit-loss/summary", response_model=ProfitLossSummary)
async def get_profit_loss_summary(
    character_id: int,
    days: int = Query(30, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get profit/loss summary for a character
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    records = db.query(ProfitLoss).filter(
        ProfitLoss.character_id == character_id,
        ProfitLoss.date >= cutoff_date
    ).all()

    if not records:
        return {
            "total_income": 0,
            "total_expenses": 0,
            "net_profit": 0,
            "income_by_source": {},
            "expenses_by_source": {},
            "daily_average": 0,
            "best_day": None,
            "best_day_profit": 0
        }

    total_income = sum(r.total_income for r in records)
    total_expenses = sum(r.total_expenses for r in records)
    net_profit = total_income - total_expenses

    # Income breakdown
    income_by_source = {
        "bounty": sum(r.bounty_income for r in records),
        "mission": sum(r.mission_income for r in records),
        "market": sum(r.market_income for r in records),
        "contract": sum(r.contract_income for r in records),
        "industry": sum(r.industry_income for r in records),
        "other": sum(r.other_income for r in records),
    }

    # Expenses breakdown
    expenses_by_source = {
        "market": sum(r.market_expenses for r in records),
        "contract": sum(r.contract_expenses for r in records),
        "industry": sum(r.industry_expenses for r in records),
        "ship_losses": sum(r.ship_losses for r in records),
        "other": sum(r.other_expenses for r in records),
    }

    # Best day
    best_record = max(records, key=lambda r: r.net_profit)

    return {
        "total_income": total_income,
        "total_expenses": total_expenses,
        "net_profit": net_profit,
        "income_by_source": income_by_source,
        "expenses_by_source": expenses_by_source,
        "daily_average": net_profit // max(days, 1),
        "best_day": best_record.date,
        "best_day_profit": best_record.net_profit
    }


@router.post("/profit-loss/calculate/{character_id}")
async def trigger_profit_loss_calculation(
    character_id: int,
    days: int = Query(30, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Trigger profit/loss calculation for a character
    """
    calculate_profit_loss.delay(character_id, days)
    return {"message": "Profit/loss calculation started"}


# ============= ISK Flow Endpoints =============

@router.get("/isk-flow", response_model=List[ISKFlowResponse])
async def list_isk_flow(
    character_id: int,
    flow_type: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List ISK flow records for a character
    """
    query = db.query(ISKFlow).filter(ISKFlow.character_id == character_id)

    if flow_type:
        query = query.filter(ISKFlow.flow_type == flow_type)
    if category:
        query = query.filter(ISKFlow.category == category)
    if start_date:
        query = query.filter(ISKFlow.date >= start_date)
    if end_date:
        query = query.filter(ISKFlow.date <= end_date)

    records = query.order_by(ISKFlow.date.desc()).offset(offset).limit(limit).all()
    return records


@router.get("/isk-flow/summary")
async def get_isk_flow_summary(
    character_id: int,
    days: int = Query(30, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get ISK flow summary with category breakdown
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    flows = db.query(ISKFlow).filter(
        ISKFlow.character_id == character_id,
        ISKFlow.date >= cutoff_date
    ).all()

    # Group by category
    income_by_category = {}
    expense_by_category = {}

    for flow in flows:
        amount = flow.amount
        category = flow.category

        if flow.flow_type == "income":
            income_by_category[category] = income_by_category.get(category, 0) + amount
        else:
            expense_by_category[category] = expense_by_category.get(category, 0) + amount

    return {
        "total_income": sum(income_by_category.values()),
        "total_expenses": sum(expense_by_category.values()),
        "income_by_category": income_by_category,
        "expense_by_category": expense_by_category,
        "net_flow": sum(income_by_category.values()) - sum(expense_by_category.values())
    }


@router.post("/isk-flow/aggregate/{character_id}")
async def trigger_isk_flow_aggregation(
    character_id: int,
    days: int = Query(30, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Trigger ISK flow aggregation from wallet data
    """
    aggregate_isk_flow.delay(character_id, days)
    return {"message": "ISK flow aggregation started"}


# ============= Industry Profitability Endpoints =============

@router.get("/industry/profitability", response_model=List[IndustryProfitabilityResponse])
async def list_industry_profitability(
    character_id: int,
    job_type: Optional[str] = Query(None),
    product_type_id: Optional[int] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List industry profitability calculations
    """
    query = db.query(IndustryProfitability).filter(
        IndustryProfitability.character_id == character_id
    )

    if job_type:
        query = query.filter(IndustryProfitability.job_type == job_type)
    if product_type_id:
        query = query.filter(IndustryProfitability.product_type_id == product_type_id)

    records = query.order_by(IndustryProfitability.calculated_at.desc()).offset(offset).limit(limit).all()
    return records


@router.get("/industry/profitability/summary", response_model=IndustryProfitabilitySummary)
async def get_industry_profitability_summary(
    character_id: int,
    days: int = Query(30, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get industry profitability summary
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    records = db.query(IndustryProfitability).filter(
        IndustryProfitability.character_id == character_id,
        IndustryProfitability.calculated_at >= cutoff_date
    ).all()

    if not records:
        return {
            "total_jobs": 0,
            "profitable_jobs": 0,
            "total_profit": 0,
            "average_margin": 0,
            "best_product_type_id": 0,
            "best_product_margin": 0
        }

    profitable_jobs = [r for r in records if r.estimated_profit > 0]
    total_profit = sum(r.estimated_profit for r in records)
    average_margin = sum(r.estimated_margin_percent for r in records) / len(records) if records else 0

    # Find best product
    best_product = max(records, key=lambda r: r.estimated_margin_percent) if records else None

    return {
        "total_jobs": len(records),
        "profitable_jobs": len(profitable_jobs),
        "total_profit": total_profit,
        "average_margin": average_margin,
        "best_product_type_id": best_product.product_type_id if best_product else 0,
        "best_product_margin": best_product.estimated_margin_percent if best_product else 0
    }


@router.post("/industry/profitability/calculate/{character_id}")
async def trigger_industry_profitability_calculation(
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Trigger industry profitability calculation
    """
    calculate_industry_profitability.delay(character_id)
    return {"message": "Industry profitability calculation started"}


# ============= Market Trends Endpoints =============

@router.get("/market/trends", response_model=List[MarketTrendResponse])
async def list_market_trends(
    type_id: int,
    region_id: int = Query(10000002),  # The Forge by default
    days: int = Query(30, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get market price trends for an item
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    trends = db.query(MarketTrend).filter(
        MarketTrend.type_id == type_id,
        MarketTrend.region_id == region_id,
        MarketTrend.date >= cutoff_date
    ).order_by(MarketTrend.date.asc()).all()

    return trends


@router.get("/market/trends/summary")
async def get_market_trend_summary(
    type_id: int,
    region_id: int = Query(10000002),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get market trend summary for an item
    """
    # Get trends for last 30 days
    cutoff_30d = datetime.utcnow() - timedelta(days=30)
    cutoff_7d = datetime.utcnow() - timedelta(days=7)

    trends_30d = db.query(MarketTrend).filter(
        MarketTrend.type_id == type_id,
        MarketTrend.region_id == region_id,
        MarketTrend.date >= cutoff_30d
    ).order_by(MarketTrend.date.desc()).all()

    trends_7d = [t for t in trends_30d if t.date >= cutoff_7d]

    if not trends_30d:
        raise HTTPException(status_code=404, detail="No trend data found")

    current = trends_30d[0]
    oldest_30d = trends_30d[-1]
    oldest_7d = trends_7d[-1] if trends_7d else current

    price_change_7d = ((current.average_price - oldest_7d.average_price) / oldest_7d.average_price * 100) if oldest_7d.average_price else 0
    price_change_30d = ((current.average_price - oldest_30d.average_price) / oldest_30d.average_price * 100) if oldest_30d.average_price else 0

    volume_7d = sum(t.volume or 0 for t in trends_7d)
    volume_30d = sum(t.volume or 0 for t in trends_30d)

    # Calculate volatility
    prices = [t.average_price for t in trends_30d if t.average_price]
    if len(prices) > 1:
        avg_price = sum(prices) / len(prices)
        variance = sum((p - avg_price) ** 2 for p in prices) / len(prices)
        volatility = (variance ** 0.5) / avg_price * 100
        volatility_label = "high" if volatility > 10 else "medium" if volatility > 5 else "low"
    else:
        volatility_label = "unknown"

    return {
        "type_id": type_id,
        "current_price": current.average_price,
        "price_change_7d": price_change_7d,
        "price_change_30d": price_change_30d,
        "volume_7d": volume_7d,
        "volume_30d": volume_30d,
        "trend_direction": current.trend_direction,
        "volatility": volatility_label
    }


@router.post("/market/trends/calculate")
async def trigger_market_trend_calculation(
    type_ids: List[int],
    region_id: int = Query(10000002),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Trigger market trend calculation for specific items
    """
    for type_id in type_ids[:100]:  # Limit to 100 items
        calculate_market_trends.delay(type_id, region_id)
    return {"message": f"Market trend calculation started for {len(type_ids[:100])} items"}


# ============= Trading Opportunities Endpoints =============

@router.get("/trading/opportunities", response_model=List[TradingOpportunityResponse])
async def list_trading_opportunities(
    min_profit_margin: float = Query(5.0, ge=0, le=100),
    max_capital: Optional[int] = Query(None),
    risk_level: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List trading opportunities
    """
    query = db.query(TradingOpportunity).filter(
        TradingOpportunity.is_active == True,
        TradingOpportunity.profit_margin_percent >= min_profit_margin
    )

    if max_capital:
        query = query.filter(TradingOpportunity.required_capital <= max_capital)
    if risk_level:
        query = query.filter(TradingOpportunity.risk_level == risk_level)

    opportunities = query.order_by(TradingOpportunity.profit_margin_percent.desc()).limit(limit).all()
    return opportunities


@router.post("/trading/opportunities/find")
async def trigger_find_trading_opportunities(
    region_ids: List[int],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Trigger trading opportunity discovery
    """
    for region_id in region_ids[:10]:  # Limit to 10 regions
        find_trading_opportunities.delay(region_id)
    return {"message": f"Trading opportunity discovery started for {len(region_ids[:10])} regions"}


# ============= Portfolio Endpoints =============

@router.get("/portfolio/snapshots", response_model=List[PortfolioSnapshotResponse])
async def list_portfolio_snapshots(
    character_id: int,
    days: int = Query(30, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List portfolio snapshots for net worth tracking
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    snapshots = db.query(PortfolioSnapshot).filter(
        PortfolioSnapshot.character_id == character_id,
        PortfolioSnapshot.snapshot_date >= cutoff_date
    ).order_by(PortfolioSnapshot.snapshot_date.desc()).all()

    return snapshots


@router.post("/portfolio/snapshot/{character_id}")
async def trigger_portfolio_snapshot(
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new portfolio snapshot
    """
    create_portfolio_snapshot.delay(character_id)
    return {"message": "Portfolio snapshot creation started"}


# ============= Analytics Dashboard =============

@router.get("/dashboard/{character_id}")
async def get_analytics_dashboard(
    character_id: int,
    days: int = Query(30, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get comprehensive analytics dashboard data
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # Profit/Loss summary
    pl_records = db.query(ProfitLoss).filter(
        ProfitLoss.character_id == character_id,
        ProfitLoss.date >= cutoff_date
    ).all()

    total_income = sum(r.total_income for r in pl_records) if pl_records else 0
    total_expenses = sum(r.total_expenses for r in pl_records) if pl_records else 0
    net_profit = total_income - total_expenses

    # Portfolio snapshot (latest)
    latest_snapshot = db.query(PortfolioSnapshot).filter(
        PortfolioSnapshot.character_id == character_id
    ).order_by(PortfolioSnapshot.snapshot_date.desc()).first()

    # Industry profitability
    industry_records = db.query(IndustryProfitability).filter(
        IndustryProfitability.character_id == character_id,
        IndustryProfitability.calculated_at >= cutoff_date
    ).all()

    industry_profit = sum(r.estimated_profit for r in industry_records) if industry_records else 0

    return {
        "character_id": character_id,
        "period_days": days,
        "profit_loss": {
            "total_income": total_income,
            "total_expenses": total_expenses,
            "net_profit": net_profit,
            "daily_average": net_profit // max(days, 1)
        },
        "portfolio": {
            "net_worth": latest_snapshot.total_net_worth if latest_snapshot else 0,
            "net_worth_change": latest_snapshot.net_worth_change if latest_snapshot else 0,
            "wallet_balance": latest_snapshot.wallet_balance if latest_snapshot else 0,
            "total_assets": latest_snapshot.total_assets_value if latest_snapshot else 0
        },
        "industry": {
            "total_jobs": len(industry_records),
            "total_profit": industry_profit,
            "average_margin": sum(r.estimated_margin_percent for r in industry_records) / len(industry_records) if industry_records else 0
        }
    }
