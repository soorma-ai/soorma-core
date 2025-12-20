import asyncio
import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional
from uuid import uuid4

from ..core.config import settings
from ..adapters.base import EventAdapter
from ..adapters.nats_adapter import NatsAdapter
from ..adapters.memory_adapter import MemoryAdapter

logger = logging.getLogger(__name__)

class EventManager:
    """
    Manages the event adapter and SSE connections.
    Singleton-like service that handles the lifecycle of the event bus connection.
    """
    
    def __init__(self):
        self.adapter: Optional[EventAdapter] = None
        # Active SSE connections: connection_id -> connection_data
        self.active_connections: Dict[str, Dict[str, Any]] = {}

    def _get_adapter(self) -> EventAdapter:
        """Factory function to create the appropriate adapter based on configuration."""
        adapter_type = settings.event_adapter.lower()
        
        if adapter_type == "nats":
            return NatsAdapter(
                url=settings.nats_url,
                reconnect_time_wait=settings.nats_reconnect_time_wait,
                max_reconnect_attempts=settings.nats_max_reconnect_attempts,
            )
        elif adapter_type == "memory":
            return MemoryAdapter()
        else:
            raise ValueError(f"Unknown adapter type: {adapter_type}")

    async def initialize(self):
        """Initialize and connect the adapter."""
        logger.info(f"Starting Event Service with {settings.event_adapter} adapter")
        self.adapter = self._get_adapter()
        
        try:
            await self.adapter.connect()
            logger.info(f"Event Service ready on port {settings.service_port}")
        except Exception as e:
            logger.error(f"Failed to connect adapter: {e}")
            # Continue anyway for graceful degradation in dev mode
            if not settings.debug:
                raise

    async def shutdown(self):
        """Shutdown adapter and close all connections."""
        logger.info("Shutting down Event Service")
        
        # Close all SSE connections
        for conn_id in list(self.active_connections.keys()):
            try:
                conn_data = self.active_connections.pop(conn_id, {})
                if "cancel_event" in conn_data:
                    conn_data["cancel_event"].set()
            except Exception as e:
                logger.warning(f"Error closing connection {conn_id}: {e}")
        
        # Disconnect adapter
        if self.adapter:
            await self.adapter.disconnect()
        
        logger.info("Event Service shutdown complete")

    async def publish(self, topic: str, message: Dict[str, Any]) -> str:
        """Publish an event."""
        if not self.adapter:
            raise RuntimeError("Event adapter not initialized")
        
        if not self.adapter.is_connected:
            raise RuntimeError("Event adapter not connected")
            
        await self.adapter.publish(topic, message)
        return topic

    async def create_stream(
        self, 
        topics: List[str], 
        agent_id: str,
        agent_name: Optional[str] = None,
        check_disconnected: Optional[callable] = None
    ) -> AsyncGenerator[Dict[str, str], None]:
        """
        Create an SSE stream generator.
        """
        if not self.adapter:
            raise RuntimeError("Event adapter not initialized")
        
        if not self.adapter.is_connected:
            raise RuntimeError("Event adapter not connected")
            
        # Generate connection ID
        connection_id = str(uuid4())
        
        logger.info(f"New SSE connection {connection_id} from agent {agent_id} (name: {agent_name}) for topics: {topics}")
        
        # Create a queue for this connection
        queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue(
            maxsize=settings.stream_max_queue_size
        )
        cancel_event = asyncio.Event()
        subscription_id: Optional[str] = None
        
        # Store connection info
        self.active_connections[connection_id] = {
            "agent_id": agent_id,
            "topics": topics,
            "queue": queue,
            "cancel_event": cancel_event,
        }
        
        try:
            # Message handler that puts messages in the queue
            async def queue_handler(topic: str, message: Dict[str, Any]) -> None:
                try:
                    # Don't block if queue is full (drop oldest messages)
                    if queue.full():
                        try:
                            queue.get_nowait()
                        except asyncio.QueueEmpty:
                            pass
                    await queue.put({"topic": topic, "message": message})
                except Exception as e:
                    logger.error(f"Error queuing message: {e}")
            
            # Subscribe to topics
            # Use agent_name as queue_group if provided, otherwise fallback to agent_id.
            # This enables load balancing across multiple instances of the same logical agent.
            queue_group = agent_name if agent_name else agent_id
            
            subscription_id = await self.adapter.subscribe(
                topics=topics,
                handler=queue_handler,
                subscription_id=connection_id,
                queue_group=queue_group,
            )
            
            logger.info(f"Subscription {subscription_id} active for connection {connection_id} [group: {queue_group}]")
            
            # Send initial connection event
            yield {
                "event": "connected",
                "data": json.dumps({
                    "connection_id": connection_id,
                    "topics": topics,
                    "agent_id": agent_id,
                }),
            }
            
            # Stream events from the queue
            heartbeat_interval = settings.stream_heartbeat_interval
            
            while not cancel_event.is_set():
                try:
                    # Check if client disconnected
                    if check_disconnected and await check_disconnected():
                        logger.info(f"Client {connection_id} disconnected")
                        break

                    # Wait for message with timeout (for heartbeat)
                    try:
                        item = await asyncio.wait_for(
                            queue.get(),
                            timeout=heartbeat_interval,
                        )
                        
                        # Yield the event
                        yield {
                            "event": "message",
                            "data": json.dumps(item["message"]),
                        }
                        
                    except asyncio.TimeoutError:
                        # Send heartbeat to keep connection alive
                        yield {
                            "event": "heartbeat",
                            "data": json.dumps({"connection_id": connection_id}),
                        }
                
                except asyncio.CancelledError:
                    logger.info(f"Stream cancelled for connection {connection_id}")
                    break
                except Exception as e:
                    logger.error(f"Error in event stream {connection_id}: {e}")
                    break
        
        finally:
            # Cleanup
            logger.info(f"Cleaning up connection {connection_id}")
            
            # Unsubscribe
            if subscription_id and self.adapter:
                try:
                    await self.adapter.unsubscribe(subscription_id)
                except Exception as e:
                    logger.warning(f"Error unsubscribing {subscription_id}: {e}")
            
            # Remove from active connections
            self.active_connections.pop(connection_id, None)
            
            # Send disconnect event (if possible)
            try:
                yield {
                    "event": "disconnected",
                    "data": json.dumps({"connection_id": connection_id}),
                }
            except Exception:
                pass

# Global instance
event_manager = EventManager()
