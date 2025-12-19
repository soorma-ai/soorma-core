"""
NATS adapter for the Event Service.

This adapter implements the EventAdapter interface using NATS JetStream
as the underlying message bus.
"""
import asyncio
import json
import logging
from typing import Any, Dict, List
from uuid import uuid4

import nats
from nats.aio.client import Client as NatsClient
from nats.aio.msg import Msg

from .base import EventAdapter, MessageHandler, PublishError, SubscriptionError

logger = logging.getLogger(__name__)


class NatsAdapter(EventAdapter):
    """
    NATS adapter for the Event Service.
    
    Uses NATS Core for simple pub/sub messaging. For durability and
    at-least-once delivery, consider using JetStream (future enhancement).
    
    Features:
    - Automatic reconnection
    - Wildcard subscriptions (e.g., "research.*", "events.>")
    - JSON message serialization
    """
    
    def __init__(
        self,
        url: str = "nats://localhost:4222",
        reconnect_time_wait: int = 2,
        max_reconnect_attempts: int = -1,
    ):
        """
        Initialize the NATS adapter.
        
        Args:
            url: NATS server URL
            reconnect_time_wait: Time to wait between reconnection attempts (seconds)
            max_reconnect_attempts: Max reconnection attempts (-1 for infinite)
        """
        self._url = url
        self._reconnect_time_wait = reconnect_time_wait
        self._max_reconnect_attempts = max_reconnect_attempts
        self._client: NatsClient | None = None
        self._subscriptions: Dict[str, nats.aio.subscription.Subscription] = {}
        self._handlers: Dict[str, MessageHandler] = {}
    
    async def connect(self) -> None:
        """Connect to NATS server with auto-reconnection."""
        if self._client is not None and self._client.is_connected:
            logger.warning("Already connected to NATS")
            return
        
        logger.info(f"Connecting to NATS at {self._url}")
        
        try:
            self._client = await nats.connect(
                servers=[self._url],
                reconnect_time_wait=self._reconnect_time_wait,
                max_reconnect_attempts=self._max_reconnect_attempts,
                error_cb=self._error_callback,
                disconnected_cb=self._disconnected_callback,
                reconnected_cb=self._reconnected_callback,
                closed_cb=self._closed_callback,
            )
            logger.info(f"Connected to NATS server: {self._client.connected_url}")
        except Exception as e:
            logger.error(f"Failed to connect to NATS: {e}")
            raise ConnectionError(f"Failed to connect to NATS at {self._url}: {e}") from e
    
    async def disconnect(self) -> None:
        """Gracefully disconnect from NATS."""
        if self._client is None:
            return
        
        logger.info("Disconnecting from NATS")
        
        # Unsubscribe from all topics
        for sub_id in list(self._subscriptions.keys()):
            await self.unsubscribe(sub_id)
        
        # Drain and close
        try:
            await self._client.drain()
        except Exception as e:
            logger.warning(f"Error draining NATS connection: {e}")
        
        self._client = None
        logger.info("Disconnected from NATS")
    
    async def publish(self, topic: str, message: Dict[str, Any]) -> None:
        """
        Publish a message to a NATS subject.
        
        Args:
            topic: NATS subject (e.g., "events.action-requests")
            message: Message payload (will be JSON serialized)
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to NATS")
        
        # Convert topic format (e.g., "action-requests" -> "events.action-requests")
        subject = self._topic_to_subject(topic)
        
        try:
            payload = json.dumps(message).encode("utf-8")
            await self._client.publish(subject, payload)
            logger.debug(f"Published message to {subject}")
        except Exception as e:
            logger.error(f"Failed to publish to {subject}: {e}")
            raise PublishError(f"Failed to publish to {subject}: {e}") from e
    
    async def subscribe(
        self,
        topics: List[str],
        handler: MessageHandler,
        subscription_id: str | None = None,
    ) -> str:
        """
        Subscribe to one or more NATS subjects.
        
        Args:
            topics: List of topics (supports NATS wildcards: *, >)
            handler: Async callback (topic, message) -> None
            subscription_id: Optional subscription identifier
        
        Returns:
            Subscription ID
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to NATS")
        
        sub_id = subscription_id or str(uuid4())
        
        # Create message handler wrapper
        async def nats_handler(msg: Msg) -> None:
            try:
                topic = self._subject_to_topic(msg.subject)
                message = json.loads(msg.data.decode("utf-8"))
                await handler(topic, message)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode message from {msg.subject}: {e}")
            except Exception as e:
                logger.error(f"Error in message handler for {msg.subject}: {e}")
        
        # Subscribe to each topic
        for topic in topics:
            subject = self._topic_to_subject(topic)
            try:
                sub = await self._client.subscribe(subject, cb=nats_handler)
                self._subscriptions[f"{sub_id}:{subject}"] = sub
                logger.info(f"Subscribed to {subject} (sub_id: {sub_id})")
            except Exception as e:
                logger.error(f"Failed to subscribe to {subject}: {e}")
                # Cleanup any successful subscriptions
                await self._cleanup_partial_subscription(sub_id)
                raise SubscriptionError(f"Failed to subscribe to {subject}: {e}") from e
        
        self._handlers[sub_id] = handler
        return sub_id
    
    async def unsubscribe(self, subscription_id: str) -> None:
        """Unsubscribe from a subscription."""
        # Find and remove all subscriptions with this ID prefix
        keys_to_remove = [k for k in self._subscriptions.keys() if k.startswith(f"{subscription_id}:")]
        
        if not keys_to_remove:
            logger.warning(f"No subscriptions found for {subscription_id}")
            return
        
        for key in keys_to_remove:
            sub = self._subscriptions.pop(key)
            try:
                await sub.unsubscribe()
                logger.info(f"Unsubscribed from {key}")
            except Exception as e:
                logger.warning(f"Error unsubscribing from {key}: {e}")
        
        self._handlers.pop(subscription_id, None)
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to NATS."""
        return self._client is not None and self._client.is_connected
    
    def _topic_to_subject(self, topic: str) -> str:
        """
        Convert topic name to NATS subject.
        
        Examples:
            "action-requests" -> "soorma.events.action-requests"
            "research.*" -> "soorma.events.research.*"
            ">" -> "soorma.events.>"
        """
        # Add Soorma namespace prefix
        return f"soorma.events.{topic}"
    
    def _subject_to_topic(self, subject: str) -> str:
        """
        Convert NATS subject back to topic name.
        
        Examples:
            "soorma.events.action-requests" -> "action-requests"
        """
        prefix = "soorma.events."
        if subject.startswith(prefix):
            return subject[len(prefix):]
        return subject
    
    async def _cleanup_partial_subscription(self, sub_id: str) -> None:
        """Clean up partial subscriptions on failure."""
        keys_to_remove = [k for k in self._subscriptions.keys() if k.startswith(f"{sub_id}:")]
        for key in keys_to_remove:
            sub = self._subscriptions.pop(key)
            try:
                await sub.unsubscribe()
            except Exception:
                pass
    
    # NATS callbacks for connection lifecycle
    
    async def _error_callback(self, e: Exception) -> None:
        """Called on NATS errors."""
        logger.error(f"NATS error: {e}")
    
    async def _disconnected_callback(self) -> None:
        """Called when disconnected from NATS."""
        logger.warning("Disconnected from NATS server")
    
    async def _reconnected_callback(self) -> None:
        """Called when reconnected to NATS."""
        logger.info(f"Reconnected to NATS server: {self._client.connected_url}")
    
    async def _closed_callback(self) -> None:
        """Called when NATS connection is closed."""
        logger.info("NATS connection closed")
