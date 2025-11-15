"""
Analytics sync tasks
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List
from sqlalchemy import func
from celery import Task

from app.core.celery_app import celery_app
from app.core.database import get_db_session
from app.models.character import Character
from app.models.analytics import (
    ProfitLoss, IndustryProfitability, ISKFlow,
    PortfolioSnapshot, MarketTrend, TradingOpportunity
)
from app.models.wallet import WalletJournal, WalletTransaction
from app.models.industry import IndustryJob
from app.models.killmail import Killmail
from app.models.market import MarketOrder
from app.services.esi_client import ESIClient
from app.websockets.publisher import publish_event
from app.websockets.events import EventType
from app.core.logger import logger


def run_async(coro):
    """Helper to run async code in Celery tasks"""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def calculate_profit_loss(self: Task, character_id: int, days: int = 30):
    """
    Calculate profit and loss for a character based on wallet data
    """
    try:
        db = next(get_db_session())
        character = db.query(Character).filter(Character.id == character_id).first()

        if not character:
            logger.error(f"Character {character_id} not found")
            return

        # Calculate for each day in the period
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        current_date = cutoff_date.date()
        end_date = datetime.utcnow().date()

        while current_date <= end_date:
            day_start = datetime.combine(current_date, datetime.min.time())
            day_end = datetime.combine(current_date, datetime.max.time())

            # Get journal entries for the day
            journal_entries = db.query(WalletJournal).filter(
                WalletJournal.character_id == character_id,
                WalletJournal.date >= day_start,
                WalletJournal.date <= day_end
            ).all()

            # Calculate income by source
            bounty_income = sum(j.amount for j in journal_entries if j.amount > 0 and j.ref_type in ['bounty_prizes', 'bounty_prize'])
            mission_income = sum(j.amount for j in journal_entries if j.amount > 0 and j.ref_type in ['agent_mission_reward', 'agent_mission_time_bonus_reward'])
            market_income = sum(j.amount for j in journal_entries if j.amount > 0 and j.ref_type in ['market_escrow', 'market_escrow_released'])
            contract_income = sum(j.amount for j in journal_entries if j.amount > 0 and j.ref_type in ['contract_reward', 'contract_price'])
            industry_income = sum(j.amount for j in journal_entries if j.amount > 0 and j.ref_type in ['industry_job_tax', 'manufacturing'])

            other_income = sum(j.amount for j in journal_entries if j.amount > 0 and j.ref_type not in [
                'bounty_prizes', 'bounty_prize', 'agent_mission_reward', 'agent_mission_time_bonus_reward',
                'market_escrow', 'market_escrow_released', 'contract_reward', 'contract_price',
                'industry_job_tax', 'manufacturing'
            ])

            total_income = bounty_income + mission_income + market_income + contract_income + industry_income + other_income

            # Calculate expenses
            market_expenses = abs(sum(j.amount for j in journal_entries if j.amount < 0 and j.ref_type in ['market_transaction']))
            contract_expenses = abs(sum(j.amount for j in journal_entries if j.amount < 0 and j.ref_type in ['contract_price', 'contract_collateral']))
            industry_expenses = abs(sum(j.amount for j in journal_entries if j.amount < 0 and j.ref_type in ['industry_job_tax', 'manufacturing']))

            # Ship losses from killmails
            ship_losses = 0
            killmails = db.query(Killmail).filter(
                Killmail.victim_character_id == character.character_id,
                Killmail.killmail_time >= day_start,
                Killmail.killmail_time <= day_end
            ).all()
            ship_losses = sum(k.total_value or 0 for k in killmails)

            other_expenses = abs(sum(j.amount for j in journal_entries if j.amount < 0 and j.ref_type not in [
                'market_transaction', 'contract_price', 'contract_collateral',
                'industry_job_tax', 'manufacturing'
            ]))

            total_expenses = market_expenses + contract_expenses + industry_expenses + ship_losses + other_expenses

            # Net profit
            net_profit = total_income - total_expenses

            # Transaction stats
            transaction_count = len(journal_entries)
            largest_income = max((j.amount for j in journal_entries if j.amount > 0), default=0)
            largest_expense = abs(min((j.amount for j in journal_entries if j.amount < 0), default=0))

            # Update or create ProfitLoss record
            pl_record = db.query(ProfitLoss).filter(
                ProfitLoss.character_id == character_id,
                func.date(ProfitLoss.date) == current_date
            ).first()

            if pl_record:
                pl_record.bounty_income = bounty_income
                pl_record.mission_income = mission_income
                pl_record.market_income = market_income
                pl_record.contract_income = contract_income
                pl_record.industry_income = industry_income
                pl_record.other_income = other_income
                pl_record.total_income = total_income
                pl_record.market_expenses = market_expenses
                pl_record.contract_expenses = contract_expenses
                pl_record.industry_expenses = industry_expenses
                pl_record.ship_losses = ship_losses
                pl_record.other_expenses = other_expenses
                pl_record.total_expenses = total_expenses
                pl_record.net_profit = net_profit
                pl_record.transaction_count = transaction_count
                pl_record.largest_income = largest_income
                pl_record.largest_expense = largest_expense
            else:
                pl_record = ProfitLoss(
                    character_id=character_id,
                    date=day_start,
                    bounty_income=bounty_income,
                    mission_income=mission_income,
                    market_income=market_income,
                    contract_income=contract_income,
                    industry_income=industry_income,
                    other_income=other_income,
                    total_income=total_income,
                    market_expenses=market_expenses,
                    contract_expenses=contract_expenses,
                    industry_expenses=industry_expenses,
                    ship_losses=ship_losses,
                    other_expenses=other_expenses,
                    total_expenses=total_expenses,
                    net_profit=net_profit,
                    transaction_count=transaction_count,
                    largest_income=largest_income,
                    largest_expense=largest_expense
                )
                db.add(pl_record)

            current_date += timedelta(days=1)

        db.commit()

        # Publish WebSocket event
        publish_event(EventType.ANALYTICS_UPDATE, {
            "character_id": character_id,
            "type": "profit_loss",
            "period_days": days
        })

        logger.info(f"Calculated profit/loss for character {character_id} for {days} days")

    except Exception as e:
        logger.error(f"Failed to calculate profit/loss for character {character_id}: {str(e)}")
        db.rollback()
        raise self.retry(exc=e)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def aggregate_isk_flow(self: Task, character_id: int, days: int = 30):
    """
    Aggregate ISK flow from wallet transactions and journal entries
    """
    try:
        db = next(get_db_session())
        character = db.query(Character).filter(Character.id == character_id).first()

        if not character:
            logger.error(f"Character {character_id} not found")
            return

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Delete existing flow records for the period
        db.query(ISKFlow).filter(
            ISKFlow.character_id == character_id,
            ISKFlow.date >= cutoff_date
        ).delete()

        # Process journal entries
        journal_entries = db.query(WalletJournal).filter(
            WalletJournal.character_id == character_id,
            WalletJournal.date >= cutoff_date
        ).all()

        for entry in journal_entries:
            # Determine flow type and category
            flow_type = "income" if entry.amount > 0 else "expense"
            category = categorize_ref_type(entry.ref_type)

            flow_record = ISKFlow(
                character_id=character_id,
                transaction_id=entry.id,
                date=entry.date,
                amount=abs(entry.amount),
                flow_type=flow_type,
                category=category,
                description=entry.description,
                ref_type=entry.ref_type
            )
            db.add(flow_record)

        db.commit()

        # Publish WebSocket event
        publish_event(EventType.ANALYTICS_UPDATE, {
            "character_id": character_id,
            "type": "isk_flow",
            "period_days": days
        })

        logger.info(f"Aggregated ISK flow for character {character_id} for {days} days")

    except Exception as e:
        logger.error(f"Failed to aggregate ISK flow for character {character_id}: {str(e)}")
        db.rollback()
        raise self.retry(exc=e)
    finally:
        db.close()


def categorize_ref_type(ref_type: str) -> str:
    """Categorize wallet ref_type into simplified categories"""
    category_map = {
        'bounty_prizes': 'bounty',
        'bounty_prize': 'bounty',
        'agent_mission_reward': 'mission',
        'agent_mission_time_bonus_reward': 'mission',
        'market_escrow': 'market',
        'market_escrow_released': 'market',
        'market_transaction': 'market',
        'contract_reward': 'contract',
        'contract_price': 'contract',
        'contract_collateral': 'contract',
        'industry_job_tax': 'industry',
        'manufacturing': 'industry',
        'insurance': 'insurance',
        'skill_purchase': 'training',
    }
    return category_map.get(ref_type, 'other')


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def calculate_industry_profitability(self: Task, character_id: int):
    """
    Calculate profitability for industry jobs
    """
    try:
        db = next(get_db_session())
        esi_client = ESIClient()

        character = db.query(Character).filter(Character.id == character_id).first()
        if not character:
            logger.error(f"Character {character_id} not found")
            return

        # Get recent industry jobs
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        jobs = db.query(IndustryJob).filter(
            IndustryJob.character_id == character_id,
            IndustryJob.start_date >= cutoff_date,
            IndustryJob.status.in_(['active', 'ready', 'delivered'])
        ).all()

        for job in jobs:
            # Check if profitability already calculated
            existing = db.query(IndustryProfitability).filter(
                IndustryProfitability.job_id == job.id
            ).first()

            if existing:
                continue

            # Calculate costs
            material_cost = 0  # Would need to fetch blueprint requirements and market prices
            installation_cost = job.cost or 0
            tax_cost = 0
            time_cost = 0

            if job.duration:
                # Estimate time value at 10M ISK/hour
                time_cost = (job.duration / 3600) * 10_000_000

            total_cost = material_cost + installation_cost + tax_cost + time_cost

            # Get estimated revenue from market price
            try:
                market_price_data = run_async(
                    esi_client.request("GET", f"/markets/prices/")
                )
                product_price = next(
                    (p['average_price'] for p in market_price_data if p['type_id'] == job.product_type_id),
                    0
                )
                estimated_revenue = int(product_price * (job.runs or 1))
            except:
                estimated_revenue = 0

            estimated_profit = estimated_revenue - total_cost
            estimated_margin = (estimated_profit / total_cost * 100) if total_cost > 0 else 0

            # Calculate ISK per hour
            isk_per_hour = 0
            if job.duration and job.duration > 0:
                isk_per_hour = int((estimated_profit / job.duration) * 3600)

            # Create profitability record
            prof_record = IndustryProfitability(
                character_id=character_id,
                job_id=job.id,
                product_type_id=job.product_type_id,
                product_quantity=job.runs or 1,
                blueprint_type_id=job.blueprint_type_id,
                material_cost=material_cost,
                installation_cost=installation_cost,
                tax_cost=tax_cost,
                time_cost=time_cost,
                total_cost=total_cost,
                estimated_revenue=estimated_revenue,
                estimated_profit=estimated_profit,
                estimated_margin_percent=estimated_margin,
                job_type=job.activity,
                run_count=job.runs or 1,
                duration_seconds=job.duration,
                isk_per_hour=isk_per_hour
            )
            db.add(prof_record)

        db.commit()

        # Publish WebSocket event
        publish_event(EventType.ANALYTICS_UPDATE, {
            "character_id": character_id,
            "type": "industry_profitability",
            "jobs_analyzed": len(jobs)
        })

        logger.info(f"Calculated industry profitability for character {character_id}")

    except Exception as e:
        logger.error(f"Failed to calculate industry profitability for character {character_id}: {str(e)}")
        db.rollback()
        raise self.retry(exc=e)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def calculate_market_trends(self: Task, type_id: int, region_id: int = 10000002):
    """
    Calculate market price trends for an item
    """
    try:
        db = next(get_db_session())
        esi_client = ESIClient()

        # Fetch market history from ESI
        history_data = run_async(
            esi_client.request("GET", f"/markets/{region_id}/history/", params={"type_id": type_id})
        )

        if not history_data:
            logger.warning(f"No market history data for type {type_id} in region {region_id}")
            return

        # Process last 30 days
        cutoff_date = datetime.utcnow() - timedelta(days=30)

        for day_data in history_data[-30:]:
            date = datetime.strptime(day_data['date'], '%Y-%m-%d')

            if date < cutoff_date:
                continue

            # Calculate trend direction
            trend_direction = "stable"
            price_change = 0

            # Get previous day's record
            prev_record = db.query(MarketTrend).filter(
                MarketTrend.type_id == type_id,
                MarketTrend.region_id == region_id,
                MarketTrend.date < date
            ).order_by(MarketTrend.date.desc()).first()

            if prev_record and prev_record.average_price:
                price_change = ((day_data['average'] - prev_record.average_price) / prev_record.average_price * 100)
                if price_change > 1:
                    trend_direction = "up"
                elif price_change < -1:
                    trend_direction = "down"

            # Update or create trend record
            trend_record = db.query(MarketTrend).filter(
                MarketTrend.type_id == type_id,
                MarketTrend.region_id == region_id,
                func.date(MarketTrend.date) == date.date()
            ).first()

            if trend_record:
                trend_record.average_price = day_data['average']
                trend_record.highest_price = day_data['highest']
                trend_record.lowest_price = day_data['lowest']
                trend_record.volume = day_data['volume']
                trend_record.order_count = day_data['order_count']
                trend_record.price_change_percent = price_change
                trend_record.trend_direction = trend_direction
            else:
                trend_record = MarketTrend(
                    type_id=type_id,
                    region_id=region_id,
                    date=date,
                    average_price=day_data['average'],
                    highest_price=day_data['highest'],
                    lowest_price=day_data['lowest'],
                    volume=day_data['volume'],
                    order_count=day_data['order_count'],
                    price_change_percent=price_change,
                    trend_direction=trend_direction
                )
                db.add(trend_record)

        db.commit()
        logger.info(f"Calculated market trends for type {type_id} in region {region_id}")

    except Exception as e:
        logger.error(f"Failed to calculate market trends for type {type_id}: {str(e)}")
        db.rollback()
        raise self.retry(exc=e)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def find_trading_opportunities(self: Task, region_id: int = 10000002):
    """
    Find trading opportunities by analyzing market data
    """
    try:
        db = next(get_db_session())
        esi_client = ESIClient()

        # Get all market orders for the region
        orders_data = run_async(
            esi_client.request("GET", f"/markets/{region_id}/orders/", params={"order_type": "all"})
        )

        if not orders_data:
            return

        # Group orders by type_id
        buy_orders = {}
        sell_orders = {}

        for order in orders_data:
            type_id = order['type_id']

            if order['is_buy_order']:
                if type_id not in buy_orders or order['price'] > buy_orders[type_id]['price']:
                    buy_orders[type_id] = order
            else:
                if type_id not in sell_orders or order['price'] < sell_orders[type_id]['price']:
                    sell_orders[type_id] = order

        # Find opportunities (items with buy price > sell price in different locations)
        opportunities_found = 0

        for type_id in set(buy_orders.keys()) & set(sell_orders.keys()):
            buy_order = buy_orders[type_id]
            sell_order = sell_orders[type_id]

            # Skip if same location
            if buy_order['location_id'] == sell_order['location_id']:
                continue

            # Calculate profit
            profit_per_unit = buy_order['price'] - sell_order['price']

            if profit_per_unit <= 0:
                continue

            profit_margin = (profit_per_unit / sell_order['price']) * 100

            # Only consider opportunities with > 5% margin
            if profit_margin < 5:
                continue

            potential_volume = min(buy_order['volume_remain'], sell_order['volume_remain'])
            total_profit = int(profit_per_unit * potential_volume)
            required_capital = int(sell_order['price'] * potential_volume)

            # Create or update opportunity
            opp = TradingOpportunity(
                type_id=type_id,
                buy_location_id=buy_order['location_id'],
                buy_region_id=region_id,
                sell_location_id=sell_order['location_id'],
                sell_region_id=region_id,
                buy_price=buy_order['price'],
                sell_price=sell_order['price'],
                profit_per_unit=profit_per_unit,
                profit_margin_percent=profit_margin,
                potential_volume=potential_volume,
                total_profit_potential=total_profit,
                required_capital=required_capital,
                risk_level="medium",
                is_active=True,
                expires_at=datetime.utcnow() + timedelta(hours=24)
            )
            db.add(opp)
            opportunities_found += 1

        # Deactivate old opportunities
        db.query(TradingOpportunity).filter(
            TradingOpportunity.expires_at < datetime.utcnow()
        ).update({"is_active": False})

        db.commit()
        logger.info(f"Found {opportunities_found} trading opportunities in region {region_id}")

    except Exception as e:
        logger.error(f"Failed to find trading opportunities in region {region_id}: {str(e)}")
        db.rollback()
        raise self.retry(exc=e)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def create_portfolio_snapshot(self: Task, character_id: int):
    """
    Create a daily portfolio snapshot for net worth tracking
    """
    try:
        db = next(get_db_session())

        character = db.query(Character).filter(Character.id == character_id).first()
        if not character:
            logger.error(f"Character {character_id} not found")
            return

        # Get wallet balance from latest journal entry
        latest_journal = db.query(WalletJournal).filter(
            WalletJournal.character_id == character_id
        ).order_by(WalletJournal.date.desc()).first()

        wallet_balance = latest_journal.balance if latest_journal else 0

        # Calculate asset values (simplified - would need actual asset data)
        total_assets = 0  # Would sum up all character assets with market prices

        # Get sell orders value
        sell_orders = db.query(MarketOrder).filter(
            MarketOrder.character_id == character_id,
            MarketOrder.is_buy_order == False
        ).all()
        sell_orders_value = sum(o.price * o.volume_remain for o in sell_orders)

        # Total net worth
        total_net_worth = wallet_balance + total_assets + sell_orders_value

        # Get previous snapshot for comparison
        prev_snapshot = db.query(PortfolioSnapshot).filter(
            PortfolioSnapshot.character_id == character_id
        ).order_by(PortfolioSnapshot.snapshot_date.desc()).first()

        net_worth_change = 0
        net_worth_change_percent = 0

        if prev_snapshot:
            net_worth_change = total_net_worth - prev_snapshot.total_net_worth
            if prev_snapshot.total_net_worth > 0:
                net_worth_change_percent = (net_worth_change / prev_snapshot.total_net_worth) * 100

        # Create snapshot
        snapshot = PortfolioSnapshot(
            character_id=character_id,
            snapshot_date=datetime.utcnow(),
            wallet_balance=wallet_balance,
            total_assets_value=total_assets,
            sell_orders_value=sell_orders_value,
            total_net_worth=total_net_worth,
            net_worth_change=net_worth_change,
            net_worth_change_percent=net_worth_change_percent
        )
        db.add(snapshot)
        db.commit()

        # Publish WebSocket event
        publish_event(EventType.ANALYTICS_UPDATE, {
            "character_id": character_id,
            "type": "portfolio_snapshot",
            "net_worth": total_net_worth
        })

        logger.info(f"Created portfolio snapshot for character {character_id}")

    except Exception as e:
        logger.error(f"Failed to create portfolio snapshot for character {character_id}: {str(e)}")
        db.rollback()
        raise self.retry(exc=e)
    finally:
        db.close()
