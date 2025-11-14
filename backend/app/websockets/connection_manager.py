"""
WebSocket Connection Manager

Manages WebSocket connections with authentication, subscriptions, and broadcasting
"""
import logging
from typing import Dict, Set, Optional, List
from fastapi import WebSocket
import asyncio
import json
from datetime import datetime

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections for real-time event streaming

    Features:
    - Per-user connection tracking
    - Topic-based subscriptions
    - Broadcast to all connections or specific topics
    - Automatic cleanup on disconnect
    """

    def __init__(self):
        # Active connections: {user_id: {connection_id: websocket}}
        self.active_connections: Dict[int, Dict[str, WebSocket]] = {}

        # Subscriptions: {topic: {user_id: Set[connection_id]}}
        self.subscriptions: Dict[str, Dict[int, Set[str]]] = {}

        # Connection metadata: {connection_id: {user_id, topics, connected_at}}
        self.connection_metadata: Dict[str, Dict] = {}

        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

    async def connect(
        self,
        websocket: WebSocket,
        connection_id: str,
        user_id: int,
    ) -> None:
        """
        Register a new WebSocket connection

        Args:
            websocket: WebSocket instance
            connection_id: Unique connection identifier
            user_id: Authenticated user ID
        """
        await websocket.accept()

        async with self._lock:
            # Add to user's connections
            if user_id not in self.active_connections:
                self.active_connections[user_id] = {}
            self.active_connections[user_id][connection_id] = websocket

            # Store metadata
            self.connection_metadata[connection_id] = {
                "user_id": user_id,
                "topics": set(),
                "connected_at": datetime.utcnow(),
            }

        logger.info(f"WebSocket connected: user={user_id}, conn={connection_id}")

    async def disconnect(self, connection_id: str) -> None:
        """
        Unregister a WebSocket connection

        Args:
            connection_id: Connection identifier to remove
        """
        async with self._lock:
            # Get metadata
            metadata = self.connection_metadata.get(connection_id)
            if not metadata:
                return

            user_id = metadata["user_id"]
            topics = metadata["topics"]

            # Remove from user connections
            if user_id in self.active_connections:
                if connection_id in self.active_connections[user_id]:
                    del self.active_connections[user_id][connection_id]

                # Clean up empty user entry
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]

            # Remove from topic subscriptions
            for topic in topics:
                if topic in self.subscriptions:
                    if user_id in self.subscriptions[topic]:
                        if connection_id in self.subscriptions[topic][user_id]:
                            self.subscriptions[topic][user_id].discard(connection_id)

                        # Clean up empty entries
                        if not self.subscriptions[topic][user_id]:
                            del self.subscriptions[topic][user_id]

                    if not self.subscriptions[topic]:
                        del self.subscriptions[topic]

            # Remove metadata
            del self.connection_metadata[connection_id]

        logger.info(f"WebSocket disconnected: conn={connection_id}")

    async def subscribe(
        self,
        connection_id: str,
        topic: str,
    ) -> bool:
        """
        Subscribe a connection to a topic

        Args:
            connection_id: Connection identifier
            topic: Topic name to subscribe to

        Returns:
            True if subscribed successfully
        """
        async with self._lock:
            metadata = self.connection_metadata.get(connection_id)
            if not metadata:
                return False

            user_id = metadata["user_id"]

            # Add to subscriptions
            if topic not in self.subscriptions:
                self.subscriptions[topic] = {}

            if user_id not in self.subscriptions[topic]:
                self.subscriptions[topic][user_id] = set()

            self.subscriptions[topic][user_id].add(connection_id)

            # Update metadata
            metadata["topics"].add(topic)

        logger.info(f"Subscribed: conn={connection_id}, topic={topic}")
        return True

    async def unsubscribe(
        self,
        connection_id: str,
        topic: str,
    ) -> bool:
        """
        Unsubscribe a connection from a topic

        Args:
            connection_id: Connection identifier
            topic: Topic name to unsubscribe from

        Returns:
            True if unsubscribed successfully
        """
        async with self._lock:
            metadata = self.connection_metadata.get(connection_id)
            if not metadata:
                return False

            user_id = metadata["user_id"]

            # Remove from subscriptions
            if topic in self.subscriptions:
                if user_id in self.subscriptions[topic]:
                    if connection_id in self.subscriptions[topic][user_id]:
                        self.subscriptions[topic][user_id].discard(connection_id)

                    if not self.subscriptions[topic][user_id]:
                        del self.subscriptions[topic][user_id]

                if not self.subscriptions[topic]:
                    del self.subscriptions[topic]

            # Update metadata
            metadata["topics"].discard(topic)

        logger.info(f"Unsubscribed: conn={connection_id}, topic={topic}")
        return True

    async def send_personal_message(
        self,
        connection_id: str,
        message: dict,
    ) -> bool:
        """
        Send a message to a specific connection

        Args:
            connection_id: Connection identifier
            message: Message dictionary to send

        Returns:
            True if sent successfully
        """
        metadata = self.connection_metadata.get(connection_id)
        if not metadata:
            return False

        user_id = metadata["user_id"]
        websocket = self.active_connections.get(user_id, {}).get(connection_id)

        if not websocket:
            return False

        try:
            await websocket.send_json(message)
            return True
        except Exception as e:
            logger.error(f"Failed to send message to {connection_id}: {e}")
            # Connection broken, disconnect it
            await self.disconnect(connection_id)
            return False

    async def broadcast_to_user(
        self,
        user_id: int,
        message: dict,
    ) -> int:
        """
        Send a message to all connections of a specific user

        Args:
            user_id: User ID
            message: Message dictionary to send

        Returns:
            Number of connections successfully sent to
        """
        user_connections = self.active_connections.get(user_id, {})
        sent_count = 0

        # Create tasks for all sends
        tasks = []
        for connection_id in list(user_connections.keys()):
            tasks.append(self.send_personal_message(connection_id, message))

        # Send concurrently
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            sent_count = sum(1 for r in results if r is True)

        return sent_count

    async def broadcast_to_topic(
        self,
        topic: str,
        message: dict,
        exclude_user_id: Optional[int] = None,
    ) -> int:
        """
        Broadcast a message to all subscribers of a topic

        Args:
            topic: Topic name
            message: Message dictionary to send
            exclude_user_id: Optional user ID to exclude from broadcast

        Returns:
            Number of connections successfully sent to
        """
        topic_subscribers = self.subscriptions.get(topic, {})
        sent_count = 0

        # Collect all connections to send to
        tasks = []
        for user_id, connection_ids in topic_subscribers.items():
            if exclude_user_id and user_id == exclude_user_id:
                continue

            for connection_id in connection_ids:
                tasks.append(self.send_personal_message(connection_id, message))

        # Send concurrently
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            sent_count = sum(1 for r in results if r is True)

        logger.debug(f"Broadcast to topic '{topic}': {sent_count} connections")
        return sent_count

    async def broadcast_to_all(
        self,
        message: dict,
        exclude_user_id: Optional[int] = None,
    ) -> int:
        """
        Broadcast a message to all connected clients

        Args:
            message: Message dictionary to send
            exclude_user_id: Optional user ID to exclude from broadcast

        Returns:
            Number of connections successfully sent to
        """
        tasks = []

        for user_id, connections in self.active_connections.items():
            if exclude_user_id and user_id == exclude_user_id:
                continue

            for connection_id in connections.keys():
                tasks.append(self.send_personal_message(connection_id, message))

        # Send concurrently
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            sent_count = sum(1 for r in results if r is True)
        else:
            sent_count = 0

        logger.debug(f"Broadcast to all: {sent_count} connections")
        return sent_count

    def get_connection_count(self) -> int:
        """Get total number of active connections"""
        return sum(len(conns) for conns in self.active_connections.values())

    def get_user_connection_count(self, user_id: int) -> int:
        """Get number of active connections for a specific user"""
        return len(self.active_connections.get(user_id, {}))

    def get_topic_subscriber_count(self, topic: str) -> int:
        """Get number of subscribers to a specific topic"""
        return sum(
            len(conn_ids)
            for conn_ids in self.subscriptions.get(topic, {}).values()
        )

    def get_stats(self) -> Dict:
        """Get connection statistics"""
        return {
            "total_connections": self.get_connection_count(),
            "total_users": len(self.active_connections),
            "total_topics": len(self.subscriptions),
            "topics": {
                topic: self.get_topic_subscriber_count(topic)
                for topic in self.subscriptions.keys()
            },
        }


# Global connection manager instance
manager = ConnectionManager()
