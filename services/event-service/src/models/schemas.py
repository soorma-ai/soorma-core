from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from soorma_common.events import EventEnvelope

# Use EventEnvelope from shared library as the payload model
EventPayload = EventEnvelope


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
