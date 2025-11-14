"""
WebSocket Server

Main WebSocket application for real-time event streaming
"""
import logging
import secrets
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Query, status
from fastapi.middleware.cors import CORSMiddleware
import json
from typing import Optional
from datetime import datetime

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.user import User
from app.models.eve_token import EveToken
from app.websockets.connection_manager import manager
from app.websockets.events import (
    EventType,
    Topic,
    create_event,
    create_error_event,
    create_subscription_confirmation,
)
from app.websockets.redis_pubsub import RedisSubscriber
from sqlalchemy import select
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="EVE WebSocket Server", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis subscriber for cross-server event distribution
redis_subscriber = RedisSubscriber()


async def get_user_from_token(token: str) -> Optional[User]:
    """
    Authenticate user from token

    Args:
        token: Authentication token

    Returns:
        User object if authenticated, None otherwise
    """
    if not token:
        return None

    db = SessionLocal()
    try:
        # For now, use simple token lookup
        # In production, verify JWT token properly
        stmt = select(User).join(EveToken).where(EveToken.access_token == token)
        result = db.execute(stmt)
        user = result.scalar_one_or_none()
        return user
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        return None
    finally:
        db.close()


@app.on_event("startup")
async def startup_event():
    """Initialize WebSocket server on startup"""
    logger.info("WebSocket server starting...")

    # Start Redis subscriber
    await redis_subscriber.start()

    # Subscribe to Redis channels and forward to WebSocket clients
    async def handle_redis_message(channel: str, message: dict):
        """Handle messages from Redis pub/sub"""
        try:
            # Determine topic from Redis channel
            topic_map = {
                "killmails": Topic.KILLMAILS,
                "market": Topic.MARKET,
                "fleet": Topic.FLEET,
                "notifications": Topic.NOTIFICATIONS,
                "mail": Topic.MAIL,
                "character": Topic.CHARACTER,
                "corporation": Topic.CORPORATION,
                "contracts": Topic.CONTRACTS,
                "industry": Topic.INDUSTRY,
                "wallet": Topic.WALLET,
                "sync_status": Topic.SYNC_STATUS,
            }

            topic = topic_map.get(channel)
            if topic:
                await manager.broadcast_to_topic(topic, message)
            else:
                logger.warning(f"Unknown Redis channel: {channel}")

        except Exception as e:
            logger.error(f"Error handling Redis message: {e}")

    # Subscribe to all relevant Redis channels
    channels = [
        "killmails",
        "market",
        "fleet",
        "notifications",
        "mail",
        "character",
        "corporation",
        "contracts",
        "industry",
        "wallet",
        "sync_status",
    ]

    for channel in channels:
        await redis_subscriber.subscribe(channel, handle_redis_message)

    logger.info("WebSocket server started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("WebSocket server shutting down...")
    await redis_subscriber.stop()
    logger.info("WebSocket server stopped")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "EVE WebSocket Server",
        "status": "running",
        "version": "1.0.0",
        "stats": manager.get_stats(),
    }


@app.get("/stats")
async def get_stats():
    """Get connection statistics"""
    return manager.get_stats()


@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
):
    """
    Main WebSocket endpoint

    Clients connect with authentication token as query parameter:
    ws://localhost:8001/ws?token=<access_token>

    Message format:
    {
        "type": "subscribe|unsubscribe|ping",
        "topic": "killmails|market|fleet|...",  // for subscribe/unsubscribe
        "data": {...}  // optional additional data
    }

    Response format:
    {
        "type": "event_type",
        "timestamp": "2024-01-01T00:00:00",
        "data": {...}
    }
    """
    connection_id = secrets.token_urlsafe(16)
    user = None

    # Authenticate user
    if token:
        user = await get_user_from_token(token)

    if not user:
        # Allow anonymous connections for public topics only
        # For now, reject unauthenticated connections
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        # Connect
        await manager.connect(websocket, connection_id, user.id)

        # Send connection confirmation
        await manager.send_personal_message(
            connection_id,
            create_event(
                EventType.CONNECTED,
                {
                    "connection_id": connection_id,
                    "user_id": user.id,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            ),
        )

        # Main message loop
        while True:
            # Receive message from client
            data = await websocket.receive_json()

            # Handle message
            await handle_client_message(connection_id, user.id, data)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await manager.send_personal_message(
                connection_id,
                create_error_event(f"Server error: {str(e)}"),
            )
        except:
            pass
    finally:
        await manager.disconnect(connection_id)


async def handle_client_message(
    connection_id: str,
    user_id: int,
    message: dict,
):
    """
    Handle incoming client messages

    Args:
        connection_id: Connection identifier
        user_id: User ID
        message: Message from client
    """
    try:
        msg_type = message.get("type")

        if msg_type == EventType.PING.value:
            # Respond with pong
            await manager.send_personal_message(
                connection_id,
                create_event(EventType.PONG),
            )

        elif msg_type == EventType.SUBSCRIBE.value:
            # Subscribe to topic
            topic_name = message.get("topic")

            if not topic_name:
                await manager.send_personal_message(
                    connection_id,
                    create_error_event("Topic required for subscription"),
                )
                return

            try:
                topic = Topic(topic_name)

                # Check if user has permission for this topic
                if not await check_topic_permission(user_id, topic):
                    await manager.send_personal_message(
                        connection_id,
                        create_error_event(
                            f"Permission denied for topic: {topic_name}"
                        ),
                    )
                    return

                # Subscribe
                success = await manager.subscribe(connection_id, topic.value)

                if success:
                    await manager.send_personal_message(
                        connection_id,
                        create_subscription_confirmation(topic, True),
                    )
                else:
                    await manager.send_personal_message(
                        connection_id,
                        create_error_event(f"Failed to subscribe to: {topic_name}"),
                    )

            except ValueError:
                await manager.send_personal_message(
                    connection_id,
                    create_error_event(f"Invalid topic: {topic_name}"),
                )

        elif msg_type == EventType.UNSUBSCRIBE.value:
            # Unsubscribe from topic
            topic_name = message.get("topic")

            if not topic_name:
                await manager.send_personal_message(
                    connection_id,
                    create_error_event("Topic required for unsubscription"),
                )
                return

            try:
                topic = Topic(topic_name)

                # Unsubscribe
                success = await manager.unsubscribe(connection_id, topic.value)

                if success:
                    await manager.send_personal_message(
                        connection_id,
                        create_subscription_confirmation(topic, False),
                    )

            except ValueError:
                await manager.send_personal_message(
                    connection_id,
                    create_error_event(f"Invalid topic: {topic_name}"),
                )

        else:
            # Unknown message type
            await manager.send_personal_message(
                connection_id,
                create_error_event(f"Unknown message type: {msg_type}"),
            )

    except Exception as e:
        logger.error(f"Error handling message: {e}")
        await manager.send_personal_message(
            connection_id,
            create_error_event(f"Error processing message: {str(e)}"),
        )


async def check_topic_permission(user_id: int, topic: Topic) -> bool:
    """
    Check if user has permission to subscribe to a topic

    Args:
        user_id: User ID
        topic: Topic to check

    Returns:
        True if user has permission
    """
    # Public topics - anyone can subscribe
    if topic in [Topic.SYSTEM_STATUS, Topic.KILLMAILS_PUBLIC]:
        return True

    # For all other topics, user must be authenticated (which they are if we got here)
    # In the future, add more granular permissions based on corporation roles, etc.

    # Admin topics
    if topic in [Topic.ADMIN_LOGS, Topic.ADMIN_METRICS]:
        # Check if user is admin (implement admin check)
        # For now, deny admin topics
        return False

    return True


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
