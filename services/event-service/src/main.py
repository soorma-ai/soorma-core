"""
Event Service - Main FastAPI Application

This service acts as a smart proxy/gateway between Soorma agents and the
underlying message bus (NATS, Kafka, Google Pub/Sub).

Key Features:
- REST API for publishing events
- Server-Sent Events (SSE) for real-time event streaming
- Adapter pattern for backend flexibility
- CloudEvents-compliant event format
"""
import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, List
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from .config import settings
from .adapters import EventAdapter, NatsAdapter, MemoryAdapter

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global adapter instance
adapter: EventAdapter | None = None

# Active SSE connections: connection_id -> connection_data
active_connections: Dict[str, Dict[str, Any]] = {}


# =============================================================================
# Request/Response Models (API-specific)
# =============================================================================


class EventPayload(BaseModel):
    """Event payload for publishing."""
    id: str = Field(default_factory=lambda: str(uuid4()), description="Event ID")
    source: str = Field(..., description="Source agent/service ID")
    type: str = Field(..., description="Event type (e.g., 'research.requested')")
    topic: str = Field(..., description="Target topic")
    data: Dict[str, Any] | None = Field(default=None, description="Event payload")
    correlation_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Correlation ID for tracing"
    )
    time: str | None = Field(default=None, description="ISO 8601 timestamp")
    specversion: str = Field(default="1.0", description="CloudEvents spec version")
    subject: str | None = Field(default=None, description="Event subject")
    tenant_id: str | None = Field(default=None, description="Tenant ID")
    session_id: str | None = Field(default=None, description="Session ID")


class PublishRequest(BaseModel):
    """Request to publish an event."""
    event: EventPayload = Field(..., description="Event to publish")


class PublishResponse(BaseModel):
    """Response after publishing an event."""
    success: bool = Field(..., description="Whether publish succeeded")
    event_id: str = Field(..., description="Published event ID")
    message: str = Field(default="", description="Status message")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service status")
    adapter: str = Field(..., description="Active adapter type")
    connected: bool = Field(..., description="Whether adapter is connected")
    active_streams: int = Field(..., description="Number of active SSE streams")


# =============================================================================
# Application Lifecycle
# =============================================================================


