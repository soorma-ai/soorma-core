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
from soorma_common.events import EventTopic


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
        @agent.on_event(topic=EventTopic.BUSINESS_FACTS, event_type="test.event")
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
        @agent.on_event("test.event", topic=EventTopic.BUSINESS_FACTS)
        async def handler(event, ctx):
            pass
        
        assert "business-facts:test.event" in agent._event_handlers
    
    def test_on_event_with_keyword_args(self, agent):
        """on_event() should accept both arguments as keywords."""
        @agent.on_event(event_type="test.event", topic=EventTopic.ACTION_REQUESTS)
        async def handler(event, ctx):
            pass
        
        assert "action-requests:test.event" in agent._event_handlers
    
    def test_on_event_tracks_consumed_events(self, agent):
        """on_event() should track consumed events in config."""
        @agent.on_event(topic=EventTopic.BUSINESS_FACTS, event_type="order.created")
        async def handler(event, ctx):
            pass
        
        assert "order.created" in agent.config.events_consumed
    
    def test_multiple_handlers_same_event(self, agent):
        """Multiple handlers can be registered for the same event+topic."""
        @agent.on_event(topic=EventTopic.BUSINESS_FACTS, event_type="test.event")
        async def handler1(event, ctx):
            pass
        
        @agent.on_event(topic=EventTopic.BUSINESS_FACTS, event_type="test.event")
        async def handler2(event, ctx):
            pass
        
        handlers = agent._event_handlers.get("business-facts:test.event", [])
        assert len(handlers) == 2
    
    def test_different_topics_different_handlers(self, agent):
        """Same event_type on different topics should have separate handlers."""
        @agent.on_event(topic=EventTopic.BUSINESS_FACTS, event_type="test.event")
        async def handler1(event, ctx):
            pass
        
        @agent.on_event(topic=EventTopic.ACTION_REQUESTS, event_type="test.event")
        async def handler2(event, ctx):
            pass
        
        assert "business-facts:test.event" in agent._event_handlers
        assert "action-requests:test.event" in agent._event_handlers
        assert len(agent._event_handlers["business-facts:test.event"]) == 1
        assert len(agent._event_handlers["action-requests:test.event"]) == 1


class TestEventTopicTyping:
    """Tests for EventTopic enum usage."""
    
    @pytest.fixture
    def agent(self):
        """Create a test agent."""
        agent = Agent(
            name="test-agent",
            description="Test agent",
            version="1.0.0",
        )
        return agent
    
    def test_on_event_accepts_event_topic_enum(self, agent):
        """on_event() should accept EventTopic enum."""
        @agent.on_event("test.event", topic=EventTopic.ACTION_REQUESTS)
        async def handler(event, ctx):
            pass
        
        assert "action-requests:test.event" in agent._event_handlers
    
    def test_all_event_topics_work(self, agent):
        """All EventTopic enum values should work."""
        topics_tested = []
        
        @agent.on_event("test1", topic=EventTopic.BUSINESS_FACTS)
        async def h1(e, c): pass
        topics_tested.append(EventTopic.BUSINESS_FACTS)
        
        @agent.on_event("test2", topic=EventTopic.ACTION_REQUESTS)
        async def h2(e, c): pass
        topics_tested.append(EventTopic.ACTION_REQUESTS)
        
        @agent.on_event("test3", topic=EventTopic.ACTION_RESULTS)
        async def h3(e, c): pass
        topics_tested.append(EventTopic.ACTION_RESULTS)
        
        @agent.on_event("test4", topic=EventTopic.BILLING_EVENTS)
        async def h4(e, c): pass
        topics_tested.append(EventTopic.BILLING_EVENTS)
        
        @agent.on_event("test5", topic=EventTopic.NOTIFICATION_EVENTS)
        async def h5(e, c): pass
        topics_tested.append(EventTopic.NOTIFICATION_EVENTS)
        
        # Verify all handlers registered
        assert f"{EventTopic.BUSINESS_FACTS.value}:test1" in agent._event_handlers
        assert f"{EventTopic.ACTION_REQUESTS.value}:test2" in agent._event_handlers
        assert f"{EventTopic.ACTION_RESULTS.value}:test3" in agent._event_handlers
        assert f"{EventTopic.BILLING_EVENTS.value}:test4" in agent._event_handlers
        assert f"{EventTopic.NOTIFICATION_EVENTS.value}:test5" in agent._event_handlers
    
    def test_event_topic_has_string_value(self):
        """EventTopic enum values should have correct string values."""
        assert EventTopic.BUSINESS_FACTS.value == "business-facts"
        assert EventTopic.ACTION_REQUESTS.value == "action-requests"
        assert EventTopic.ACTION_RESULTS.value == "action-results"
        assert EventTopic.BILLING_EVENTS.value == "billing-events"
        assert EventTopic.NOTIFICATION_EVENTS.value == "notification-events"
    
    def test_string_topics_rejected(self, agent):
        """on_event() should not accept plain strings for topic (runtime error)."""
        # Strings are no longer accepted - only EventTopic enum
        with pytest.raises(AttributeError, match="'str' object has no attribute 'value'"):
            @agent.on_event("test.event", topic="business-facts")  # type: ignore
            async def handler(event, ctx):
                pass
