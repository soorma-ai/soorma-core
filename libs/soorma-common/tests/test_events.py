"""
Tests for Event DTOs in soorma-common.
"""
import pytest
from datetime import datetime, timezone

from soorma_common.events import (
    EventTopic,
    EventEnvelope,
    ActionRequestEvent,
    ActionResultEvent,
    BusinessFactEvent,
    BillingEvent,
    NotificationEvent,
    PublishRequest,
    PublishResponse,
)


class TestEventTopic:
    """Tests for EventTopic enum."""
    
    def test_topic_values(self):
        """Test that topics have expected string values."""
        assert EventTopic.BUSINESS_FACTS.value == "business-facts"
        assert EventTopic.ACTION_REQUESTS.value == "action-requests"
        assert EventTopic.ACTION_RESULTS.value == "action-results"
        assert EventTopic.BILLING_EVENTS.value == "billing-events"


class TestEventEnvelope:
    """Tests for EventEnvelope model."""
    
    def test_create_minimal_envelope(self):
        """Test creating envelope with minimal required fields."""
        envelope = EventEnvelope(
            source="test-agent",
            type="test.event",
            topic=EventTopic.BUSINESS_FACTS,
        )
        
        assert envelope.source == "test-agent"
        assert envelope.type == "test.event"
        assert envelope.topic == EventTopic.BUSINESS_FACTS
        assert envelope.specversion == "1.0"
        assert envelope.id is not None
        assert envelope.correlation_id is not None
        assert envelope.time is not None
    
    def test_create_full_envelope(self):
        """Test creating envelope with all fields."""
        envelope = EventEnvelope(
            id="event-123",
            source="test-agent",
            type="test.event",
            topic=EventTopic.BUSINESS_FACTS,
            data={"key": "value"},
            correlation_id="trace-456",
            subject="resource:789",
            tenant_id="tenant-1",
            session_id="session-abc",
        )
        
        assert envelope.id == "event-123"
        assert envelope.data == {"key": "value"}
        assert envelope.correlation_id == "trace-456"
        assert envelope.subject == "resource:789"
        assert envelope.tenant_id == "tenant-1"
        assert envelope.session_id == "session-abc"
    
    def test_to_cloudevents_dict(self):
        """Test CloudEvents dict conversion."""
        envelope = EventEnvelope(
            id="event-123",
            source="test-agent",
            type="test.event",
            topic=EventTopic.BUSINESS_FACTS,
            data={"key": "value"},
            correlation_id="trace-456",
        )
        
        ce_dict = envelope.to_cloudevents_dict()
        
        assert ce_dict["id"] == "event-123"
        assert ce_dict["source"] == "test-agent"
        assert ce_dict["type"] == "test.event"
        assert ce_dict["specversion"] == "1.0"
        assert ce_dict["data"] == {"key": "value"}
        assert ce_dict["correlationid"] == "trace-456"
        assert ce_dict["topic"] == "business-facts"
    
    def test_camel_case_serialization(self):
        """Test that fields serialize to camelCase."""
        envelope = EventEnvelope(
            source="test-agent",
            type="test.event",
            topic=EventTopic.BUSINESS_FACTS,
            correlation_id="trace-123",
            tenant_id="tenant-1",
            session_id="session-abc",
        )
        
        data = envelope.model_dump(by_alias=True)
        
        assert "correlationId" in data
        assert "tenantId" in data
        assert "sessionId" in data


class TestActionRequestEvent:
    """Tests for ActionRequestEvent model."""
    
    def test_topic_is_fixed(self):
        """Test that topic is always ACTION_REQUESTS."""
        event = ActionRequestEvent(
            source="planner",
            type="research.requested",
            topic=EventTopic.BUSINESS_FACTS,  # Try to override
        )
        
        # Should be overridden to ACTION_REQUESTS
        assert event.topic == EventTopic.ACTION_REQUESTS
    
    def test_action_request_fields(self):
        """Test ActionRequestEvent-specific fields."""
        event = ActionRequestEvent(
            source="planner",
            type="research.requested",
            topic=EventTopic.ACTION_REQUESTS,
            plan_id="plan-123",
            caused_by="event-456",
            callback_url="http://localhost:8080/callback",
        )
        
        assert event.plan_id == "plan-123"
        assert event.caused_by == "event-456"
        assert event.callback_url == "http://localhost:8080/callback"