def get_adapter() -> EventAdapter:
    """
    Factory function to create the appropriate adapter based on configuration.
    """
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


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.
    
    Handles startup (connect to message bus) and shutdown (cleanup).
    """
    global adapter
    
    # Startup
    logger.info(f"Starting Event Service with {settings.event_adapter} adapter")
    adapter = get_adapter()
    
    try:
        await adapter.connect()
        logger.info(f"Event Service ready on port {settings.service_port}")
    except Exception as e:
        logger.error(f"Failed to connect adapter: {e}")
        # Continue anyway for graceful degradation in dev mode
        if not settings.debug:
            raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Event Service")
    
    # Close all SSE connections
    for conn_id in list(active_connections.keys()):
        try:
            conn_data = active_connections.pop(conn_id, {})
            if "cancel_event" in conn_data:
                conn_data["cancel_event"].set()
        except Exception as e:
            logger.warning(f"Error closing connection {conn_id}: {e}")
    
    # Disconnect adapter
    if adapter:
        await adapter.disconnect()
    
    logger.info("Event Service shutdown complete")


# =============================================================================
# FastAPI Application
# =============================================================================


app = FastAPI(
    title="Soorma Event Service",
    description="Event proxy/gateway for the Soorma DisCo platform",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Health & Info Endpoints
# =============================================================================


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """
    Health check endpoint.
    
    Returns service status, adapter connection state, and active streams count.
    """
    return HealthResponse(
        status="healthy" if adapter and adapter.is_connected else "degraded",
        adapter=adapter.name if adapter else "none",
        connected=adapter.is_connected if adapter else False,
        active_streams=len(active_connections),
    )


@app.get("/", tags=["Info"])
async def root() -> Dict[str, str]:
    """Root endpoint with service info."""
    return {
        "service": "soorma-event-service",
        "version": "0.1.0",
        "docs": "/docs",
    }


# =============================================================================
# Publish Endpoint
# =============================================================================


@app.post("/v1/events/publish", response_model=PublishResponse, tags=["Events"])
async def publish_event(request: PublishRequest) -> PublishResponse:
    """
    Publish an event to the message bus.
    
    The event is validated and forwarded to the configured adapter (NATS, etc.).
    
    Args:
        request: PublishRequest containing the event envelope
    
    Returns:
        PublishResponse with success status and event ID
    """
    if not adapter:
        raise HTTPException(status_code=503, detail="Event adapter not initialized")
    
    if not adapter.is_connected:
        raise HTTPException(status_code=503, detail="Event adapter not connected")
    
    event = request.event
    
    try:
        # Build the message payload
        message = event.model_dump(exclude_none=True)
        
        # Publish to the adapter
        await adapter.publish(event.topic, message)
        
        logger.info(f"Published event {event.id} to topic {event.topic}")
        
        return PublishResponse(
            success=True,
            event_id=event.id,
            message=f"Event published to {event.topic}",
        )
    except Exception as e:
        logger.error(f"Failed to publish event: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to publish event: {str(e)}",
        )


# =============================================================================
# SSE Stream Endpoint
# =============================================================================


@app.get("/v1/events/stream", tags=["Events"])
async def stream_events(
    request: Request,
    topics: str = Query(
        ...,
        description="Comma-separated list of topics to subscribe to (supports wildcards)"
    ),
    agent_id: str = Query(
        ...,
        description="ID of the subscribing agent"
    ),
) -> EventSourceResponse:
    """
    Subscribe to events via Server-Sent Events (SSE).
    
    This endpoint establishes a long-lived HTTP connection that streams
    events matching the specified topics in real-time.
    
    Query Parameters:
        topics: Comma-separated topic patterns (e.g., "research.*,billing.alert")
        agent_id: Identifier for the subscribing agent
    
    Returns:
        SSE stream with event messages in JSON format
    
    Example:
        GET /v1/events/stream?topics=research.*,action-results&agent_id=my-agent
        
        Response (SSE format):
        event: message
        data: {"id": "...", "type": "research.completed", "data": {...}}
    """
    if not adapter:
        raise HTTPException(status_code=503, detail="Event adapter not initialized")
    
    if not adapter.is_connected:
        raise HTTPException(status_code=503, detail="Event adapter not connected")
    
    # Parse topics
    topic_list = [t.strip() for t in topics.split(",") if t.strip()]
    if not topic_list:
        raise HTTPException(status_code=400, detail="At least one topic is required")
    
    # Generate connection ID
    connection_id = str(uuid4())
    
    logger.info(f"New SSE connection {connection_id} from agent {agent_id} for topics: {topic_list}")
    
    async def event_generator() -> AsyncGenerator[Dict[str, str], None]:
        """
        Generator that yields events from the message queue.
        
        This creates an asyncio.Queue, subscribes to the requested topics,
        and yields messages as they arrive.
        """
        # Create a queue for this connection
        queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue(
            maxsize=settings.stream_max_queue_size
        )
        cancel_event = asyncio.Event()
        subscription_id: str | None = None
        
        # Store connection info
        active_connections[connection_id] = {
            "agent_id": agent_id,
            "topics": topic_list,
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
            subscription_id = await adapter.subscribe(
                topics=topic_list,
                handler=queue_handler,
                subscription_id=connection_id,
            )
            
            logger.info(f"Subscription {subscription_id} active for connection {connection_id}")
            
            # Send initial connection event
            yield {
                "event": "connected",
                "data": json.dumps({
                    "connection_id": connection_id,
                    "topics": topic_list,
                    "agent_id": agent_id,
                }),
            }
            
            # Stream events from the queue
            heartbeat_interval = settings.stream_heartbeat_interval
            
            while not cancel_event.is_set():
                try:
                    # Check if client disconnected
                    if await request.is_disconnected():
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
            if subscription_id and adapter:
                try:
                    await adapter.unsubscribe(subscription_id)
                except Exception as e:
                    logger.warning(f"Error unsubscribing {subscription_id}: {e}")
            
            # Remove from active connections
            active_connections.pop(connection_id, None)
            
            # Send disconnect event (if possible)
            try:
                yield {
                    "event": "disconnected",
                    "data": json.dumps({"connection_id": connection_id}),
                }
            except Exception:
                pass
    
    return EventSourceResponse(event_generator())


# =============================================================================
# Admin/Debug Endpoints (protected in production)
# =============================================================================


@app.get("/v1/admin/connections", tags=["Admin"])
async def list_connections() -> Dict[str, Any]:
    """
    List all active SSE connections.
    
    Note: This endpoint should be protected in production.
    """
    return {
        "count": len(active_connections),
        "connections": [
            {
                "connection_id": conn_id,
                "agent_id": data.get("agent_id"),
                "topics": data.get("topics"),
            }
            for conn_id, data in active_connections.items()
        ],
    }


# =============================================================================
# Error Handlers
# =============================================================================


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return {
        "error": "Internal server error",
        "detail": str(exc) if settings.debug else "An unexpected error occurred",
    }
