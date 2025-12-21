"""
Tests for AI tools (function calling interface).
"""
import pytest
from soorma.ai.tools import (
    AI_FUNCTION_TOOLS,
    execute_ai_tool,
    get_tool_definitions,
    format_tool_result_for_llm,
)
from soorma.models import EventDefinition


@pytest.fixture
def mock_event():
    """Create a mock event for testing."""
    return EventDefinition(
        event_name="test.event",
        topic="test-topic",
        description="A test event",
        payload_schema={
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Test message"},
            },
            "required": ["message"],
        },
        response_schema={
            "type": "object",
            "properties": {
                "status": {"type": "string"},
            },
            "required": ["status"],
        },
    )


class TestAIFunctionTools:
    """Tests for AI function tool definitions."""
    
    def test_tool_definitions_structure(self):
        """Test that tool definitions have correct structure."""
        tools = get_tool_definitions()
        
        assert len(tools) == 4
        assert all("type" in tool for tool in tools)
        assert all(tool["type"] == "function" for tool in tools)
        assert all("function" in tool for tool in tools)
        
        tool_names = [tool["function"]["name"] for tool in tools]
        assert "discover_events" in tool_names
        assert "get_event_schema" in tool_names
        assert "create_event_payload" in tool_names
        assert "validate_event_response" in tool_names
    
    def test_discover_events_tool(self):
        """Test discover_events tool definition."""
        tools = get_tool_definitions()
        discover_tool = next(
            t for t in tools
            if t["function"]["name"] == "discover_events"
        )
        
        assert "description" in discover_tool["function"]
        assert "parameters" in discover_tool["function"]
        
        params = discover_tool["function"]["parameters"]
        assert params["type"] == "object"
        assert "topic" in params["properties"]
        assert "event_name_pattern" in params["properties"]
    
    def test_get_event_schema_tool(self):
        """Test get_event_schema tool definition."""
        tools = get_tool_definitions()
        schema_tool = next(
            t for t in tools
            if t["function"]["name"] == "get_event_schema"
        )
        
        params = schema_tool["function"]["parameters"]
        assert "event_name" in params["properties"]
        assert "event_name" in params["required"]
    
    def test_create_event_payload_tool(self):
        """Test create_event_payload tool definition."""
        tools = get_tool_definitions()
        create_tool = next(
            t for t in tools
            if t["function"]["name"] == "create_event_payload"
        )
        
        params = create_tool["function"]["parameters"]
        assert "event_name" in params["properties"]
        assert "payload_data" in params["properties"]
        assert params["required"] == ["event_name", "payload_data"]
    
    def test_validate_event_response_tool(self):
        """Test validate_event_response tool definition."""
        tools = get_tool_definitions()
        validate_tool = next(
            t for t in tools
            if t["function"]["name"] == "validate_event_response"
        )
        
        params = validate_tool["function"]["parameters"]
        assert "event_name" in params["properties"]
        assert "response_data" in params["properties"]
        assert params["required"] == ["event_name", "response_data"]


