"""
In-memory adapter for the Event Service.

This adapter is primarily used for:
- Local development without external dependencies
- Unit testing
- Demo purposes

Messages are stored in memory and delivered to subscribers synchronously.
"""
import asyncio
import fnmatch
import logging
from typing import Any, Dict, List, Set
from uuid import uuid4

from .base import EventAdapter, MessageHandler, PublishError

logger = logging.getLogger(__name__)


class MemoryAdapter(EventAdapter):
    """
    In-memory event adapter for development and testing.
    
    This adapter simulates a message bus by maintaining subscriptions
    in memory and delivering messages directly to handlers.
    
    Features:
    - Wildcard pattern matching (e.g., "research.*", "events.*")
    - Synchronous delivery (messages delivered immediately)
    - No persistence (messages not stored)
    """
    
    def __init__(self):
        """Initialize the memory adapter."""
        self._connected = False
        self._subscriptions: Dict[str, Dict[str, Any]] = {}
        # Pattern -> Set of subscription IDs
        self._pattern_subs: Dict[str, Set[str]] = {}
        # Queue group -> List of subscription IDs (for round-robin)
        self._queue_groups: Dict[str, List[str]] = {}
        # Queue group -> Current index (for round-robin)
        self._queue_group_cursors: Dict[str, int] = {}
    
    async def connect(self) -> None:
        """Mark adapter as connected."""
        if self._connected:
            logger.warning("Memory adapter already connected")
            return
        
        self._connected = True
        logger.info("Memory adapter connected (in-memory mode)")
    
    async def disconnect(self) -> None:
        """Disconnect and clean up subscriptions."""
        self._subscriptions.clear()
        self._pattern_subs.clear()
        self._connected = False
        logger.info("Memory adapter disconnected")
    
    async def publish(self, topic: str, message: Dict[str, Any]) -> None:
        """
        Publish a message to matching subscribers.
        
        Messages are delivered synchronously to all matching handlers.
        
        Args:
            topic: The topic to publish to
            message: The message payload
        """
        if not self._connected:
            raise ConnectionError("Memory adapter not connected")
        
        logger.debug(f"Publishing to topic: {topic}")
        
        # Find all matching subscriptions
        matching_subs = self._find_matching_subscriptions(topic)
        
        if not matching_subs:
            logger.debug(f"No subscribers for topic: {topic}")
            return
        
        # Group subscriptions by queue group
        # None key is for subscribers without a queue group (broadcast)
        grouped_subs: Dict[str | None, List[str]] = {None: []}
        
        for sub_id in matching_subs:
            if sub_id in self._subscriptions:
                q_group = self._subscriptions[sub_id].get("queue_group")
                if q_group:
                    if q_group not in grouped_subs:
                        grouped_subs[q_group] = []
                    grouped_subs[q_group].append(sub_id)
                else:
                    grouped_subs[None].append(sub_id)
        
        # Determine final list of subscribers to deliver to
        final_subs = []
        
        # 1. Broadcast to all non-queue-group subscribers
        final_subs.extend(grouped_subs[None])
        
        # 2. Round-robin for each queue group
        for q_group, sub_ids in grouped_subs.items():
            if q_group is None:
                continue
                
            # Sort sub_ids to ensure deterministic order for round-robin
            # (though in memory adapter, order in list is usually insertion order)
            # We need to pick ONE from this list based on global cursor for this group
            
            # Note: The simple cursor approach in __init__ is global per group, 
            # but here we have a subset of subs that match the topic.
            # To keep it simple and effective for testing:
            # We'll use the global cursor to pick the next sub_id from the *available matching* subs.
            
            if not sub_ids:
                continue
                
            cursor = self._queue_group_cursors.get(q_group, 0)
            selected_index = cursor % len(sub_ids)
            selected_sub = sub_ids[selected_index]
            final_subs.append(selected_sub)
            
            # Advance cursor
            self._queue_group_cursors[q_group] = cursor + 1
        
        # Deliver to selected handlers
        delivery_tasks = []
        for sub_id in final_subs:
            if sub_id in self._subscriptions:
                handler = self._subscriptions[sub_id]["handler"]
                delivery_tasks.append(self._deliver_message(handler, topic, message))
        
        # Wait for all deliveries to complete
        if delivery_tasks:
            results = await asyncio.gather(*delivery_tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Error delivering message: {result}")
    
    async def subscribe(
        self,
        topics: List[str],
        handler: MessageHandler,
        subscription_id: str | None = None,
        queue_group: str | None = None,
    ) -> str:
        """
        Subscribe to topics with pattern matching support.
        
        Supports wildcards:
        - "*" matches a single segment (e.g., "research.*" matches "research.requested")
        - ">" matches any remaining segments (e.g., "events.>" matches "events.a.b.c")
        
        Args:
            topics: List of topic patterns
            handler: Async callback function
            subscription_id: Optional subscription identifier
            queue_group: Optional queue group (ignored in memory adapter)
        
        Returns:
            Subscription ID
        """
        if not self._connected:
            raise ConnectionError("Memory adapter not connected")
        
        if queue_group:
            # logger.warning("Queue groups are not fully supported in MemoryAdapter (broadcast only)")
            pass

        sub_id = subscription_id or str(uuid4())
        
        self._subscriptions[sub_id] = {
            "patterns": topics,
            "handler": handler,
            "queue_group": queue_group,
        }
        
        # Index patterns for efficient matching
        for pattern in topics:
            if pattern not in self._pattern_subs:
                self._pattern_subs[pattern] = set()
            self._pattern_subs[pattern].add(sub_id)
        
        # Add to queue group if specified
        if queue_group:
            if queue_group not in self._queue_groups:
                self._queue_groups[queue_group] = []
                self._queue_group_cursors[queue_group] = 0
            self._queue_groups[queue_group].append(sub_id)
        
        logger.info(f"Subscribed to {topics} (sub_id: {sub_id})")
        return sub_id
    
    async def unsubscribe(self, subscription_id: str) -> None:
        """Unsubscribe from a subscription."""
        if subscription_id not in self._subscriptions:
            logger.warning(f"Subscription {subscription_id} not found")
            return
        
        sub_data = self._subscriptions.pop(subscription_id)
        
        # Remove from pattern index
        for pattern in sub_data["patterns"]:
            if pattern in self._pattern_subs:
                self._pattern_subs[pattern].discard(subscription_id)
                if not self._pattern_subs[pattern]:
                    del self._pattern_subs[pattern]
        
        # Remove from queue group
        queue_group = sub_data.get("queue_group")
        if queue_group and queue_group in self._queue_groups:
            if subscription_id in self._queue_groups[queue_group]:
                self._queue_groups[queue_group].remove(subscription_id)
                if not self._queue_groups[queue_group]:
                    del self._queue_groups[queue_group]
                    del self._queue_group_cursors[queue_group]
        
        logger.info(f"Unsubscribed: {subscription_id}")
    
    @property
    def is_connected(self) -> bool:
        """Check if adapter is connected."""
        return self._connected
    
    def _find_matching_subscriptions(self, topic: str) -> Set[str]:
        """
        Find all subscriptions that match a topic.
        
        Supports NATS-style wildcards:
        - "*" matches exactly one token
        - ">" matches one or more tokens (only at end)
        
        Args:
            topic: The topic to match against
        
        Returns:
            Set of matching subscription IDs
        """
        matching = set()
        
        for pattern, sub_ids in self._pattern_subs.items():
            if self._pattern_matches(pattern, topic):
                matching.update(sub_ids)
        
        return matching
    
    def _pattern_matches(self, pattern: str, topic: str) -> bool:
        """
        Check if a pattern matches a topic.
        
        Args:
            pattern: Pattern with optional wildcards
            topic: Topic to match
        
        Returns:
            True if pattern matches topic
        """
        # Exact match
        if pattern == topic:
            return True
        
        # Handle NATS-style wildcards
        pattern_parts = pattern.split(".")
        topic_parts = topic.split(".")
        
        # ">" matches any remaining segments
        if pattern_parts[-1] == ">":
            # Pattern without ">" must match the beginning
            prefix_pattern = pattern_parts[:-1]
            if len(topic_parts) < len(prefix_pattern):
                return False
            for i, p in enumerate(prefix_pattern):
                if p != "*" and p != topic_parts[i]:
                    return False
            return True
        
        # Must have same number of parts for "*" matching
        if len(pattern_parts) != len(topic_parts):
            return False
        
        # Match each part
        for p, t in zip(pattern_parts, topic_parts):
            if p != "*" and p != t:
                return False
        
        return True
    
    async def _deliver_message(
        self,
        handler: MessageHandler,
        topic: str,
        message: Dict[str, Any],
    ) -> None:
        """Deliver a message to a handler."""
        try:
            await handler(topic, message)
        except Exception as e:
            logger.error(f"Handler error for topic {topic}: {e}")
            raise
