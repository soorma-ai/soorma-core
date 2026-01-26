"""
Tests for AI event toolkit.
"""
import pytest
from unittest.mock import AsyncMock
from soorma.ai.event_toolkit import (
    EventToolkit,
    discover_events_simple,
    create_event_payload_simple,
    get_event_info_simple,
)
from soorma.models import EventDefinition


@pytest.fixture
def mock_events():
    """Create mock event definitions for testing."""
    return [
        EventDefinition(
            event_name="web.search.request",
            topic="action-requests",
            description="Request to perform a web search",
            payload_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query",
                        "example": "AI trends 2025",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "minimum": 1,
                        "maximum": 100,
                    },
                },
                "required": ["query"],
            },
            response_schema={
                "type": "object",
                "properties": {
                    "results": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "url": {"type": "string"},
                                "snippet": {"type": "string"},
                            },
                        },
                    },
                },
                "required": ["results"],
            },
        ),
        EventDefinition(
            event_name="data.process.request",
            topic="action-requests",
            description="Request to process data",
            payload_schema={
                "type": "object",
                "properties": {
                    "data_id": {"type": "string", "description": "Data identifier"},
                    "operation": {
                        "type": "string",
                        "enum": ["transform", "analyze", "aggregate"],
                    },
                },
                "required": ["data_id", "operation"],
            },
        ),
        EventDefinition(
            event_name="notification.sent",
            topic="notifications",
            description="Notification was sent",
            payload_schema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                    "message": {"type": "string"},
                },
                "required": ["user_id", "message"],
            },
        ),
    ]


