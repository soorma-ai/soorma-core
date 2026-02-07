"""
Tests for Tool Model Refactoring (Stage 3, Phase 1).

RF-SDK-005: Tool Synchronous Model with on_invoke() decorator.

This tests the refactored Tool implementation:
- InvocationContext class for lightweight invocation context
- on_invoke(event_type) decorator for multiple event handlers
- Auto-publishing to response_event (caller-specified or default)
- Return type validation against schema
- Registry publishing with multi-event support
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass
from typing import Dict, Any, Optional
from uuid import uuid4

from soorma.agents.tool import Tool, InvocationContext
from soorma.context import PlatformContext, BusClient
from soorma_common.events import EventEnvelope, EventTopic


class TestInvocationContext:
    """Tests for InvocationContext class."""
    
    def test_invocation_context_creation(self):
        """Test creating InvocationContext directly."""
        ctx = InvocationContext(
            request_id="req-123",
            event_type="calculate.requested",
            correlation_id="corr-456",
            data={"expression": "2 + 2"},
            response_event="calculate.completed",
            response_topic="action-results",
            tenant_id="tenant-1",
            user_id="user-1",
        )
        
        assert ctx.request_id == "req-123"
        assert ctx.event_type == "calculate.requested"
        assert ctx.correlation_id == "corr-456"
        assert ctx.data == {"expression": "2 + 2"}
        assert ctx.response_event == "calculate.completed"
        assert ctx.response_topic == "action-results"
        assert ctx.tenant_id == "tenant-1"
        assert ctx.user_id == "user-1"
    
    def test_invocation_context_from_event(self):
        """Test creating InvocationContext from EventEnvelope."""
        event_data = {
            "request_id": "req-789",
            "correlation_id": "corr-999",
            "expression": "5 * 3",
        }
        
        event = EventEnvelope(
            id=str(uuid4()),
            source="test-tool",
            type="calculate.requested",
            data=event_data,
            topic=EventTopic.ACTION_REQUESTS,
            correlation_id="corr-999",
            response_event="custom.response",
            response_topic="action-results",
            tenant_id="tenant-1",
            user_id="user-1",
        )
        
        # Create a mock PlatformContext
        mock_context = MagicMock(spec=PlatformContext)
        
        ctx = InvocationContext.from_event(event, mock_context)
        
        assert ctx.request_id == "req-789"
        assert ctx.event_type == "calculate.requested"
        assert ctx.correlation_id == "corr-999"
        assert ctx.response_event == "custom.response"
        assert ctx.response_topic == "action-results"
        assert ctx.data == event_data
        assert ctx.tenant_id == "tenant-1"
        assert ctx.user_id == "user-1"
    
    def test_invocation_context_from_event_auto_generates_request_id(self):
        """Test that missing request_id is auto-generated."""
        event_data = {
            "expression": "5 * 3",
        }
        
        event = EventEnvelope(
            id=str(uuid4()),
            source="test-tool",
            type="calculate.requested",
            data=event_data,
            topic=EventTopic.ACTION_REQUESTS,
            response_event="custom.response",
            tenant_id="tenant-1",
            user_id="user-1",
        )
        
        mock_context = MagicMock(spec=PlatformContext)
        
        ctx = InvocationContext.from_event(event, mock_context)
        
        # Request ID should be generated (not in original data)
        assert ctx.request_id is not None
        assert len(ctx.request_id) > 0
    
    def test_invocation_context_default_response_topic(self):
        """Test that response_topic defaults to 'action-results' when not provided."""
        event_data = {
            "request_id": "req-123",
        }
        
        event = EventEnvelope(
            id=str(uuid4()),
            source="test-tool",
            type="test.requested",
            data=event_data,
            topic=EventTopic.ACTION_REQUESTS,
            response_event="my.response",
            tenant_id="tenant-1",
            user_id="user-1",
        )
        
        mock_context = MagicMock(spec=PlatformContext)
        
        ctx = InvocationContext.from_event(event, mock_context)
        
        assert ctx.response_topic == "action-results"


class TestToolOnInvokeDecorator:
    """Tests for Tool.on_invoke() decorator."""
    
    def test_tool_on_invoke_basic_registration(self):
        """Test basic on_invoke() decorator registers handler."""
        tool = Tool(
            name="calculator",
            description="Simple calculator",
        )
        
        @tool.on_invoke("calculate")
        async def handle_calculate(request: InvocationContext, context: PlatformContext):
            return {"result": 4}
        
        # Handler should be registered
        assert "calculate" in tool._operation_handlers
        assert tool._operation_handlers["calculate"] == handle_calculate
    
    def test_tool_multiple_on_invoke_handlers(self):
        """Test that Tool can have multiple on_invoke() handlers for different event types."""
        tool = Tool(
            name="calculator",
            description="Multi-function calculator",
        )
        
        @tool.on_invoke("add")
        async def handle_add(request: InvocationContext, context: PlatformContext):
            return {"result": request.data["a"] + request.data["b"]}
        
        @tool.on_invoke("multiply")
        async def handle_multiply(request: InvocationContext, context: PlatformContext):
            return {"result": request.data["a"] * request.data["b"]}
        
        # Both should be registered
        assert "add" in tool._operation_handlers
        assert "multiply" in tool._operation_handlers
        assert len(tool._operation_handlers) >= 2
    
    def test_tool_on_invoke_adds_to_capabilities(self):
        """Test that on_invoke() automatically adds event type to capabilities."""
        tool = Tool(
            name="calculator",
            description="Calculator",
            capabilities=[],
        )
        
        @tool.on_invoke("calculate")
        async def handle(request: InvocationContext, context: PlatformContext):
            return {}
        
        # Event type should be added to capabilities
        assert "calculate" in tool.config.capabilities
    
    def test_tool_on_invoke_requires_event_type(self):
        """Test that on_invoke() requires event_type parameter."""
        tool = Tool(name="test", description="Test")
        
        # Should require event_type - this will raise TypeError at call time
        with pytest.raises(TypeError):
            @tool.on_invoke()  # Missing event_type
            async def handle():
                pass


class TestToolResponsePublishing:
    """Tests for automatic response publishing."""
    
    @pytest.mark.asyncio
    async def test_tool_handler_execution(self):
        """Test that tool handler can be executed directly."""
        tool = Tool(name="calculator", description="Test")
        
        @tool.on_invoke("calculate")
        async def handle_calc(request: InvocationContext, context: PlatformContext):
            return {"result": 4, "expression": "2 + 2"}
        
        # Create mock context
        mock_context = MagicMock(spec=PlatformContext)
        
        # Create invocation
        invocation = InvocationContext(
            request_id="req-123",
            event_type="calculate",
            correlation_id="corr-456",
            data={"expression": "2 + 2"},
            response_event="math.calculated",
            response_topic="action-results",
            tenant_id="tenant-1",
            user_id="user-1",
        )
        
        # Execute handler directly
        result = await handle_calc(invocation, mock_context)
        
        assert result == {"result": 4, "expression": "2 + 2"}


class TestReturnTypeValidation:
    """Tests for return type validation against schema."""
    
    def test_tool_stores_response_schema(self):
        """Test that Tool stores response schema when provided."""
        response_schema = {
            "type": "object",
            "properties": {
                "result": {"type": "number"},
            },
            "required": ["result"],
        }
        
        tool = Tool(name="calculator", description="Test")
        
        @tool.on_invoke("calculate", response_schema=response_schema)
        async def handle(request: InvocationContext, context: PlatformContext):
            return {"result": 42}
        
        # Schema should be stored
        assert "calculate" in tool._response_schemas
        assert tool._response_schemas["calculate"] == response_schema


class TestToolRegistry:
    """Tests for Tool registry integration."""
    
    def test_tool_events_consumed_populated_by_decorator(self):
        """Test that Tool's events_consumed is populated by @on_invoke()."""
        tool = Tool(name="test", description="Test")
        
        @tool.on_invoke("test.requested")
        async def handle(request: InvocationContext, context: PlatformContext):
            return {}
        
        # Event type (not topic) should be in events_consumed
        assert "test.requested" in tool.config.events_consumed
    
    def test_tool_no_topics_in_events_lists(self):
        """Test that topic names are NOT in events_consumed/events_produced."""
        tool = Tool(name="test", description="Test")
        
        # Topics should NOT be in events lists (they're specified in decorators)
        assert "action-requests" not in tool.config.events_consumed
        assert "action-results" not in tool.config.events_produced
    
    def test_tool_registry_includes_multiple_event_handlers(self):
        """Test that Tool's capabilities list includes all event types."""
        tool = Tool(name="calculator", description="Multi-function", capabilities=[])
        
        @tool.on_invoke("add")
        async def handle_add(request: InvocationContext, context: PlatformContext):
            return {}
        
        @tool.on_invoke("multiply")
        async def handle_multiply(request: InvocationContext, context: PlatformContext):
            return {}
        
        # Both event types should be in capabilities
        assert "add" in tool.config.capabilities
        assert "multiply" in tool.config.capabilities
        
        # Both should be in events_consumed
        assert "add" in tool.config.events_consumed
        assert "multiply" in tool.config.events_consumed


class TestToolDefaultResponseEvent:
    """Tests for default response event handling."""
    
    def test_tool_can_have_default_response_event(self):
        """Test that Tool can specify a default response_event."""
        tool = Tool(
            name="calculator",
            description="Test",
            default_response_event="calculator.completed",
        )
        
        assert tool.default_response_event == "calculator.completed"
        # Default response event should be in events_produced
        assert "calculator.completed" in tool.config.events_produced
    
    def test_tool_without_default_response_event(self):
        """Test that Tool doesn't require default_response_event."""
        tool = Tool(name="calculator", description="Test")
        
        assert tool.default_response_event is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
