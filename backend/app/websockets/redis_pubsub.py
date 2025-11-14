"""
Redis Pub/Sub Subscriber

Subscribes to Redis channels and forwards messages to WebSocket clients
Enables multi-server WebSocket deployments with shared event bus
"""
import asyncio
import logging
import json
from typing import Dict, Callable, Awaitable, Optional
import redis.asyncio as aioredis
from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisSubscriber:
    """
    Redis Pub/Sub subscriber for event distribution

    Subscribes to Redis channels and calls registered handlers when messages arrive
    """

    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None
        self.pubsub: Optional[aioredis.client.PubSub] = None
        self.handlers: Dict[str, Callable[[str, dict], Awaitable[None]]] = {}
        self._running = False
        self._listener_task: Optional[asyncio.Task] = None

    async def start(self):
        """Initialize Redis connection and start listening"""
        try:
            # Create Redis connection
            self.redis = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )

            # Create pub/sub
            self.pubsub = self.redis.pubsub()

            self._running = True
            logger.info("Redis subscriber initialized")

        except Exception as e:
            logger.error(f"Failed to initialize Redis subscriber: {e}")
            raise

    async def stop(self):
        """Stop listening and close Redis connection"""
        self._running = False

        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass

        if self.pubsub:
            await self.pubsub.unsubscribe()
            await self.pubsub.close()

        if self.redis:
            await self.redis.close()

        logger.info("Redis subscriber stopped")

    async def subscribe(
        self,
        channel: str,
        handler: Callable[[str, dict], Awaitable[None]],
    ):
        """
        Subscribe to a Redis channel

        Args:
            channel: Redis channel name
            handler: Async function to call when messages arrive
                     Signature: async def handler(channel: str, message: dict)
        """
        if not self.pubsub:
            raise RuntimeError("Redis subscriber not initialized")

        # Store handler
        self.handlers[channel] = handler

        # Subscribe to channel
        await self.pubsub.subscribe(channel)

        logger.info(f"Subscribed to Redis channel: {channel}")

        # Start listener if not already running
        if not self._listener_task or self._listener_task.done():
            self._listener_task = asyncio.create_task(self._listen())

    async def unsubscribe(self, channel: str):
        """
        Unsubscribe from a Redis channel

        Args:
            channel: Redis channel name
        """
        if not self.pubsub:
            return

        # Remove handler
        if channel in self.handlers:
            del self.handlers[channel]

        # Unsubscribe from channel
        await self.pubsub.unsubscribe(channel)

        logger.info(f"Unsubscribed from Redis channel: {channel}")

    async def _listen(self):
        """Listen for messages on subscribed channels"""
        logger.info("Redis listener started")

        try:
            while self._running:
                try:
                    # Get message
                    message = await self.pubsub.get_message(
                        ignore_subscribe_messages=True,
                        timeout=1.0,
                    )

                    if message and message["type"] == "message":
                        channel = message["channel"]
                        data = message["data"]

                        # Parse JSON data
                        try:
                            message_data = json.loads(data)
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid JSON from channel {channel}: {data}")
                            continue

                        # Call handler
                        handler = self.handlers.get(channel)
                        if handler:
                            try:
                                await handler(channel, message_data)
                            except Exception as e:
                                logger.error(
                                    f"Error in handler for channel {channel}: {e}"
                                )

                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.error(f"Error in Redis listener: {e}")
                    await asyncio.sleep(1)

        except asyncio.CancelledError:
            logger.info("Redis listener cancelled")
            raise
        except Exception as e:
            logger.error(f"Fatal error in Redis listener: {e}")
        finally:
            logger.info("Redis listener stopped")


class RedisPublisher:
    """
    Redis publisher for event distribution

    Publishes events to Redis channels for distribution to all WebSocket servers
    """

    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None

    async def connect(self):
        """Initialize Redis connection"""
        try:
            self.redis = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
            logger.info("Redis publisher initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Redis publisher: {e}")
            raise

    async def close(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()
            logger.info("Redis publisher closed")

    async def publish(self, channel: str, message: dict):
        """
        Publish a message to a Redis channel

        Args:
            channel: Redis channel name
            message: Message dictionary to publish
        """
        if not self.redis:
            await self.connect()

        try:
            # Convert message to JSON
            message_json = json.dumps(message)

            # Publish to channel
            await self.redis.publish(channel, message_json)

            logger.debug(f"Published to channel {channel}: {message_json[:100]}")

        except Exception as e:
            logger.error(f"Failed to publish to channel {channel}: {e}")
            raise


# Global publisher instance
redis_publisher = RedisPublisher()