@pytest.mark.asyncio
class TestEventToolkit:
    """Tests for EventToolkit class."""
    
    async def test_discover_all_events(self, monkeypatch, mock_events):
        """Test discovering all events returns EventDefinition objects."""
        async def mock_get_all_events():
            return mock_events
        
        toolkit = EventToolkit("http://localhost:8000")
        async with toolkit:
            monkeypatch.setattr(toolkit._client, "get_all_events", mock_get_all_events)
            
            events = await toolkit.discover_events()
            
            # Should return EventDefinition objects
            assert len(events) == 3
            assert events[0].event_name == "web.search.request"
            assert events[0].topic == "action-requests"
            assert "query" in events[0].payload_schema.get("properties", {})
            assert "query" in events[0].payload_schema.get("required", [])
    
    async def test_discover_events_by_topic(self, monkeypatch, mock_events):
        """Test discovering events filtered by topic."""
        from soorma_common.events import EventTopic

        async def mock_get_events_by_topic(topic):
            topic_value = getattr(topic, "value", topic)
            return [e for e in mock_events if e.topic == topic_value]
        
        toolkit = EventToolkit("http://localhost:8000")
        async with toolkit:
            monkeypatch.setattr(toolkit._client, "get_events_by_topic", mock_get_events_by_topic)
            
            events = await toolkit.discover_events(topic=EventTopic.ACTION_REQUESTS)
            
            assert len(events) == 2
            assert all(e.topic == EventTopic.ACTION_REQUESTS.value for e in events)
    
    async def test_discover_events_by_name_pattern(self, monkeypatch, mock_events):
        """Test discovering events filtered by name pattern."""
        async def mock_get_all_events():
            return mock_events
        
        toolkit = EventToolkit("http://localhost:8000")
        async with toolkit:
            monkeypatch.setattr(toolkit._client, "get_all_events", mock_get_all_events)
            
            events = await toolkit.discover_events(event_name_pattern="search")
            
            assert len(events) == 1
            assert events[0].event_name == "web.search.request"
    
    async def test_format_for_llm(self, monkeypatch, mock_events):
        """Test formatting EventDefinitions for LLM consumption."""
        async def mock_get_all_events():
            return [mock_events[0]]  # web.search.request
        
        toolkit = EventToolkit("http://localhost:8000")
        async with toolkit:
            monkeypatch.setattr(toolkit._client, "get_all_events", mock_get_all_events)
            
            events = await toolkit.discover_events()
            formatted = toolkit.format_for_llm(events)
            
            # Should return dictionaries
            assert len(formatted) == 1
            event = formatted[0]
            
            # Check LLM-friendly format
            assert "name" in event
            assert "topic" in event
            assert "description" in event
            assert "payload_fields" in event
            assert "required_fields" in event
            assert "example_payload" in event
            assert "has_response" in event
    
    async def test_format_as_prompt_text(self, monkeypatch, mock_events):
        """Test formatting events as prompt text."""
        async def mock_get_all_events():
            return mock_events[:2]  # First two events
        
        toolkit = EventToolkit("http://localhost:8000")
        async with toolkit:
            monkeypatch.setattr(toolkit._client, "get_all_events", mock_get_all_events)
            
            definitions = await toolkit.discover_events()
            dicts = toolkit.format_for_llm(definitions)
            prompt_text = toolkit.format_as_prompt_text(dicts)
            
            # Should be formatted text
            assert isinstance(prompt_text, str)
            assert "1. **web.search.request**" in prompt_text
            assert "2. **data.process.request**" in prompt_text
            assert "Description:" in prompt_text
    
    async def test_format_as_prompt_text_no_numbering(self, monkeypatch, mock_events):
        """Test formatting without numbering."""
        async def mock_get_all_events():
            return [mock_events[0]]
        
        toolkit = EventToolkit("http://localhost:8000")
        async with toolkit:
            monkeypatch.setattr(toolkit._client, "get_all_events", mock_get_all_events)
            
            definitions = await toolkit.discover_events()
            dicts = toolkit.format_for_llm(definitions)
            prompt_text = toolkit.format_as_prompt_text(dicts, numbered=False)
            
            # Should not have numbers
            assert "1." not in prompt_text
            assert "**web.search.request**" in prompt_text
    
    async def test_event_descriptor_structure(self, monkeypatch, mock_events):
        """Test that format_for_llm creates correct structure."""
        async def mock_get_all_events():
            return [mock_events[0]]  # web.search.request
        
        toolkit = EventToolkit("http://localhost:8000")
        async with toolkit:
            monkeypatch.setattr(toolkit._client, "get_all_events", mock_get_all_events)
            
            definitions = await toolkit.discover_events()
            events = toolkit.format_for_llm(definitions)
            event = events[0]
            
            # Check required fields
            assert "name" in event
            assert "topic" in event
            assert "description" in event
            assert "payload_fields" in event
            assert "required_fields" in event
            assert "example_payload" in event
            assert "has_response" in event
            
            # Check payload fields structure
            assert "query" in event["payload_fields"]
            query_field = event["payload_fields"]["query"]
            assert query_field["type"] == "string"
            assert query_field["description"] == "Search query"
            assert query_field["required"] is True
            assert query_field["example"] == "AI trends 2025"
            
            # Check response fields
            assert event["has_response"] is True
            assert "response_fields" in event
            assert "results" in event["response_fields"]
    
    async def test_field_constraints_extraction(self, monkeypatch, mock_events):
        """Test that field constraints are correctly extracted in format_for_llm."""
        async def mock_get_all_events():
            return [mock_events[0]]
        
        toolkit = EventToolkit("http://localhost:8000")
        async with toolkit:
            monkeypatch.setattr(toolkit._client, "get_all_events", mock_get_all_events)
            
            definitions = await toolkit.discover_events()
            events = toolkit.format_for_llm(definitions)
            max_results = events[0]["payload_fields"]["max_results"]
            
            assert max_results["type"] == "integer"
            assert max_results["minimum"] == 1
            assert max_results["maximum"] == 100
    
    async def test_enum_values_extraction(self, monkeypatch, mock_events):
        """Test that enum values are correctly extracted in format_for_llm."""
        async def mock_get_all_events():
            return [mock_events[1]]  # data.process.request
        
        toolkit = EventToolkit("http://localhost:8000")
        async with toolkit:
            monkeypatch.setattr(toolkit._client, "get_all_events", mock_get_all_events)
            
            definitions = await toolkit.discover_events()
            events = toolkit.format_for_llm(definitions)
            operation = events[0]["payload_fields"]["operation"]
            
            assert "allowed_values" in operation
            assert operation["allowed_values"] == ["transform", "analyze", "aggregate"]
    
    async def test_create_payload_success(self, monkeypatch, mock_events):
        """Test successful payload creation."""
        async def mock_get_event(event_name):
            return next((e for e in mock_events if e.event_name == event_name), None)
        
        toolkit = EventToolkit("http://localhost:8000")
        async with toolkit:
            monkeypatch.setattr(toolkit._client, "get_event", mock_get_event)
            
            payload = await toolkit.create_payload(
                "web.search.request",
                {"query": "AI trends 2025", "max_results": 10}
            )
            
            assert "query" in payload
            assert payload["query"] == "AI trends 2025"
            assert "maxResults" in payload  # camelCase conversion
            assert payload["maxResults"] == 10
    
    async def test_create_payload_minimal_fields(self, monkeypatch, mock_events):
        """Test payload creation with only required fields."""
        async def mock_get_event(event_name):
            return next((e for e in mock_events if e.event_name == event_name), None)
        
        toolkit = EventToolkit("http://localhost:8000")
        async with toolkit:
            monkeypatch.setattr(toolkit._client, "get_event", mock_get_event)
            
            payload = await toolkit.create_payload(
                "web.search.request",
                {"query": "test"}
            )
            
            assert payload["query"] == "test"
    
    async def test_create_payload_validation_error(self, monkeypatch, mock_events):
        """Test payload creation with validation errors."""
        async def mock_get_event(event_name):
            return next((e for e in mock_events if e.event_name == event_name), None)
        
        toolkit = EventToolkit("http://localhost:8000")
        async with toolkit:
            monkeypatch.setattr(toolkit._client, "get_event", mock_get_event)
            
            # Missing required field
            with pytest.raises(ValueError, match="Payload validation failed"):
                await toolkit.create_payload(
                    "web.search.request",
                    {"max_results": 10}  # missing 'query'
                )
    
    async def test_create_payload_event_not_found(self, monkeypatch):
        """Test payload creation when event doesn't exist."""
        async def mock_get_event(event_name):
            return None
        
        toolkit = EventToolkit("http://localhost:8000")
        async with toolkit:
            monkeypatch.setattr(toolkit._client, "get_event", mock_get_event)
            
            with pytest.raises(ValueError, match="not found in registry"):
                await toolkit.create_payload(
                    "nonexistent.event",
                    {"data": "test"}
                )
    
    async def test_validate_response_success(self, monkeypatch, mock_events):
        """Test successful response validation."""
        async def mock_get_event(event_name):
            return next((e for e in mock_events if e.event_name == event_name), None)
        
        toolkit = EventToolkit("http://localhost:8000")
        async with toolkit:
            monkeypatch.setattr(toolkit._client, "get_event", mock_get_event)
            
            response = await toolkit.validate_response(
                "web.search.request",
                {
                    "results": [
                        {
                            "title": "Test",
                            "url": "https://example.com",
                            "snippet": "Test snippet"
                        }
                    ]
                }
            )
            
            assert "results" in response
            assert len(response["results"]) == 1
    
    async def test_validate_response_no_schema(self, monkeypatch, mock_events):
        """Test validation when event has no response schema."""
        async def mock_get_event(event_name):
            return next((e for e in mock_events if e.event_name == event_name), None)
        
        toolkit = EventToolkit("http://localhost:8000")
        async with toolkit:
            monkeypatch.setattr(toolkit._client, "get_event", mock_get_event)
            
            with pytest.raises(ValueError, match="has no response schema"):
                await toolkit.validate_response(
                    "notification.sent",
                    {"some": "data"}
                )
    
    async def test_validate_response_validation_error(self, monkeypatch, mock_events):
        """Test response validation with invalid data."""
        async def mock_get_event(event_name):
            return next((e for e in mock_events if e.event_name == event_name), None)
        
        toolkit = EventToolkit("http://localhost:8000")
        async with toolkit:
            monkeypatch.setattr(toolkit._client, "get_event", mock_get_event)
            
            with pytest.raises(ValueError, match="Response validation failed"):
                await toolkit.validate_response(
                    "web.search.request",
                    {"invalid": "data"}  # missing 'results'
                )
    
    async def test_get_event_info(self, monkeypatch, mock_events):
        """Test getting detailed event information returns EventDefinition."""
        async def mock_get_event(event_name):
            return next((e for e in mock_events if e.event_name == event_name), None)
        
        toolkit = EventToolkit("http://localhost:8000")
        async with toolkit:
            monkeypatch.setattr(toolkit._client, "get_event", mock_get_event)
            
            info = await toolkit.get_event_info("web.search.request")
            
            assert info is not None
            assert info.event_name == "web.search.request"
            assert info.description == "Request to perform a web search"
            assert "query" in info.payload_schema.get("properties", {})
            assert info.response_schema is not None
    
    async def test_get_event_info_not_found(self, monkeypatch):
        """Test getting info for non-existent event."""
        async def mock_get_event(event_name):
            return None
        
        toolkit = EventToolkit("http://localhost:8000")
        async with toolkit:
            monkeypatch.setattr(toolkit._client, "get_event", mock_get_event)
            
            info = await toolkit.get_event_info("nonexistent.event")
            
            assert info is None
    
    async def test_context_manager_error_handling(self, monkeypatch):
        """Test that toolkit must be used as context manager."""
        toolkit = EventToolkit("http://localhost:8000")
        
        with pytest.raises(RuntimeError, match="context manager"):
            await toolkit.discover_events()
    
    async def test_example_payload_generation(self, monkeypatch, mock_events):
        """Test that example payloads are generated correctly in format_for_llm."""
        async def mock_get_all_events():
            return [mock_events[0]]
        
        toolkit = EventToolkit("http://localhost:8000")
        async with toolkit:
            monkeypatch.setattr(toolkit._client, "get_all_events", mock_get_all_events)
            
            definitions = await toolkit.discover_events()
            events = toolkit.format_for_llm(definitions)
            example = events[0]["example_payload"]
            
            assert "query" in example
            assert "max_results" in example
            example = events[0]["example_payload"]
            
            # Should have required fields
            assert "query" in example
            # Should use provided example value
            assert example["query"] == "AI trends 2025"


