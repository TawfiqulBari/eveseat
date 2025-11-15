"""
Celery tasks module
"""
from app.core.celery_app import celery_app
from app.tasks.token_refresh import refresh_expired_tokens, refresh_token_for_character
from app.tasks.killmail_sync import (
    sync_killmails_from_esi,
    sync_killmail_from_zkillboard,
    subscribe_zkillboard_redisq,
)
from app.tasks.corporation_sync import (
    sync_corporation_data,
    sync_all_corporations,
)
from app.tasks.market_sync import (
    sync_market_orders,
    sync_trade_hub_markets,
    sync_price_history,
)
from app.tasks.market_backfill import backfill_market_order_names
from app.tasks.character_sync import (
    sync_character_assets,
    sync_character_market_orders,
    sync_character_details,
)
from app.tasks.mail_sync import (
    sync_character_mail,
    send_mail_task,
)
from app.tasks.contact_sync import sync_character_contacts
from app.tasks.calendar_sync import sync_character_calendar, respond_to_event_task
from app.tasks.contract_sync import sync_character_contracts
from app.tasks.wallet_sync import sync_character_wallet
from app.tasks.industry_sync import sync_character_industry
from app.tasks.blueprint_sync import sync_character_blueprints
from app.tasks.planetary_sync import sync_character_planets
from app.tasks.loyalty_sync import sync_character_loyalty
from app.tasks.fitting_sync import sync_character_fittings
from app.tasks.skill_sync import sync_character_skills
from app.tasks.clone_sync import sync_character_clones
from app.tasks.bookmark_sync import sync_character_bookmarks
from app.tasks.structure_sync import sync_corporation_structures
from app.tasks.moon_sync import sync_moon_extractions, sync_mining_ledger
from app.tasks.sovereignty_sync import sync_sovereignty_data
from app.tasks.analytics_sync import (
    calculate_profit_loss,
    aggregate_isk_flow,
    calculate_industry_profitability,
    calculate_market_trends,
    find_trading_opportunities,
    create_portfolio_snapshot,
)

# Import all tasks to ensure they're registered
__all__ = [
    "celery_app",
    "refresh_expired_tokens",
    "refresh_token_for_character",
    "sync_killmails_from_esi",
    "sync_killmail_from_zkillboard",
    "subscribe_zkillboard_redisq",
    "sync_corporation_data",
    "sync_all_corporations",
    "sync_market_orders",
    "sync_trade_hub_markets",
    "sync_price_history",
    "backfill_market_order_names",
    "sync_character_assets",
    "sync_character_market_orders",
    "sync_character_details",
    "sync_character_mail",
    "send_mail_task",
    "sync_character_contacts",
    "sync_character_calendar",
    "respond_to_event_task",
    "sync_character_contracts",
    "sync_character_wallet",
    "sync_character_industry",
    "sync_character_blueprints",
    "sync_character_planets",
    "sync_character_loyalty",
    "sync_character_fittings",
    "sync_character_skills",
    "sync_character_clones",
    "sync_character_bookmarks",
    "sync_corporation_structures",
    "sync_moon_extractions",
    "sync_mining_ledger",
    "sync_sovereignty_data",
    "calculate_profit_loss",
    "aggregate_isk_flow",
    "calculate_industry_profitability",
    "calculate_market_trends",
    "find_trading_opportunities",
    "create_portfolio_snapshot",
]

# Celery Beat schedule configuration
celery_app.conf.beat_schedule = {
    "refresh-expired-tokens": {
        "task": "app.tasks.token_refresh.refresh_expired_tokens",
        "schedule": 900.0,  # Every 15 minutes
    },
    "sync-killmails-from-esi": {
        "task": "app.tasks.killmail_sync.sync_killmails_from_esi",
        "schedule": 300.0,  # Every 5 minutes
    },
    "sync-all-corporations": {
        "task": "app.tasks.corporation_sync.sync_all_corporations",
        "schedule": 3600.0,  # Every hour
    },
    "sync-trade-hub-markets": {
        "task": "app.tasks.market_sync.sync_trade_hub_markets",
        "schedule": 600.0,  # Every 10 minutes
    },
}