@pytest.mark.asyncio
class TestExecuteAITool:
    """Tests for execute_ai_tool function."""
    
    async def test_discover_events_execution(self, monkeypatch, mock_event):
        """Test executing discover_events tool."""
        from soorma.registry.client import RegistryClient
        
        async def mock_get_events_by_topic(topic):
            return [mock_event]
        
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
        
        result = await execute_ai_tool(
            "discover_events",
            {"topic": "test-topic"}
        )
        
        assert result["success"] is True
        assert "events" in result
        assert result["count"] == 1
        assert result["events"][0]["name"] == "test.event"
    
    async def test_get_event_schema_execution(self, monkeypatch, mock_event):
        """Test executing get_event_schema tool."""
        from soorma.registry.client import RegistryClient
        
        async def mock_get_event(event_name):
            return mock_event if event_name == "test.event" else None
        
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
        
        result = await execute_ai_tool(
            "get_event_schema",
            {"event_name": "test.event"}
        )
        
        assert result["success"] is True
        assert "event" in result
        assert result["event"]["name"] == "test.event"
        assert "payload_fields" in result["event"]
    
    async def test_get_event_schema_not_found(self, monkeypatch):
        """Test get_event_schema with non-existent event."""
        from soorma.registry.client import RegistryClient
        
        async def mock_get_event(event_name):
            return None
        
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
        
        result = await execute_ai_tool(
            "get_event_schema",
            {"event_name": "nonexistent"}
        )
        
        assert result["success"] is False
        assert "error" in result
        assert "suggestion" in result
    
    async def test_create_event_payload_execution(self, monkeypatch, mock_event):
        """Test executing create_event_payload tool."""
        from soorma.registry.client import RegistryClient
        
        async def mock_get_event(event_name):
            return mock_event if event_name == "test.event" else None
        
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
        
        result = await execute_ai_tool(
            "create_event_payload",
            {
                "event_name": "test.event",
                "payload_data": {"message": "Hello"}
            }
        )
        
        assert result["success"] is True
        assert "payload" in result
        assert result["payload"]["message"] == "Hello"
    
    async def test_create_event_payload_validation_error(self, monkeypatch, mock_event):
        """Test create_event_payload with invalid data."""
        from soorma.registry.client import RegistryClient
        
        async def mock_get_event(event_name):
            return mock_event
        
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
        
        result = await execute_ai_tool(
            "create_event_payload",
            {
                "event_name": "test.event",
                "payload_data": {}  # Missing required field
            }
        )
        
        assert result["success"] is False
        assert "error" in result
        assert "suggestion" in result
    
    async def test_unknown_tool(self):
        """Test executing unknown tool."""
        result = await execute_ai_tool("unknown_tool", {})
        
        assert result["success"] is False
        assert "Unknown tool" in result["error"]
        assert "available_tools" in result


class TestFormatToolResult:
    """Tests for format_tool_result_for_llm function."""
    
    def test_format_error_result(self):
        """Test formatting error result."""
        result = {
            "success": False,
            "error": "Something went wrong",
            "suggestion": "Try this instead"
        }
        
        formatted = format_tool_result_for_llm(result)
        
        assert "❌" in formatted
        assert "Something went wrong" in formatted
        assert "Try this instead" in formatted
    
    def test_format_discover_events_result(self):
        """Test formatting discover_events result."""
        result = {
            "success": True,
            "events": [
                {
                    "name": "test.event",
                    "topic": "test-topic",
                    "description": "A test event",
                    "required_fields": ["field1", "field2"],
                    "has_response": True,
                }
            ],
            "count": 1,
        }
        
        formatted = format_tool_result_for_llm(result)
        
        assert "1 event(s)" in formatted
        assert "test.event" in formatted
        assert "test-topic" in formatted
        assert "A test event" in formatted
        assert "field1, field2" in formatted
        assert "Has response: Yes" in formatted
    
    def test_format_discover_events_empty(self):
        """Test formatting empty discover_events result."""
        result = {
            "success": True,
            "events": [],
            "count": 0,
        }
        
        formatted = format_tool_result_for_llm(result)
        
        assert "No events found" in formatted
    
    def test_format_get_event_schema_result(self):
        """Test formatting get_event_schema result."""
        result = {
            "success": True,
            "event": {
                "name": "test.event",
                "description": "Test event",
                "topic": "test-topic",
                "payload_fields": {
                    "message": {
                        "type": "string",
                        "description": "Test message",
                        "required": True,
                    }
                },
                "example_payload": {"message": "example"},
                "has_response": False,
            }
        }
        
        formatted = format_tool_result_for_llm(result)
        
        assert "test.event" in formatted
        assert "Test event" in formatted
        assert "Payload Fields:" in formatted
        assert "message" in formatted
        assert "string" in formatted
        assert "required" in formatted
    
    def test_format_create_payload_result(self):
        """Test formatting create_event_payload result."""
        result = {
            "success": True,
            "payload": {"message": "Hello"},
        }
        
        formatted = format_tool_result_for_llm(result)
        
        assert "✅" in formatted
        assert "Payload validated successfully" in formatted
        assert "Hello" in formatted
    
    def test_format_validate_response_result(self):
        """Test formatting validate_event_response result."""
        result = {
            "success": True,
            "validated_response": {"status": "ok"},
        }
        
        formatted = format_tool_result_for_llm(result)
        
        assert "✅" in formatted
        assert "Response validated successfully" in formatted
        assert "status" in formatted
