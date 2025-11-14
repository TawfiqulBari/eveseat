"""
Application configuration
"""
from pydantic_settings import BaseSettings
from typing import List
import json


class Settings(BaseSettings):
    """Application settings"""
    
    # Database
    DATABASE_URL: str
    POSTGRES_USER: str = "eve_user"
    POSTGRES_PASSWORD: str = "secure_password"
    POSTGRES_DB: str = "eve_db"
    
    # Redis
    REDIS_URL: str = "redis://redis:6379/0"
    
    # Security
    SECRET_KEY: str
    ENCRYPTION_KEY: str
    
    # EVE ESI
    ESI_CLIENT_ID: str
    ESI_CLIENT_SECRET: str
    ESI_CALLBACK_URL: str
    ESI_BASE_URL: str = "https://esi.evetech.net/latest"
    ESI_SSO_AUTH_URL: str = "https://login.eveonline.com/v2/oauth/authorize"
    ESI_SSO_TOKEN_URL: str = "https://login.eveonline.com/v2/oauth/token"
    ESI_SSO_JWKS_URL: str = "https://login.eveonline.com/oauth/jwks"
    
    # Application
    DEBUG: bool = False
    ALLOWED_ORIGINS: str = "http://localhost:3000"
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    
    # zKillboard
    ZKILL_REDISQ_QUEUE_ID: str = ""
    ZKILL_REDISQ_URL: str = "https://zkillboard.com/api/no-items/no-attackers/queueID"
    
    # ESI Scopes
    ESI_SCOPES: List[str] = [
        # Character information
        "esi-characters.read_contacts.v1",
        "esi-characters.read_standings.v1",
        "esi-characters.read_titles.v1",
        "esi-characters.read_blueprints.v1",
        "esi-characters.read_corporation_roles.v1",
        "esi-characters.read_corporation_membership.v1",
        "esi-characters.read_loyalty.v1",
        "esi-characters.read_medals.v1",
        "esi-characters.read_fatigue.v1",
        "esi-characters.read_opportunities.v1",
        "esi-characters.read_notifications.v1",
        "esi-characters.read_mail.v1",
        "esi-characters.read_calendar.v1",
        "esi-characters.read_chat_channels.v1",
        "esi-characters.read_fw_stats.v1",
        # Character assets and wallet
        "esi-assets.read_assets.v1",  # Personal character assets
        "esi-characters.read_wallet.v1",  # Personal wallet
        # Character location and ship
        "esi-location.read_location.v1",
        "esi-characters.read_online.v1",
        "esi-characters.read_ship_type.v1",
        # Character skills
        "esi-characters.read_skillqueue.v1",
        "esi-characters.read_skills.v1",
        # Personal market orders
        "esi-markets.read_character_orders.v1",  # Personal market orders
        # Corporation data (if user has access)
        "esi-corporations.read_corporation_membership.v1",
        "esi-assets.read_corporation_assets.v1",
        "esi-wallet.read_corporation_wallets.v1",
        "esi-corporations.read_structures.v1",
        "esi-markets.read_corporation_orders.v1",
        # Killmails
        "esi-killmails.read_killmails.v1",
        # Universe
        "esi-universe.read_structures.v1",
        # Fleets
        "esi-fleets.read_fleet.v1",
    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        
        @classmethod
        def parse_env_var(cls, field_name: str, raw_val: str) -> any:
            if field_name == "CORS_ORIGINS":
                try:
                    return json.loads(raw_val)
                except json.JSONDecodeError:
                    return [raw_val]
            return cls.json_loads(raw_val) if field_name.endswith("_LIST") else raw_val


settings = Settings()

