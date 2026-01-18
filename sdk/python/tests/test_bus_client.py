"""
Tests for BusClient in soorma SDK.

Tests the refactored event system:
- Explicit topic parameter (no inference)
- Response event routing
- Distributed tracing
- Convenience methods (request, respond, announce)
- Event creation utilities (create_child_request, create_response)
"""
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from soorma.context import BusClient
from soorma.events import EventClient
from soorma_common.events import EventEnvelope, EventTopic


class TestBusClientPublish:
    """Tests for BusClient.publish() with explicit topic."""
    
    @pytest.fixture
    def bus_client(self):
        """Create a BusClient with mocked EventClient."""
        client = BusClient()
        client.event_client = AsyncMock(spec=EventClient)
        client.event_client.publish = AsyncMock(return_value="event-123")
        return client
    
    @pytest.mark.asyncio
    async def test_publish_requires_topic(self, bus_client):
        """publish() should require explicit topic parameter."""
        # This should work - topic is explicit
        await bus_client.publish(
            topic="action-requests",
            event_type="test.event",
            data={"key": "value"},
        )
        
        bus_client.event_client.publish.assert_called_once()
        call_kwargs = bus_client.event_client.publish.call_args[1]
        assert call_kwargs["topic"] == "action-requests"
        assert call_kwargs["event_type"] == "test.event"
    
    @pytest.mark.asyncio
    async def test_publish_with_response_event(self, bus_client):
        """publish() should include response_event in envelope."""
        await bus_client.publish(
            topic="action-requests",
            event_type="test.requested",
            data={},
            response_event="test.completed",
        )
        
        call_kwargs = bus_client.event_client.publish.call_args[1]
        assert call_kwargs["response_event"] == "test.completed"
    
    @pytest.mark.asyncio
    async def test_publish_with_tracing_fields(self, bus_client):
        """publish() should propagate trace_id and parent_event_id."""
        await bus_client.publish(
            topic="action-requests",
            event_type="test.event",
            data={},
            trace_id="trace-123",
            parent_event_id="parent-456",
        )
        
        call_kwargs = bus_client.event_client.publish.call_args[1]
        assert call_kwargs["trace_id"] == "trace-123"
        assert call_kwargs["parent_event_id"] == "parent-456"
    
    @pytest.mark.asyncio
    async def test_publish_with_payload_schema(self, bus_client):
        """publish() should include payload_schema_name."""
        await bus_client.publish(
            topic="action-results",
            event_type="test.completed",
            data={},
            payload_schema_name="test_result_v1",
        )
        
        call_kwargs = bus_client.event_client.publish.call_args[1]
        assert call_kwargs["payload_schema_name"] == "test_result_v1"


class TestBusClientConvenienceMethods:
    """Tests for request(), respond(), announce() convenience methods."""
    
    @pytest.fixture
    def bus_client(self):
        """Create a BusClient with mocked publish."""
        client = BusClient()
        client.event_client = AsyncMock(spec=EventClient)
        client.event_client.publish = AsyncMock(return_value="event-123")
        return client
    
    @pytest.mark.asyncio
    async def test_request_enforces_response_event(self, bus_client):
        """request() should require response_event parameter."""
        await bus_client.request(
            event_type="research.requested",
            data={"topic": "AI"},
            response_event="research.completed",
        )
        
        call_kwargs = bus_client.event_client.publish.call_args[1]
        assert call_kwargs["topic"] == "action-requests"
        assert call_kwargs["event_type"] == "research.requested"
        assert call_kwargs["response_event"] == "research.completed"
        assert call_kwargs["response_topic"] == "action-results"
    
    @pytest.mark.asyncio
    async def test_request_with_custom_response_topic(self, bus_client):
        """request() should allow custom response_topic."""
        await bus_client.request(
            event_type="research.requested",
            data={"topic": "AI"},
            response_event="research.completed",
            response_topic="custom-results",
        )
        
        call_kwargs = bus_client.event_client.publish.call_args[1]
        assert call_kwargs["response_topic"] == "custom-results"
    
    @pytest.mark.asyncio
    async def test_respond_enforces_correlation_id(self, bus_client):
        """respond() should require correlation_id parameter."""
        await bus_client.respond(
            event_type="test.completed",
            data={"result": "success"},
            correlation_id="task-123",
        )
        
        call_kwargs = bus_client.event_client.publish.call_args[1]
        assert call_kwargs["topic"] == "action-results"
        assert call_kwargs["event_type"] == "test.completed"
        assert call_kwargs["correlation_id"] == "task-123"
    
    @pytest.mark.asyncio
    async def test_respond_with_custom_topic(self, bus_client):
        """respond() should allow custom topic."""
        await bus_client.respond(
            event_type="test.completed",
            data={"result": "success"},
            correlation_id="task-123",
            topic="custom-results",
        )
        
        call_kwargs = bus_client.event_client.publish.call_args[1]
        assert call_kwargs["topic"] == "custom-results"
    
    @pytest.mark.asyncio
    async def test_announce_to_business_facts(self, bus_client):
        """announce() should publish to business-facts topic."""
        await bus_client.announce(
            event_type="order.placed",
            data={"order_id": "123"},
        )
        
        call_kwargs = bus_client.event_client.publish.call_args[1]
        assert call_kwargs["topic"] == "business-facts"
        assert call_kwargs["event_type"] == "order.placed"


