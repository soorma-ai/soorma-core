"""
Event DTOs for Soorma platform event-driven architecture.

This module defines CloudEvents-compliant event envelopes and topic-specific
event types for the DisCo (Distributed Cognition) pattern.

Based on the adapter pattern, agents interact with events through the Event Service
proxy rather than directly with the underlying message bus (NATS/Kafka/PubSub).
"""
from typing import Any, Dict, Optional, List
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import Field, model_validator

from .models import BaseDTO


class EventTopic(str, Enum):
    """
    PubSub topics for different event types in the Soorma platform.
    
    This enum defines stable, well-defined topics. Adding new topics requires
    code changes to ensure proper topic-specific event DTO implementations exist.
    """
    # Core DisCo topics
    BUSINESS_FACTS = "business-facts"         # General business facts/observations
    ACTION_REQUESTS = "action-requests"       # Requests for agent actions
    ACTION_RESULTS = "action-results"         # Results from agent actions
    
    # System topics
    BILLING_EVENTS = "billing-events"         # Usage/cost tracking
    NOTIFICATION_EVENTS = "notification-events"  # User notifications
    SYSTEM_EVENTS = "system-events"           # Platform lifecycle events
    
    # Plan orchestration topics
    PLAN_EVENTS = "plan-events"               # Plan creation/updates
    TASK_EVENTS = "task-events"               # Task lifecycle events


class EventEnvelope(BaseDTO):
    """
    CloudEvents-compliant event envelope for all Soorma platform events.
    
    This envelope wraps every message flowing through the Event Service,
    providing standard metadata for tracing, routing, and correlation.
    
    Follows CloudEvents spec v1.0: https://github.com/cloudevents/spec
    
    Fields:
        id: Unique identifier for this event (UUID)
        source: Agent ID or service that produced this event
        specversion: CloudEvents spec version (always "1.0")
        type: Event type (e.g., "research.requested", "order.created")
        time: ISO 8601 timestamp when the event was created
        data: The event payload (arbitrary JSON object)
        correlation_id: Trace ID for request correlation across services
        topic: The destination topic for this event
        subject: Optional subject/resource this event pertains to
    """
    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for this event (UUID)"
    )
    source: str = Field(
        ..., 
        description="Agent ID or service that produced this event"
    )
    specversion: str = Field(
        default="1.0",
        description="CloudEvents spec version"
    )
    type: str = Field(
        ..., 
        description="Event type (e.g., 'research.requested')"
    )
    time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="ISO 8601 timestamp when the event was created"
    )
    data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="The event payload data"
    )
    correlation_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Trace ID for request correlation"
    )
    topic: EventTopic = Field(
        ...,
        description="The destination topic for this event"
    )
    subject: Optional[str] = Field(
        default=None,
        description="Optional subject/resource this event pertains to"
    )
    
    # Additional Soorma-specific metadata
    tenant_id: Optional[str] = Field(
        default=None,
        description="Tenant ID for multi-tenancy"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Session ID for conversation/workflow correlation"
    )
    
    # Response routing (DisCo pattern)
    response_event: Optional[str] = Field(
        default=None,
        description="Event type the callee should use for response (caller-specified)"
    )
    response_topic: Optional[str] = Field(
        default=None,
        description="Topic for response (defaults to action-results if not specified)"
    )
    
    # Distributed tracing
    trace_id: Optional[str] = Field(
        default=None,
        description="Root trace ID for entire workflow"
    )
    parent_event_id: Optional[str] = Field(
        default=None,
        description="ID of parent event in trace tree"
    )
    
    # Schema reference
    payload_schema_name: Optional[str] = Field(
        default=None,
        description="Registered schema name for payload (enables dynamic schema lookup)"
    )
    
    def to_cloudevents_dict(self) -> Dict[str, Any]:
        """
        Convert to CloudEvents JSON format.
        
        Returns a dictionary with CloudEvents standard field names.
        """
        result = {
            "id": self.id,
            "source": self.source,
            "specversion": self.specversion,
            "type": self.type,
            "time": self.time.isoformat(),
            "data": self.data,
        }
        
        # Add optional fields if present
        if self.correlation_id:
            result["correlationid"] = self.correlation_id
        if self.subject:
            result["subject"] = self.subject
        if self.tenant_id:
            result["tenantid"] = self.tenant_id
        if self.session_id:
            result["sessionid"] = self.session_id
        if self.topic:
            result["topic"] = self.topic.value
        if self.response_event:
            result["responseevent"] = self.response_event
        if self.response_topic:
            result["responsetopic"] = self.response_topic
        if self.trace_id:
            result["traceid"] = self.trace_id
        if self.parent_event_id:
            result["parenteventid"] = self.parent_event_id
        if self.payload_schema_name:
            result["payloadschemaname"] = self.payload_schema_name
            
        return result


