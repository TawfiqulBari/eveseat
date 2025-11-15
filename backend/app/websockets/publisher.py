"""
Event Publisher Utilities

Helper functions to publish events from anywhere in the application
to WebSocket clients via Redis pub/sub
"""
import logging
import redis
import json
from typing import Dict, Any, Optional
from datetime import datetime

from app.core.config import settings
from app.websockets.events import EventType

logger = logging.getLogger(__name__)


class EventPublisher:
    """
    Publishes events to Redis for distribution to WebSocket clients

    This is a synchronous publisher for use in Celery tasks and other
    non-async contexts
    """

    def __init__(self):
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
            )
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            self.redis_client = None

    def publish(
        self,
        channel: str,
        event_type: EventType,
        data: Dict[str, Any],
    ) -> bool:
        """
        Publish an event to a Redis channel

        Args:
            channel: Redis channel name (e.g., "killmails", "market")
            event_type: Event type
            data: Event data

        Returns:
            True if published successfully
        """
        if not self.redis_client:
            logger.warning("Redis not available, event not published")
            return False

        try:
            message = {
                "type": event_type.value,
                "timestamp": datetime.utcnow().isoformat(),
                "data": data,
            }

            message_json = json.dumps(message)
            self.redis_client.publish(channel, message_json)

            logger.debug(f"Published event to {channel}: {event_type.value}")
            return True

        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            return False

    def publish_killmail(
        self,
        killmail_id: int,
        killmail_data: Dict[str, Any],
    ):
        """
        Publish a new killmail event

        Args:
            killmail_id: Killmail ID
            killmail_data: Killmail data
        """
        return self.publish(
            "killmails",
            EventType.KILLMAIL_NEW,
            {
                "killmail_id": killmail_id,
                **killmail_data,
            },
        )

    def publish_market_order(
        self,
        order_id: int,
        order_data: Dict[str, Any],
        event_type: EventType = EventType.MARKET_ORDER_NEW,
    ):
        """
        Publish a market order event

        Args:
            order_id: Order ID
            order_data: Order data
            event_type: Event type (new, update, cancel)
        """
        return self.publish(
            "market",
            event_type,
            {
                "order_id": order_id,
                **order_data,
            },
        )

    def publish_fleet_update(
        self,
        fleet_id: int,
        fleet_data: Dict[str, Any],
    ):
        """
        Publish a fleet update event

        Args:
            fleet_id: Fleet ID
            fleet_data: Fleet data
        """
        return self.publish(
            "fleet",
            EventType.FLEET_UPDATE,
            {
                "fleet_id": fleet_id,
                **fleet_data,
            },
        )

    def publish_notification(
        self,
        character_id: int,
        notification_data: Dict[str, Any],
    ):
        """
        Publish a notification event

        Args:
            character_id: Character ID
            notification_data: Notification data
        """
        return self.publish(
            "notifications",
            EventType.NOTIFICATION_NEW,
            {
                "character_id": character_id,
                **notification_data,
            },
        )

    def publish_mail(
        self,
        character_id: int,
        mail_data: Dict[str, Any],
    ):
        """
        Publish a mail event

        Args:
            character_id: Character ID
            mail_data: Mail data
        """
        return self.publish(
            "mail",
            EventType.MAIL_NEW,
            {
                "character_id": character_id,
                **mail_data,
            },
        )

    def publish_character_location(
        self,
        character_id: int,
        location_data: Dict[str, Any],
    ):
        """
        Publish a character location update

        Args:
            character_id: Character ID
            location_data: Location data
        """
        return self.publish(
            "character",
            EventType.CHARACTER_LOCATION_UPDATE,
            {
                "character_id": character_id,
                **location_data,
            },
        )

    def publish_corporation_update(
        self,
        corporation_id: int,
        update_data: Dict[str, Any],
        event_type: EventType,
    ):
        """
        Publish a corporation update event

        Args:
            corporation_id: Corporation ID
            update_data: Update data
            event_type: Event type
        """
        return self.publish(
            "corporation",
            event_type,
            {
                "corporation_id": corporation_id,
                **update_data,
            },
        )

    def publish_contract(
        self,
        contract_id: int,
        contract_data: Dict[str, Any],
        event_type: EventType,
    ):
        """
        Publish a contract event

        Args:
            contract_id: Contract ID
            contract_data: Contract data
            event_type: Event type
        """
        return self.publish(
            "contracts",
            event_type,
            {
                "contract_id": contract_id,
                **contract_data,
            },
        )

    def publish_industry_job(
        self,
        job_id: int,
        job_data: Dict[str, Any],
        event_type: EventType,
    ):
        """
        Publish an industry job event

        Args:
            job_id: Job ID
            job_data: Job data
            event_type: Event type
        """
        return self.publish(
            "industry",
            event_type,
            {
                "job_id": job_id,
                **job_data,
            },
        )

    def publish_wallet_event(
        self,
        character_id: int,
        wallet_data: Dict[str, Any],
        event_type: EventType,
    ):
        """
        Publish a wallet event

        Args:
            character_id: Character ID
            wallet_data: Wallet data
            event_type: Event type (transaction or journal)
        """
        return self.publish(
            "wallet",
            event_type,
            {
                "character_id": character_id,
                **wallet_data,
            },
        )

    def publish_sync_status(
        self,
        sync_id: str,
        sync_type: str,
        status: str,
        **kwargs,
    ):
        """
        Publish a sync status event

        Args:
            sync_id: Unique sync operation ID
            sync_type: Type of sync operation
            status: Status (started, progress, completed, error)
            **kwargs: Additional data (character_id, progress, error_message, etc.)
        """
        event_type_map = {
            "started": EventType.SYNC_START,
            "progress": EventType.SYNC_PROGRESS,
            "completed": EventType.SYNC_COMPLETE,
            "error": EventType.SYNC_ERROR,
        }

        event_type = event_type_map.get(status, EventType.SYNC_PROGRESS)

        return self.publish(
            "sync_status",
            event_type,
            {
                "sync_id": sync_id,
                "sync_type": sync_type,
                "status": status,
                **kwargs,
            },
        )


# Global event publisher instance
event_publisher = EventPublisher()


# Convenience function for publishing events
def publish_event(
    channel: str,
    event_type: EventType,
    data: Dict[str, Any],
) -> bool:
    """
    Convenience function to publish an event using the global publisher

    Args:
        channel: Redis channel name
        event_type: Event type
        data: Event data

    Returns:
        True if published successfully
    """
    return event_publisher.publish(channel, event_type, data)
