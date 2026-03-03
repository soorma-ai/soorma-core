"""NATS client for soorma-nats library.

GREEN PHASE: Real nats-py implementation.
Adapted from services/event-service/src/adapters/nats_adapter.py.
"""

import json
import logging
from typing import Awaitable, Callable, Dict, List
from uuid import uuid4

import nats
from nats.aio.client import Client as NatsClient
from nats.aio.msg import Msg

from soorma_nats.exceptions import NATSConnectionError, NATSSubscriptionError

logger = logging.getLogger(__name__)

# Type alias for async message callback
MessageCallback = Callable[[str, dict], Awaitable[None]]
"""Async callback: (subject: str, message: dict) -> None"""


class NATSClient:
    """Lightweight NATS client for Soorma infrastructure services.

    Wraps nats-py with:
    - Auto-reconnection (infinite retries by default)
    - JSON message deserialization
    - Subject namespace (soorma.events.*)
    - Graceful drain-and-disconnect on shutdown

    Subject mapping: topic -> ``soorma.events.<topic>``
    Example: ``action-requests`` -> ``soorma.events.action-requests``

    Usage::

        client = NATSClient(url="nats://localhost:4222")
        await client.connect()

        async def on_message(subject: str, message: dict) -> None:
            print(subject, message)

        await client.subscribe(
            topics=["action-requests"],
            callback=on_message,
            queue_group="my-service",
        )

        await client.disconnect()
    """

    SUBJECT_PREFIX = "soorma.events."

    def __init__(
        self,
        url: str = "nats://localhost:4222",
        reconnect_time_wait: int = 2,
        max_reconnect_attempts: int = -1,
    ) -> None:
        """Initialise NATSClient.

        Args:
            url: NATS server URL.
            reconnect_time_wait: Seconds between reconnection attempts.
            max_reconnect_attempts: Max reconnection attempts (-1 = infinite).
        """
        self._url = url
        self._reconnect_time_wait = reconnect_time_wait
        self._max_reconnect_attempts = max_reconnect_attempts
        # Internal nats-py client — None until connect() is called
        self._client: NatsClient | None = None
        # Track subscriptions: "{sub_id}:{subject}" -> nats Subscription
        self._subscriptions: Dict[str, object] = {}

    async def connect(self) -> None:
        """Connect to NATS server with auto-reconnection.

        Raises:
            NATSConnectionError: If initial connection fails.
        """
        if self._client is not None and self._client.is_connected:
            logger.warning("NATSClient: already connected to NATS")
            return

        logger.info(f"NATSClient: connecting to NATS at {self._url}")

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
            logger.info(f"NATSClient: connected to {self._client.connected_url}")
        except Exception as exc:
            logger.error(f"NATSClient: failed to connect to NATS: {exc}")
            raise NATSConnectionError(
                f"Failed to connect to NATS at {self._url}: {exc}"
            ) from exc

    async def subscribe(
        self,
        topics: List[str],
        callback: MessageCallback,
        queue_group: str | None = None,
    ) -> str:
        """Subscribe to one or more topics.

        Each topic is mapped to ``soorma.events.<topic>`` before subscribing.
        Messages are JSON-decoded and passed to *callback* as
        ``(subject, dict)``.

        Args:
            topics: List of topic names (e.g. ``["action-requests"]``).
            callback: Async function called with ``(subject, message)`` for
                each received message.
            queue_group: Optional NATS queue group for load balancing across
                multiple service instances.

        Returns:
            Subscription ID string.

        Raises:
            NATSConnectionError: If not connected.
            NATSSubscriptionError: If subscription fails.
        """
        if not self.is_connected:
            raise NATSConnectionError("Not connected to NATS. Call connect() first.")

        sub_id = str(uuid4())

        # Build a NATS message handler wrapping the user's callback
        async def _nats_handler(msg: Msg) -> None:
            try:
                # Decode subject -> topic for the callback
                topic = self._subject_to_topic(msg.subject)
                message = json.loads(msg.data.decode("utf-8"))
                await callback(msg.subject, message)
            except json.JSONDecodeError as exc:
                logger.error(
                    f"NATSClient: failed to decode JSON from {msg.subject}: {exc}"
                )
            except Exception as exc:
                logger.error(
                    f"NATSClient: error in message handler for {msg.subject}: {exc}"
                )

        for topic in topics:
            subject = self._topic_to_subject(topic)
            try:
                sub = await self._client.subscribe(
                    subject,
                    cb=_nats_handler,
                    queue=queue_group or "",
                )
                self._subscriptions[f"{sub_id}:{subject}"] = sub

                log_msg = f"NATSClient: subscribed to {subject}"
                if queue_group:
                    log_msg += f" [queue group: {queue_group}]"
                logger.info(log_msg)

            except Exception as exc:
                logger.error(f"NATSClient: failed to subscribe to {subject}: {exc}")
                # Clean up any subscriptions created in this batch
                await self._cleanup_partial_subscription(sub_id)
                raise NATSSubscriptionError(
                    f"Failed to subscribe to {subject}: {exc}"
                ) from exc

        return sub_id

    async def unsubscribe(self, subscription_id: str) -> None:
        """Unsubscribe from a previously created subscription.

        Args:
            subscription_id: The ID returned by :meth:`subscribe`.
        """
        keys = [k for k in self._subscriptions if k.startswith(f"{subscription_id}:")]
        if not keys:
            logger.warning(f"NATSClient: no subscriptions found for id={subscription_id}")
            return

        for key in keys:
            sub = self._subscriptions.pop(key)
            try:
                await sub.unsubscribe()
                logger.info(f"NATSClient: unsubscribed {key}")
            except Exception as exc:
                logger.warning(f"NATSClient: error unsubscribing {key}: {exc}")

    async def disconnect(self) -> None:
        """Drain all subscriptions and disconnect from NATS.

        Safe to call even if not connected.
        """
        if self._client is None:
            return

        logger.info("NATSClient: disconnecting from NATS")

        # Drain and close (gracefully flushes in-flight messages)
        try:
            await self._client.drain()
        except Exception as exc:
            logger.warning(f"NATSClient: error draining NATS connection: {exc}")

        self._client = None
        self._subscriptions.clear()
        logger.info("NATSClient: disconnected")

    @property
    def is_connected(self) -> bool:
        """Return True if connected to NATS server."""
        return self._client is not None and self._client.is_connected

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _topic_to_subject(self, topic: str) -> str:
        """Convert a topic name to a NATS subject.

        Args:
            topic: Topic name (e.g. ``"action-requests"``).

        Returns:
            NATS subject (e.g. ``"soorma.events.action-requests"``).
        """
        if topic.startswith(self.SUBJECT_PREFIX):
            return topic
        return f"{self.SUBJECT_PREFIX}{topic}"

    def _subject_to_topic(self, subject: str) -> str:
        """Convert a NATS subject back to a topic name.

        Args:
            subject: NATS subject (e.g. ``"soorma.events.action-requests"``).

        Returns:
            Topic name (e.g. ``"action-requests"``).
        """
        return subject.removeprefix(self.SUBJECT_PREFIX)

    async def _cleanup_partial_subscription(self, sub_id: str) -> None:
        """Remove any subscriptions created under a given sub_id prefix.

        Called on error during subscribe() to avoid dangling subscriptions.

        Args:
            sub_id: Subscription ID prefix to clean up.
        """
        keys = [k for k in list(self._subscriptions) if k.startswith(f"{sub_id}:")]
        for key in keys:
            sub = self._subscriptions.pop(key, None)
            if sub:
                try:
                    await sub.unsubscribe()
                except Exception:
                    pass

    # ------------------------------------------------------------------
    # NATS connection lifecycle callbacks
    # ------------------------------------------------------------------

    async def _error_callback(self, exc: Exception) -> None:
        """Log NATS client errors."""
        logger.error(f"NATSClient: NATS error: {exc}")

    async def _disconnected_callback(self) -> None:
        """Log NATS disconnection."""
        logger.warning("NATSClient: disconnected from NATS")

    async def _reconnected_callback(self) -> None:
        """Log NATS reconnection."""
        logger.info("NATSClient: reconnected to NATS")

    async def _closed_callback(self) -> None:
        """Log NATS connection closed."""
        logger.info("NATSClient: NATS connection closed")
