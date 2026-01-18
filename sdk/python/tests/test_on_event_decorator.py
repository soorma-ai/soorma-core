"""
Tests for Agent.on_event() decorator changes.

Tests the refactored on_event() signature:
- Requires topic parameter for base Agent
- Event handlers registered with topic
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from soorma.agents.base import Agent, AgentConfig
from soorma.context import PlatformContext


class TestOnEventSignature:
    """Tests for on_event() decorator with required topic parameter."""
    
    @pytest.fixture
    def agent(self):
        """Create a test agent."""
        agent = Agent(
            name="test-agent",
            description="Test agent",
            version="1.0.0",
        )
        return agent
    
    def test_on_event_requires_topic_for_base_agent(self, agent):
        """Base Agent.on_event() should require topic parameter."""
        # This should work - topic is explicit
        @agent.on_event(topic="business-facts", event_type="test.event")
        async def handler(event, ctx):
            pass
        
        # Verify handler is registered
        assert "business-facts:test.event" in agent._event_handlers
        assert len(agent._event_handlers["business-facts:test.event"]) == 1
    
    def test_on_event_missing_topic_raises_error(self, agent):
        """on_event() without topic should raise TypeError for base Agent."""
        with pytest.raises(TypeError, match="missing 1 required keyword-only argument: 'topic'"):
            @agent.on_event(event_type="test.event")
            async def handler(event, ctx):
                pass
    
    def test_on_event_with_positional_event_type(self, agent):
        """on_event() should accept event_type as positional argument."""
        @agent.on_event("test.event", topic="business-facts")
        async def handler(event, ctx):
            pass
        
        assert "business-facts:test.event" in agent._event_handlers
    
    def test_on_event_with_keyword_args(self, agent):
        """on_event() should accept both arguments as keywords."""
        @agent.on_event(event_type="test.event", topic="action-requests")
        async def handler(event, ctx):
            pass
        
        assert "action-requests:test.event" in agent._event_handlers
    
    def test_on_event_tracks_consumed_events(self, agent):
        """on_event() should track consumed events in config."""
        @agent.on_event(topic="business-facts", event_type="order.created")
        async def handler(event, ctx):
            pass
        
        assert "order.created" in agent.config.events_consumed
    
    def test_multiple_handlers_same_event(self, agent):
        """Multiple handlers can be registered for the same event+topic."""
        @agent.on_event(topic="business-facts", event_type="test.event")
        async def handler1(event, ctx):
            pass
        
        @agent.on_event(topic="business-facts", event_type="test.event")
        async def handler2(event, ctx):
            pass
        
        handlers = agent._event_handlers.get("business-facts:test.event", [])
        assert len(handlers) == 2
    
    def test_different_topics_different_handlers(self, agent):
        """Same event_type on different topics should have separate handlers."""
        @agent.on_event(topic="business-facts", event_type="test.event")
        async def handler1(event, ctx):
            pass
        
        @agent.on_event(topic="action-requests", event_type="test.event")
        async def handler2(event, ctx):
            pass
        
        assert "business-facts:test.event" in agent._event_handlers
        assert "action-requests:test.event" in agent._event_handlers
        assert len(agent._event_handlers["business-facts:test.event"]) == 1
        assert len(agent._event_handlers["action-requests:test.event"]) == 1
