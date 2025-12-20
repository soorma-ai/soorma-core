"""
Event Client for the Soorma SDK.

This module provides an EventClient class that connects to the Soorma Event Service
using Server-Sent Events (SSE) for real-time event streaming and HTTP for publishing.

The SDK abstracts away the underlying message bus (NATS, Kafka, etc.), providing
a clean interface for agents to publish and subscribe to events.

Usage:
    from soorma.events import EventClient

    # Create client
    client = EventClient(
        event_service_url="http://localhost:8082",
        agent_id="my-agent",
    )

    # Define event handlers
    @client.on_event("research.requested")
    async def handle_research(event):
        print(f"Got research request: {event['data']}")

    # Connect and start receiving events
    await client.connect(topics=["research.*", "action-requests"])

    # Publish events
    await client.publish(
        event_type="research.completed",
        topic="action-results",
        data={"result": "Analysis complete"},
    )
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

# Type alias for event handlers
EventHandler = Callable[[Dict[str, Any]], Awaitable[None]]


class EventClient:
    """
    Client for publishing and subscribing to events via the Soorma Event Service.
    
    This client:
    - Uses HTTP POST for publishing events
    - Uses SSE (Server-Sent Events) for real-time event subscription
    - Handles auto-reconnection with exponential backoff
    - Dispatches events to registered handlers
    
    Attributes:
        event_service_url: Base URL of the Event Service
        agent_id: Unique identifier for this agent
        source: Source identifier for published events (defaults to agent_id)
    """
    
    def __init__(
        self,
        event_service_url: str = "http://localhost:8082",
        agent_id: Optional[str] = None,
        source: Optional[str] = None,
        tenant_id: Optional[str] = None,
        session_id: Optional[str] = None,
        max_reconnect_attempts: int = -1,  # -1 = infinite
        reconnect_base_delay: float = 1.0,
        reconnect_max_delay: float = 60.0,
    ):
        """
        Initialize the EventClient.
        
        Args:
            event_service_url: Base URL of the Event Service (e.g., "http://localhost:8082")
            agent_id: Unique identifier for this agent (auto-generated if not provided)
            source: Source identifier for events (defaults to agent_id)
            tenant_id: Default tenant ID for multi-tenancy
            session_id: Default session ID for correlation
            max_reconnect_attempts: Max reconnection attempts (-1 for infinite)
            reconnect_base_delay: Initial delay between reconnection attempts (seconds)
            reconnect_max_delay: Maximum delay between reconnection attempts (seconds)
        """
        self.event_service_url = event_service_url.rstrip("/")
        self.agent_id = agent_id or f"agent-{str(uuid4())[:8]}"
        self.source = source or self.agent_id
        self.tenant_id = tenant_id
        self.session_id = session_id
        
        # Reconnection settings
        self._max_reconnect_attempts = max_reconnect_attempts
        self._reconnect_base_delay = reconnect_base_delay
        self._reconnect_max_delay = reconnect_max_delay
        
        # Connection state
        self._connected = False
        self._connection_id: Optional[str] = None
        self._subscribed_topics: List[str] = []
        self._stream_task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        
        # Event handlers: event_type -> list of handlers
        self._handlers: Dict[str, List[EventHandler]] = {}
        # Catch-all handlers (receive all events)
        self._catch_all_handlers: List[EventHandler] = []
        
        # HTTP client (lazy initialized)
        self._http_client = None
    
    # =========================================================================
    # Decorator for registering handlers
    # =========================================================================
    
    def on_event(self, event_type: str) -> Callable[[EventHandler], EventHandler]:
        """
        Decorator to register an event handler for a specific event type.
        
        Usage:
            @client.on_event("research.requested")
            async def handle_research(event):
                print(f"Received: {event}")
        
        Args:
            event_type: The event type to handle (e.g., "research.requested")
        
        Returns:
            Decorator function
        """
        def decorator(func: EventHandler) -> EventHandler:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(func)
            logger.debug(f"Registered handler for event type: {event_type}")
            return func
        return decorator
    
    def on_all_events(self, func: EventHandler) -> EventHandler:
        """
        Decorator to register a catch-all event handler.
        
        Usage:
            @client.on_all_events
            async def handle_all(event):
                print(f"Received: {event}")
        
        Args:
            func: The handler function
        
        Returns:
            The handler function
        """
        self._catch_all_handlers.append(func)
        logger.debug("Registered catch-all handler")
        return func
    
    # =========================================================================
    # Connection Management
    # =========================================================================
    
    async def connect(self, topics: List[str]) -> None:
        """
        Connect to the Event Service and start receiving events.
        
        This method:
        1. Establishes an SSE connection to the Event Service
        2. Subscribes to the specified topics
        3. Starts a background task to process incoming events
        
        Args:
            topics: List of topic patterns to subscribe to (e.g., ["research.*"])
        
        Raises:
            ConnectionError: If unable to connect to the Event Service
        """
        if self._connected:
            logger.warning("Already connected")
            return
        
        self._subscribed_topics = topics
        self._stop_event.clear()
        
        # Start the SSE stream task
        self._stream_task = asyncio.create_task(self._run_stream())
        
        # Wait briefly for connection to establish
        await asyncio.sleep(0.5)
        
        if not self._connected:
            logger.warning("Connection not yet established, will retry in background")
    
    async def disconnect(self) -> None:
        """
        Disconnect from the Event Service.
        
        This gracefully closes the SSE connection and stops the background task.
        """
        logger.info("Disconnecting from Event Service")
        
        self._stop_event.set()
        
        if self._stream_task:
            self._stream_task.cancel()
            try:
                await self._stream_task
            except asyncio.CancelledError:
                pass
            self._stream_task = None
        
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        
        self._connected = False
        self._connection_id = None
        logger.info("Disconnected from Event Service")
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to the Event Service."""
        return self._connected
    
    # =========================================================================
    # Publishing
    # =========================================================================
    
    async def publish(
        self,
        event_type: str,
        topic: str,
        data: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        subject: Optional[str] = None,
    ) -> str:
        """
        Publish an event to the Event Service.
        
        Args:
            event_type: Event type (e.g., "research.completed")
            topic: Target topic (e.g., "action-results")
            data: Event payload data
            correlation_id: Optional correlation ID for tracing
            subject: Optional subject/resource identifier
        
        Returns:
            The event ID
        
        Raises:
            ConnectionError: If unable to publish the event
        """
        await self._ensure_http_client()
        
        event_id = str(uuid4())
        
        event = {
            "id": event_id,
            "source": self.source,
            "specversion": "1.0",
            "type": event_type,
            "topic": topic,
            "time": datetime.now(timezone.utc).isoformat(),
            "data": data or {},
            "correlation_id": correlation_id or str(uuid4()),
        }
        
        # Add optional fields
        if subject:
            event["subject"] = subject
        if self.tenant_id:
            event["tenant_id"] = self.tenant_id
        if self.session_id:
            event["session_id"] = self.session_id
        
        url = f"{self.event_service_url}/v1/events/publish"
        
        try:
            response = await self._http_client.post(
                url,
                json={"event": event},
                timeout=30.0,
            )
            
            if response.status_code != 200:
                error_detail = response.text
                raise ConnectionError(f"Failed to publish event: {response.status_code} - {error_detail}")
            
            result = response.json()
            logger.debug(f"Published event {event_id} to {topic}")
            
            return result.get("event_id", event_id)
            
        except Exception as e:
            logger.error(f"Error publishing event: {e}")
            raise ConnectionError(f"Failed to publish event: {e}") from e
    
    # =========================================================================
    # SSE Stream Processing
    # =========================================================================
    
    async def _run_stream(self) -> None:
        """
        Main loop for the SSE stream.
        
        Handles connection, reconnection with exponential backoff, and event dispatch.
        """
        attempt = 0
        
        while not self._stop_event.is_set():
            try:
                await self._stream_events()
                # If we get here, connection closed gracefully
                if self._stop_event.is_set():
                    break
                attempt = 0  # Reset on successful connection
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._connected = False
                
                # Only log if there's meaningful error info
                error_msg = str(e).strip()
                if error_msg:
                    logger.warning(f"Stream connection issue: {error_msg}")
                else:
                    logger.debug("Stream disconnected, reconnecting...")
                
                # Check if we should retry
                if self._max_reconnect_attempts >= 0 and attempt >= self._max_reconnect_attempts:
                    logger.error("Max reconnection attempts reached")
                    break
                
                # Calculate backoff delay
                delay = min(
                    self._reconnect_base_delay * (2 ** attempt),
                    self._reconnect_max_delay,
                )
                
                # Only log reconnection on first few attempts to reduce noise
                if attempt < 3:
                    logger.debug(f"Reconnecting in {delay:.1f}s (attempt {attempt + 1})")
                
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=delay,
                    )
                    break  # Stop event was set
                except asyncio.TimeoutError:
                    pass  # Continue with retry
                
                attempt += 1
    
    async def _stream_events(self) -> None:
        """
        Connect to SSE stream and process events.
        """
        await self._ensure_http_client()
        
        topics_param = ",".join(self._subscribed_topics)
        # Pass source as agent_name for load balancing queue groups
        url = f"{self.event_service_url}/v1/events/stream?topics={topics_param}&agent_id={self.agent_id}&agent_name={self.source}"
        
        logger.info(f"Connecting to SSE stream: {url}")
        
        async with self._http_client.stream("GET", url) as response:
            if response.status_code != 200:
                raise ConnectionError(f"SSE connection failed: {response.status_code}")
            
            # Process SSE stream
            event_type = None
            data_lines: List[str] = []
            
            async for line in response.aiter_lines():
                if self._stop_event.is_set():
                    break
                
                line = line.strip()
                
                if not line:
                    # Empty line = end of event
                    if event_type and data_lines:
                        data = "\n".join(data_lines)
                        await self._handle_sse_event(event_type, data)
                    event_type = None
                    data_lines = []
                    continue
                
                if line.startswith("event:"):
                    event_type = line[6:].strip()
                elif line.startswith("data:"):
                    data_lines.append(line[5:].strip())
                # Ignore other fields (id, retry, etc.)
    
    async def _handle_sse_event(self, event_type: str, data: str) -> None:
        """
        Handle an SSE event.
        
        Args:
            event_type: SSE event type (e.g., "connected", "message", "heartbeat")
            data: Event data (JSON string)
        """
        try:
            parsed_data = json.loads(data)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse SSE data: {data}")
            return
        
        if event_type == "connected":
            self._connected = True
            self._connection_id = parsed_data.get("connection_id")
            logger.info(f"Connected to Event Service (connection_id: {self._connection_id})")
            
        elif event_type == "heartbeat":
            logger.debug("Received heartbeat")
            
        elif event_type == "message":
            # Dispatch to handlers
            await self._dispatch_event(parsed_data)
            
        elif event_type == "disconnected":
            self._connected = False
            logger.info("Received disconnect from Event Service")
            
        else:
            logger.debug(f"Unknown SSE event type: {event_type}")
    
    async def _dispatch_event(self, event: Dict[str, Any]) -> None:
        """
        Dispatch an event to registered handlers.
        
        Args:
            event: The event data
        """
        event_type = event.get("type", "")
        
        # Call specific handlers
        handlers = self._handlers.get(event_type, [])
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Error in handler for {event_type}: {e}")
        
        # Call catch-all handlers
        for handler in self._catch_all_handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Error in catch-all handler: {e}")
        
        if not handlers and not self._catch_all_handlers:
            logger.debug(f"No handlers for event type: {event_type}")
    
    # =========================================================================
    # HTTP Client Management
    # =========================================================================
    
    async def _ensure_http_client(self) -> None:
        """Ensure HTTP client is initialized."""
        if self._http_client is None:
            try:
                import httpx
            except ImportError:
                raise ImportError(
                    "httpx is required for EventClient. "
                    "Install it with: pip install httpx"
                )
            
            # Configure timeout for SSE streaming:
            # - connect: 10s for initial connection
            # - read: None (no timeout) for long-lived SSE streams
            # - write: 30s for publishing
            # - pool: None (no timeout) for connection pool
            timeout = httpx.Timeout(
                connect=10.0,
                read=None,  # SSE streams are long-lived
                write=30.0,
                pool=None,
            )
            
            self._http_client = httpx.AsyncClient(timeout=timeout)
    
    # =========================================================================
    # Context Manager Support
    # =========================================================================
    
    async def __aenter__(self) -> "EventClient":
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.disconnect()