class ActionRequestEvent(EventEnvelope):
    """
    Event schema for action requests in agentic orchestration.
    
    Used when a planner or agent requests another agent to perform an action.
    Topic is fixed to ACTION_REQUESTS.
    """
    topic: EventTopic = Field(
        default=EventTopic.ACTION_REQUESTS,
        description="PubSub topic (fixed to ACTION_REQUESTS)"
    )
    plan_id: Optional[str] = Field(
        default=None,
        description="Plan execution ID this action belongs to"
    )
    caused_by: Optional[str] = Field(
        default=None,
        description="Event ID that triggered this action request"
    )
    callback_url: Optional[str] = Field(
        default=None,
        description="Optional callback URL for reporting action results"
    )
    
    @model_validator(mode='before')
    @classmethod
    def set_topic(cls, data: Any) -> Any:
        """Ensure topic is always ACTION_REQUESTS."""
        if isinstance(data, dict):
            data['topic'] = EventTopic.ACTION_REQUESTS
        return data


class ActionResultEvent(EventEnvelope):
    """
    Event schema for action results (responses to action requests).
    
    Topic is fixed to ACTION_RESULTS.
    """
    topic: EventTopic = Field(
        default=EventTopic.ACTION_RESULTS,
        description="PubSub topic (fixed to ACTION_RESULTS)"
    )
    action_event_id: str = Field(
        ...,
        description="ID of the original action request event"
    )
    plan_id: Optional[str] = Field(
        default=None,
        description="Plan execution ID"
    )
    success: bool = Field(
        ...,
        description="Whether the action completed successfully"
    )
    result: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Result data from action execution"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if action failed"
    )
    completed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the action was completed"
    )
    
    @model_validator(mode='before')
    @classmethod
    def set_topic(cls, data: Any) -> Any:
        """Ensure topic is always ACTION_RESULTS."""
        if isinstance(data, dict):
            data['topic'] = EventTopic.ACTION_RESULTS
        return data


class BusinessFactEvent(EventEnvelope):
    """
    Event schema for business fact announcements.
    
    Used for publishing observations, state changes, or facts about
    the business domain. Topic is fixed to BUSINESS_FACTS.
    """
    topic: EventTopic = Field(
        default=EventTopic.BUSINESS_FACTS,
        description="PubSub topic (fixed to BUSINESS_FACTS)"
    )
    
    @model_validator(mode='before')
    @classmethod
    def set_topic(cls, data: Any) -> Any:
        """Ensure topic is always BUSINESS_FACTS."""
        if isinstance(data, dict):
            data['topic'] = EventTopic.BUSINESS_FACTS
        return data


class BillingEvent(EventEnvelope):
    """
    Event schema for billing/usage tracking.
    
    Topic is fixed to BILLING_EVENTS.
    """
    topic: EventTopic = Field(
        default=EventTopic.BILLING_EVENTS,
        description="PubSub topic (fixed to BILLING_EVENTS)"
    )
    unit_of_work: str = Field(
        ...,
        description="Description of work unit completed"
    )
    cost: float = Field(
        ...,
        description="Cost associated with this work unit"
    )
    currency: str = Field(
        default="USD",
        description="Currency for the cost"
    )
    
    @model_validator(mode='before')
    @classmethod
    def set_topic(cls, data: Any) -> Any:
        """Ensure topic is always BILLING_EVENTS."""
        if isinstance(data, dict):
            data['topic'] = EventTopic.BILLING_EVENTS
        return data


class NotificationEvent(EventEnvelope):
    """
    Event schema for user notifications.
    
    Topic is fixed to NOTIFICATION_EVENTS.
    """
    topic: EventTopic = Field(
        default=EventTopic.NOTIFICATION_EVENTS,
        description="PubSub topic (fixed to NOTIFICATION_EVENTS)"
    )
    message: str = Field(
        ...,
        description="Notification message for user"
    )
    priority: str = Field(
        default="normal",
        description="Priority level (low, normal, high, urgent)"
    )
    channel: str = Field(
        default="email",
        description="Notification channel (email, sms, push)"
    )
    
    @model_validator(mode='before')
    @classmethod
    def set_topic(cls, data: Any) -> Any:
        """Ensure topic is always NOTIFICATION_EVENTS."""
        if isinstance(data, dict):
            data['topic'] = EventTopic.NOTIFICATION_EVENTS
        return data


# =============================================================================
# Event Service API DTOs
# =============================================================================


class PublishRequest(BaseDTO):
    """Request to publish an event through the Event Service."""
    event: EventEnvelope = Field(
        ...,
        description="The event envelope to publish"
    )


class PublishResponse(BaseDTO):
    """Response after publishing an event."""
    success: bool = Field(..., description="Whether publish was successful")
    event_id: str = Field(..., description="ID of the published event")
    message: str = Field(default="", description="Status message")


class SubscribeRequest(BaseDTO):
    """Request to subscribe to event topics via SSE stream."""
    topics: List[str] = Field(
        ...,
        description="List of topics to subscribe to (supports wildcards like 'research.*')"
    )
    agent_id: str = Field(
        ...,
        description="ID of the subscribing agent"
    )


class StreamConnectionInfo(BaseDTO):
    """Information about an SSE stream connection."""
    connection_id: str = Field(..., description="Unique connection identifier")
    agent_id: str = Field(..., description="Connected agent ID")
    topics: List[str] = Field(..., description="Subscribed topics")
    connected_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the connection was established"
    )