class TestActionResultEvent:
    """Tests for ActionResultEvent model."""
    
    def test_topic_is_fixed(self):
        """Test that topic is always ACTION_RESULTS."""
        event = ActionResultEvent(
            source="worker",
            type="research.completed",
            topic=EventTopic.BUSINESS_FACTS,  # Try to override
            action_event_id="event-123",
            success=True,
        )
        
        assert event.topic == EventTopic.ACTION_RESULTS
    
    def test_success_result(self):
        """Test successful action result."""
        event = ActionResultEvent(
            source="worker",
            type="research.completed",
            topic=EventTopic.ACTION_RESULTS,
            action_event_id="event-123",
            success=True,
            result={"answer": "42"},
        )
        
        assert event.success is True
        assert event.result == {"answer": "42"}
        assert event.error is None
    
    def test_failure_result(self):
        """Test failed action result."""
        event = ActionResultEvent(
            source="worker",
            type="research.failed",
            topic=EventTopic.ACTION_RESULTS,
            action_event_id="event-123",
            success=False,
            error="Resource not found",
        )
        
        assert event.success is False
        assert event.error == "Resource not found"


class TestBillingEvent:
    """Tests for BillingEvent model."""
    
    def test_topic_is_fixed(self):
        """Test that topic is always BILLING_EVENTS."""
        event = BillingEvent(
            source="worker",
            type="tokens.consumed",
            topic=EventTopic.BUSINESS_FACTS,  # Try to override
            unit_of_work="llm_call",
            cost=0.02,
        )
        
        assert event.topic == EventTopic.BILLING_EVENTS
    
    def test_billing_fields(self):
        """Test BillingEvent-specific fields."""
        event = BillingEvent(
            source="worker",
            type="tokens.consumed",
            topic=EventTopic.BILLING_EVENTS,
            unit_of_work="llm_call",
            cost=0.02,
            currency="USD",
        )
        
        assert event.unit_of_work == "llm_call"
        assert event.cost == 0.02
        assert event.currency == "USD"


class TestNotificationEvent:
    """Tests for NotificationEvent model."""
    
    def test_topic_is_fixed(self):
        """Test that topic is always NOTIFICATION_EVENTS."""
        event = NotificationEvent(
            source="agent",
            type="user.notification",
            topic=EventTopic.BUSINESS_FACTS,  # Try to override
            message="Task completed!",
        )
        
        assert event.topic == EventTopic.NOTIFICATION_EVENTS
    
    def test_notification_fields(self):
        """Test NotificationEvent-specific fields."""
        event = NotificationEvent(
            source="agent",
            type="user.notification",
            topic=EventTopic.NOTIFICATION_EVENTS,
            message="Task completed!",
            priority="high",
            channel="push",
        )
        
        assert event.message == "Task completed!"
        assert event.priority == "high"
        assert event.channel == "push"


class TestServiceDTOs:
    """Tests for Event Service request/response DTOs."""
    
    def test_publish_request(self):
        """Test PublishRequest model."""
        envelope = EventEnvelope(
            source="test",
            type="test.event",
            topic=EventTopic.BUSINESS_FACTS,
        )
        
        request = PublishRequest(event=envelope)
        
        assert request.event == envelope
    
    def test_publish_response(self):
        """Test PublishResponse model."""
        response = PublishResponse(
            success=True,
            event_id="event-123",
            message="Published",
        )
        
        assert response.success is True
        assert response.event_id == "event-123"
        assert response.message == "Published"
