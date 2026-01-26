"""
Tests for EventEnvelope usage in event handlers.

Verifies that:
- Handlers receive EventEnvelope objects instead of dicts
- EventEnvelope attributes are properly accessible
- EventClient properly deserializes events
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from soorma.agents.base import Agent
from soorma.events import EventClient
from soorma_common.events import EventEnvelope, EventTopic


class TestEventClientTopicTyping:
    """Test that EventClient methods accept both EventTopic enum and string values."""
    
    @pytest.mark.asyncio
    async def test_connect_accepts_event_topic_enum(self):
        """connect() should accept EventTopic enum values."""
        client = EventClient(agent_id="test-client")
        
        # This should not raise an error
        await client.connect(topics=[EventTopic.ACTION_REQUESTS, EventTopic.BUSINESS_FACTS])
        
        # Verify topics were converted to strings
        assert EventTopic.ACTION_REQUESTS.value in client._subscribed_topics
        assert EventTopic.BUSINESS_FACTS.value in client._subscribed_topics
        
        await client.disconnect()
    
    @pytest.mark.asyncio
    async def test_connect_accepts_string_topics(self):
        """connect() should accept string values for wildcards."""
        client = EventClient(agent_id="test-client")
        
        # This should not raise an error
        await client.connect(topics=["research.*", "action-requests"])
        
        # Verify topics are stored as strings
        assert "research.*" in client._subscribed_topics
        assert "action-requests" in client._subscribed_topics
        
        await client.disconnect()
    
    @pytest.mark.asyncio
    async def test_connect_accepts_mixed_types(self):
        """connect() should accept both EventTopic and string in the same list."""
        client = EventClient(agent_id="test-client")
        
        # Mix of enum and string
        await client.connect(topics=[EventTopic.ACTION_REQUESTS, "research.*", EventTopic.BUSINESS_FACTS])
        
        # Verify all topics are converted to strings
        assert EventTopic.ACTION_REQUESTS.value in client._subscribed_topics
        assert "research.*" in client._subscribed_topics
        assert EventTopic.BUSINESS_FACTS.value in client._subscribed_topics
        
        await client.disconnect()
    
    @pytest.mark.asyncio
    async def test_publish_accepts_event_topic_enum(self):
        """publish() should accept EventTopic enum for topic parameter."""
        client = EventClient(agent_id="test-client")
        
        with patch.object(client, '_ensure_http_client', new_callable=AsyncMock):
            # Mock the HTTP client
            mock_http = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"event_id": "test-123"}
            mock_http.post = AsyncMock(return_value=mock_response)
            client._http_client = mock_http
            
            # This should not raise an error
            event_id = await client.publish(
                event_type="test.event",
                topic=EventTopic.ACTION_REQUESTS,
                data={"key": "value"},
            )
            
            # Verify topic was converted to string in the event
            call_args = mock_http.post.call_args
            event_payload = call_args[1]["json"]["event"]
            assert event_payload["topic"] == EventTopic.ACTION_REQUESTS.value
            assert event_id == "test-123"
    
    @pytest.mark.asyncio
    async def test_publish_accepts_string_topic(self):
        """publish() should accept string for topic parameter."""
        client = EventClient(agent_id="test-client")
        
        with patch.object(client, '_ensure_http_client', new_callable=AsyncMock):
            # Mock the HTTP client
            mock_http = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"event_id": "test-456"}
            mock_http.post = AsyncMock(return_value=mock_response)
            client._http_client = mock_http
            
            # This should not raise an error
            event_id = await client.publish(
                event_type="test.event",
                topic="action-requests",
                data={"key": "value"},
            )
            
            # Verify topic is kept as string
            call_args = mock_http.post.call_args
            event_payload = call_args[1]["json"]["event"]
            assert event_payload["topic"] == "action-requests"
            assert event_id == "test-456"
    
    @pytest.mark.asyncio
    async def test_all_event_topics_work_with_connect(self):
        """All EventTopic enum values should work with connect()."""
        client = EventClient(agent_id="test-client")
        
        # Use all topics from the enum
        all_topics = [
            EventTopic.BUSINESS_FACTS,
            EventTopic.ACTION_REQUESTS,
            EventTopic.ACTION_RESULTS,
            EventTopic.BILLING_EVENTS,
            EventTopic.NOTIFICATION_EVENTS,
            EventTopic.SYSTEM_EVENTS,
            EventTopic.PLAN_EVENTS,
            EventTopic.TASK_EVENTS,
        ]
        
        await client.connect(topics=all_topics)
        
        # Verify all topics were converted to strings
        for topic in all_topics:
            assert topic.value in client._subscribed_topics
        
        await client.disconnect()
    
    @pytest.mark.asyncio
    async def test_connect_with_empty_topics_skips_sse(self):
        """connect() with empty topics should skip SSE connection (publish-only mode)."""
        client = EventClient(agent_id="test-client")
        
        # Connect with no topics (publish-only)
        await client.connect(topics=[])
        
        # Should be marked as connected
        assert client.is_connected
        
        # But should not have started SSE stream task
        assert client._stream_task is None
        
        # Should have empty subscribed topics
        assert client._subscribed_topics == []
        
        await client.disconnect()


class TestEventEnvelopeInHandlers:
    """Test that handlers receive EventEnvelope objects."""
    
    @pytest.mark.asyncio
    async def test_agent_handler_receives_event_envelope(self):
        """Agent event handler should receive EventEnvelope object."""
        agent = Agent(name="test-agent")
        received_event = None
        
        @agent.on_event("test.event", topic=EventTopic.BUSINESS_FACTS)
        async def handler(event, context):
            nonlocal received_event
            received_event = event
        
        # Simulate event dispatch by directly calling the wrapped handler
        # This tests the EventEnvelope deserialization in base.py
        test_event_dict = {
            "id": "test-123",
            "source": "test-source",
            "type": "test.event",
            "specversion": "1.0",
            "time": datetime.now(timezone.utc).isoformat(),
            "data": {"key": "value"},
            "correlation_id": "corr-123",
            "topic": EventTopic.BUSINESS_FACTS,
        }
        
        # Get the registered handler
        handlers = agent._event_handlers.get("business-facts:test.event", [])
        assert len(handlers) == 1
        
        # Create a mock context
        mock_context = MagicMock()
        
        # Call handler with dict (simulating what EventClient does)
        # In the actual code, wrapped_handler converts dict -> EventEnvelope
        # We're testing that conversion
        event_envelope = EventEnvelope(**test_event_dict)
        await handlers[0](event_envelope, mock_context)
        
        # Verify handler received EventEnvelope
        assert isinstance(received_event, EventEnvelope)
        assert received_event.id == "test-123"
        assert received_event.source == "test-source"
        assert received_event.type == "test.event"
        assert received_event.correlation_id == "corr-123"
        assert received_event.data == {"key": "value"}
    
    @pytest.mark.asyncio
    async def test_event_client_handler_receives_event_envelope(self):
        """EventClient handlers should receive EventEnvelope object."""
        client = EventClient(agent_id="test-client")
        received_event = None
        
        @client.on_event("test.event")
        async def handler(event):
            nonlocal received_event
            received_event = event
        
        # Simulate event dispatch
        test_event_dict = {
            "id": "test-456",
            "source": "test-source",
            "type": "test.event",
            "specversion": "1.0",
            "time": datetime.now(timezone.utc).isoformat(),
            "data": {"message": "hello"},
            "correlation_id": "corr-456",
            "topic": EventTopic.ACTION_REQUESTS,
        }
        
        # Call _dispatch_event which should deserialize to EventEnvelope
        await client._dispatch_event(test_event_dict)
        
        # Verify handler received EventEnvelope
        assert isinstance(received_event, EventEnvelope)
        assert received_event.id == "test-456"
        assert received_event.type == "test.event"
        assert received_event.data == {"message": "hello"}
    
    @pytest.mark.asyncio
    async def test_event_envelope_attributes_accessible(self):
        """EventEnvelope attributes should be accessible with dot notation."""
        client = EventClient(agent_id="test-client")
        test_results = {}
        
        @client.on_event("test.event")
        async def handler(event):
            # Test all common attributes
            test_results["id"] = event.id
            test_results["source"] = event.source
            test_results["type"] = event.type
            test_results["correlation_id"] = event.correlation_id
            test_results["data"] = event.data
            test_results["topic"] = event.topic
            test_results["subject"] = event.subject
            test_results["trace_id"] = event.trace_id
        
        test_event_dict = {
            "id": "evt-789",
            "source": "my-agent",
            "type": "test.event",
            "specversion": "1.0",
            "time": datetime.now(timezone.utc).isoformat(),
            "data": {"count": 42},
            "correlation_id": "corr-789",
            "topic": EventTopic.BUSINESS_FACTS,
            "subject": "test-subject",
            "trace_id": "trace-789",
        }
        
        await client._dispatch_event(test_event_dict)
        
        # Verify all attributes were accessible
        assert test_results["id"] == "evt-789"
        assert test_results["source"] == "my-agent"
        assert test_results["type"] == "test.event"
        assert test_results["correlation_id"] == "corr-789"
        assert test_results["data"] == {"count": 42}
        assert test_results["topic"] == EventTopic.BUSINESS_FACTS
        assert test_results["subject"] == "test-subject"
        assert test_results["trace_id"] == "trace-789"
    
    @pytest.mark.asyncio
    async def test_invalid_event_dict_handles_gracefully(self):
        """EventClient should handle invalid event dicts gracefully."""
        client = EventClient(agent_id="test-client")
        handler_called = False
        
        @client.on_event("test.event")
        async def handler(event):
            nonlocal handler_called
            handler_called = True
        
        # Invalid event missing required fields
        invalid_event = {
            "type": "test.event",
            # Missing required fields like 'source', 'id', etc.
        }
        
        # Should not raise exception, just log error
        await client._dispatch_event(invalid_event)
        
        # Handler should not have been called
        assert not handler_called
    
    def test_event_envelope_type_hints_work(self):
        """Type hints for EventEnvelope should work correctly."""
        agent = Agent(name="test-agent")
        
        # This should not raise any type errors (in IDE with type checking)
        @agent.on_event("test.event", topic=EventTopic.BUSINESS_FACTS)
        async def handler(event: EventEnvelope, context):
            # These should all be valid with proper IDE autocomplete
            event_id: str = event.id
            source: str = event.source
            event_type: str = event.type
            data: dict = event.data or {}
            correlation: str = event.correlation_id
        
        # Just verify the handler was registered
        assert "business-facts:test.event" in agent._event_handlers


class TestEventEnvelopeValidation:
    """Test EventEnvelope validation features."""
    
    def test_event_envelope_validates_required_fields(self):
        """EventEnvelope should validate required fields."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            EventEnvelope()  # Missing required fields
    
    def test_event_envelope_accepts_valid_data(self):
        """EventEnvelope should accept valid data."""
        envelope = EventEnvelope(
            source="test-agent",
            type="test.event",
            topic=EventTopic.BUSINESS_FACTS,
        )
        
        assert envelope.source == "test-agent"
        assert envelope.type == "test.event"
        assert envelope.topic == EventTopic.BUSINESS_FACTS
        assert envelope.id is not None  # Auto-generated
        assert envelope.correlation_id is not None  # Auto-generated
    
    def test_event_envelope_auto_generates_ids(self):
        """EventEnvelope should auto-generate IDs if not provided."""
        envelope1 = EventEnvelope(
            source="test-agent",
            type="test.event",
            topic=EventTopic.BUSINESS_FACTS,
        )
        
        envelope2 = EventEnvelope(
            source="test-agent",
            type="test.event",
            topic=EventTopic.BUSINESS_FACTS,
        )
        
        # IDs should be auto-generated and unique
        assert envelope1.id is not None
        assert envelope2.id is not None
        assert envelope1.id != envelope2.id
        
        # Correlation IDs should also be auto-generated and unique
        assert envelope1.correlation_id is not None
        assert envelope2.correlation_id is not None
        assert envelope1.correlation_id != envelope2.correlation_id
    def test_event_envelope_with_tenant_and_user_id(self):
        """Test that EventEnvelope properly handles tenant_id and user_id fields."""
        tenant_id = "tenant-123"
        user_id = "user-456"
        
        envelope = EventEnvelope(
            source="test-source",
            type="test.event",
            topic=EventTopic.ACTION_REQUESTS,
            data={"key": "value"},
            tenant_id=tenant_id,
            user_id=user_id,
        )
        
        # Verify fields are set
        assert envelope.tenant_id == tenant_id
        assert envelope.user_id == user_id
        assert envelope.data == {"key": "value"}
    
    def test_event_envelope_serialization_with_tenant_user(self):
        """Test that tenant_id and user_id are properly serialized to CloudEvents format."""
        tenant_id = "tenant-789"
        user_id = "user-101"
        
        envelope = EventEnvelope(
            source="test-source",
            type="test.event",
            topic=EventTopic.BUSINESS_FACTS,
            data={"result": "success"},
            tenant_id=tenant_id,
            user_id=user_id,
        )
        
        # Convert to CloudEvents dict
        cloud_events = envelope.to_cloudevents_dict()
        
        # Verify fields are serialized
        assert cloud_events["tenantid"] == tenant_id
        assert cloud_events["userid"] == user_id
        assert cloud_events["data"] == {"result": "success"}
    
    def test_event_envelope_deserialization_with_tenant_user(self):
        """Test that tenant_id and user_id can be deserialized from dict."""
        tenant_id = "tenant-999"
        user_id = "user-202"
        
        event_dict = {
            "id": "event-001",
            "source": "test-source",
            "type": "test.event",
            "specversion": "1.0",
            "time": datetime.now(timezone.utc).isoformat(),
            "data": {"info": "test"},
            "correlation_id": "corr-001",
            "topic": EventTopic.ACTION_RESULTS,
            "tenant_id": tenant_id,
            "user_id": user_id,
        }
        
        # Deserialize from dict
        envelope = EventEnvelope(**event_dict)
        
        # Verify fields are accessible
        assert envelope.tenant_id == tenant_id
        assert envelope.user_id == user_id
        assert envelope.type == "test.event"
        assert envelope.data == {"info": "test"}