@pytest.mark.asyncio
class TestConvenienceFunctions:
    """Tests for convenience functions."""
    
    async def test_discover_events_simple(self, monkeypatch, mock_events):
        """Test simple event discovery function returns EventDefinitions."""
        from soorma.registry.client import RegistryClient
        from soorma_common.events import EventTopic
        
        async def mock_get_events_by_topic(topic):
            topic_value = getattr(topic, "value", topic)
            return [e for e in mock_events if e.topic == topic_value]
        
        # Mock the client method
        original_init = RegistryClient.__init__
        original_aenter = RegistryClient.__aenter__
        
        def mock_init(self, base_url, timeout=30.0):
            original_init(self, base_url, timeout)
        
        async def mock_aenter(self):
            await original_aenter(self)
            self.get_events_by_topic = mock_get_events_by_topic
            return self
        
        monkeypatch.setattr(RegistryClient, "__init__", mock_init)
        monkeypatch.setattr(RegistryClient, "__aenter__", mock_aenter)
        
        events = await discover_events_simple(topic=EventTopic.ACTION_REQUESTS)
        
        assert len(events) == 2
        assert all(e.topic == EventTopic.ACTION_REQUESTS.value for e in events)
    
    async def test_create_event_payload_simple(self, monkeypatch, mock_events):
        """Test simple payload creation function."""
        from soorma.registry.client import RegistryClient
        
        async def mock_get_event(event_name):
            return next((e for e in mock_events if e.event_name == event_name), None)
        
        original_init = RegistryClient.__init__
        original_aenter = RegistryClient.__aenter__
        
        def mock_init(self, base_url, timeout=30.0):
            original_init(self, base_url, timeout)
        
        async def mock_aenter(self):
            await original_aenter(self)
            self.get_event = mock_get_event
            return self
        
        monkeypatch.setattr(RegistryClient, "__init__", mock_init)
        monkeypatch.setattr(RegistryClient, "__aenter__", mock_aenter)
        
        result = await create_event_payload_simple(
            "web.search.request",
            {"query": "test"}
        )
        
        assert result["success"] is True
        assert "query" in result["payload"]
        assert result["payload"]["query"] == "test"
        assert result["errors"] == []
    
    async def test_get_event_info_simple(self, monkeypatch, mock_events):
        """Test simple event info function returns EventDefinition."""
        from soorma.registry.client import RegistryClient
        
        async def mock_get_event(event_name):
            return next((e for e in mock_events if e.event_name == event_name), None)
        
        original_init = RegistryClient.__init__
        original_aenter = RegistryClient.__aenter__
        
        def mock_init(self, base_url, timeout=30.0):
            original_init(self, base_url, timeout)
        
        async def mock_aenter(self):
            await original_aenter(self)
            self.get_event = mock_get_event
            return self
        
        monkeypatch.setattr(RegistryClient, "__init__", mock_init)
        monkeypatch.setattr(RegistryClient, "__aenter__", mock_aenter)
        
        info = await get_event_info_simple("web.search.request")
        
        assert info is not None
        assert info.event_name == "web.search.request"