class TestBusClientEventCreation:
    """Tests for create_child_request(), create_response() utilities."""
    
    @pytest.fixture
    def parent_event(self):
        """Create a parent event for testing."""
        return EventEnvelope(
            id="parent-123",
            source="planner-agent",
            type="research.goal",
            topic=EventTopic.ACTION_REQUESTS,
            data={"goal": "AI trends"},
            trace_id="trace-root",
            correlation_id="goal-corr",
            tenant_id="tenant-1",
            session_id="session-abc",
        )
    
    @pytest.fixture
    def bus_client(self):
        """Create a BusClient."""
        return BusClient()
    
    def test_create_child_request_propagates_metadata(self, bus_client, parent_event):
        """create_child_request() should auto-propagate trace_id, tenant_id, session_id."""
        child = bus_client.create_child_request(
            parent_event=parent_event,
            event_type="web.search.requested",
            data={"query": "AI trends"},
            response_event="web.search.completed",
        )
        
        assert child.type == "web.search.requested"
        assert child.topic == EventTopic.ACTION_REQUESTS
        assert child.response_event == "web.search.completed"
        assert child.response_topic == "action-results"
        
        # Metadata propagation
        assert child.trace_id == "trace-root"  # Propagated
        assert child.parent_event_id == "parent-123"  # Linked
        assert child.tenant_id == "tenant-1"  # Propagated
        assert child.session_id == "session-abc"  # Propagated
        assert child.correlation_id != parent_event.correlation_id  # New correlation
    
    def test_create_child_request_with_custom_correlation(self, bus_client, parent_event):
        """create_child_request() should allow custom correlation_id."""
        child = bus_client.create_child_request(
            parent_event=parent_event,
            event_type="web.search.requested",
            data={"query": "AI trends"},
            response_event="web.search.completed",
            new_correlation_id="task-1",
        )
        
        assert child.correlation_id == "task-1"
    
    def test_create_response_matches_request(self, bus_client):
        """create_response() should use request's response_event and correlation_id."""
        request = EventEnvelope(
            id="request-123",
            source="planner",
            type="web.search.requested",
            topic=EventTopic.ACTION_REQUESTS,
            data={"query": "AI"},
            response_event="web.search.completed",
            response_topic="action-results",
            correlation_id="task-1",
            trace_id="trace-root",
        )
        
        response = bus_client.create_response(
            request_event=request,
            data={"results": ["result1"]},
        )
        
        assert response.type == "web.search.completed"  # From request.response_event
        assert response.topic == EventTopic.ACTION_RESULTS
        assert response.correlation_id == "task-1"  # Matched
        assert response.trace_id == "trace-root"  # Propagated
        assert response.parent_event_id == "request-123"  # Linked
    
    def test_create_response_with_schema(self, bus_client):
        """create_response() should support payload_schema_name."""
        request = EventEnvelope(
            id="request-123",
            source="planner",
            type="web.search.requested",
            topic=EventTopic.ACTION_REQUESTS,
            data={},
            response_event="web.search.completed",
            correlation_id="task-1",
        )
        
        response = bus_client.create_response(
            request_event=request,
            data={"results": []},
            payload_schema_name="search_result_v1",
        )
        
        assert response.payload_schema_name == "search_result_v1"
    
    @pytest.mark.asyncio
    async def test_publish_envelope_convenience(self, parent_event):
        """publish_envelope() should publish pre-constructed envelope."""
        bus_client = BusClient()
        bus_client.event_client = AsyncMock(spec=EventClient)
        bus_client.event_client.publish = AsyncMock(return_value="event-123")
        
        child = bus_client.create_child_request(
            parent_event=parent_event,
            event_type="web.search.requested",
            data={"query": "AI trends"},
            response_event="web.search.completed",
        )
        
        event_id = await bus_client.publish_envelope(child)
        
        assert event_id == "event-123"
        call_kwargs = bus_client.event_client.publish.call_args[1]
        assert call_kwargs["topic"] == "action-requests"
        assert call_kwargs["event_type"] == "web.search.requested"
        assert call_kwargs["trace_id"] == "trace-root"
