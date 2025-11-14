"""
WebSocket Event Types and Handlers

Defines event types and streaming handlers for real-time data
"""
from typing import Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class EventType(str, Enum):
    """WebSocket event types"""

    # System events
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"

    # Subscription events
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    SUBSCRIBED = "subscribed"
    UNSUBSCRIBED = "unsubscribed"

    # Data events
    KILLMAIL_NEW = "killmail.new"
    KILLMAIL_UPDATE = "killmail.update"

    MARKET_ORDER_NEW = "market.order.new"
    MARKET_ORDER_UPDATE = "market.order.update"
    MARKET_ORDER_CANCEL = "market.order.cancel"
    MARKET_PRICE_UPDATE = "market.price.update"

    FLEET_UPDATE = "fleet.update"
    FLEET_MEMBER_JOIN = "fleet.member.join"
    FLEET_MEMBER_LEAVE = "fleet.member.leave"
    FLEET_WING_UPDATE = "fleet.wing.update"

    NOTIFICATION_NEW = "notification.new"
    NOTIFICATION_READ = "notification.read"

    MAIL_NEW = "mail.new"
    MAIL_READ = "mail.read"

    CHARACTER_LOCATION_UPDATE = "character.location.update"
    CHARACTER_SHIP_UPDATE = "character.ship.update"
    CHARACTER_ONLINE_STATUS = "character.online.status"

    CORPORATION_MEMBER_JOIN = "corporation.member.join"
    CORPORATION_MEMBER_LEAVE = "corporation.member.leave"
    CORPORATION_STRUCTURE_UPDATE = "corporation.structure.update"

    CONTRACT_NEW = "contract.new"
    CONTRACT_ACCEPT = "contract.accept"
    CONTRACT_COMPLETE = "contract.complete"
    CONTRACT_EXPIRE = "contract.expire"

    INDUSTRY_JOB_START = "industry.job.start"
    INDUSTRY_JOB_COMPLETE = "industry.job.complete"
    INDUSTRY_JOB_UPDATE = "industry.job.update"

    BLUEPRINT_UPDATE = "blueprint.update"

    PLANETARY_UPDATE = "planetary.update"
    PLANETARY_EXTRACTION_EXPIRE = "planetary.extraction.expire"

    LOYALTY_UPDATE = "loyalty.update"

    WALLET_TRANSACTION = "wallet.transaction"
    WALLET_JOURNAL = "wallet.journal"

    FITTING_UPDATE = "fitting.update"
    FITTING_DELETE = "fitting.delete"

    SKILL_UPDATE = "skill.update"
    SKILL_QUEUE_UPDATE = "skill.queue.update"
    SKILL_TRAINING_COMPLETE = "skill.training.complete"

    CLONE_UPDATE = "clone.update"
    IMPLANT_UPDATE = "implant.update"

    BOOKMARK_NEW = "bookmark.new"
    BOOKMARK_UPDATE = "bookmark.update"
    BOOKMARK_DELETE = "bookmark.delete"
    BOOKMARK_FOLDER_UPDATE = "bookmark.folder.update"

    # Sync status events
    SYNC_START = "sync.start"
    SYNC_PROGRESS = "sync.progress"
    SYNC_COMPLETE = "sync.complete"
    SYNC_ERROR = "sync.error"


class Topic(str, Enum):
    """Available subscription topics"""

    # Public topics (no auth required)
    SYSTEM_STATUS = "system.status"
    KILLMAILS_PUBLIC = "killmails.public"

    # User topics (auth required)
    KILLMAILS = "killmails"
    MARKET = "market"
    FLEET = "fleet"
    NOTIFICATIONS = "notifications"
    MAIL = "mail"
    CHARACTER = "character"
    CORPORATION = "corporation"
    CONTRACTS = "contracts"
    INDUSTRY = "industry"
    BLUEPRINTS = "blueprints"
    PLANETARY = "planetary"
    LOYALTY = "loyalty"
    WALLET = "wallet"
    FITTINGS = "fittings"
    SKILLS = "skills"
    CLONES = "clones"
    BOOKMARKS = "bookmarks"
    SYNC_STATUS = "sync.status"

    # Admin topics (admin auth required)
    ADMIN_LOGS = "admin.logs"
    ADMIN_METRICS = "admin.metrics"


class WebSocketMessage(BaseModel):
    """Base WebSocket message"""

    type: EventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Optional[Dict[str, Any]] = None


class SubscriptionMessage(BaseModel):
    """Subscription request message"""

    type: Literal[EventType.SUBSCRIBE, EventType.UNSUBSCRIBE]
    topic: Topic


class KillmailEventData(BaseModel):
    """Killmail event data"""

    killmail_id: int
    killmail_hash: str
    victim_character_id: Optional[int] = None
    victim_character_name: Optional[str] = None
    victim_corporation_id: Optional[int] = None
    victim_ship_type_id: int
    victim_ship_name: str
    solar_system_id: int
    solar_system_name: str
    killmail_time: datetime
    total_value: Optional[float] = None
    attackers_count: int


class MarketOrderEventData(BaseModel):
    """Market order event data"""

    order_id: int
    type_id: int
    type_name: str
    location_id: int
    location_name: str
    is_buy_order: bool
    price: float
    volume_total: int
    volume_remain: int
    issued: datetime
    duration: int


class FleetEventData(BaseModel):
    """Fleet event data"""

    fleet_id: int
    fleet_name: Optional[str] = None
    member_count: int
    is_free_move: bool
    is_voice_enabled: bool
    motd: Optional[str] = None


class NotificationEventData(BaseModel):
    """Notification event data"""

    notification_id: int
    sender_id: Optional[int] = None
    sender_type: str
    type: str
    timestamp: datetime
    is_read: bool
    text: Optional[str] = None


class MailEventData(BaseModel):
    """Mail event data"""

    mail_id: int
    from_id: int
    from_name: str
    subject: str
    timestamp: datetime
    is_read: bool
    labels: list[int] = []


class CharacterLocationEventData(BaseModel):
    """Character location update data"""

    character_id: int
    solar_system_id: int
    solar_system_name: str
    station_id: Optional[int] = None
    structure_id: Optional[int] = None


class SyncStatusEventData(BaseModel):
    """Sync status event data"""

    sync_id: str
    sync_type: str  # e.g., "character_assets", "corporation_members"
    character_id: Optional[int] = None
    corporation_id: Optional[int] = None
    status: Literal["started", "progress", "completed", "error"]
    progress_current: Optional[int] = None
    progress_total: Optional[int] = None
    error_message: Optional[str] = None


def create_event(
    event_type: EventType,
    data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Create a WebSocket event message

    Args:
        event_type: Type of event
        data: Event data

    Returns:
        Event message dictionary
    """
    return {
        "type": event_type.value,
        "timestamp": datetime.utcnow().isoformat(),
        "data": data or {},
    }


def create_error_event(
    error_message: str,
    error_code: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create an error event message

    Args:
        error_message: Error message
        error_code: Optional error code

    Returns:
        Error event message
    """
    return create_event(
        EventType.ERROR,
        {
            "message": error_message,
            "code": error_code,
        },
    )


def create_subscription_confirmation(
    topic: Topic,
    subscribed: bool,
) -> Dict[str, Any]:
    """
    Create a subscription confirmation event

    Args:
        topic: Topic name
        subscribed: Whether subscribed (True) or unsubscribed (False)

    Returns:
        Subscription confirmation event
    """
    event_type = EventType.SUBSCRIBED if subscribed else EventType.UNSUBSCRIBED
    return create_event(
        event_type,
        {"topic": topic.value},
    )
