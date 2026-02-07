"""
Tests for Agent initialization with structured definitions (Capabilities and Events).
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from soorma import Agent, Planner, Worker, Tool
from soorma.models import AgentCapability, EventDefinition

class TestAgentStructured:
    """Tests for Agent with structured capabilities and events."""

    def test_agent_with_structured_capabilities(self):
        """Test initializing an agent with AgentCapability objects."""
        cap = AgentCapability(
            task_name="structured_cap",
            description="A structured capability",
            consumed_event="structured.request",
            produced_events=["structured.response"]
        )

        agent = Agent(
            name="structured-agent",
            capabilities=[cap]
        )

        assert len(agent.capabilities) == 1
        assert agent.capabilities[0] == cap
        assert agent.capabilities[0].task_name == "structured_cap"

    def test_agent_with_mixed_capabilities(self):
        """Test initializing an agent with mixed string and structured capabilities."""
        cap = AgentCapability(
            task_name="structured_cap",
            description="A structured capability",
            consumed_event="structured.request",
            produced_events=["structured.response"]
        )

        agent = Agent(
            name="mixed-agent",
            capabilities=["string_cap", cap]
        )

        assert len(agent.capabilities) == 2
        assert "string_cap" in agent.capabilities
        assert cap in agent.capabilities

    def test_agent_with_structured_events(self):
        """Test initializing an agent with EventDefinition objects."""
        event_def = EventDefinition(
            event_name="custom.event",
            topic="business-facts",
            description="A custom event",
            payload_schema={"type": "object"}
        )

        agent = Agent(
            name="event-agent",
            events_consumed=[event_def],
            events_produced=["simple.event", event_def]
        )

        # Check that event types are extracted for consumption/production lists
        assert "custom.event" in agent.config.events_consumed
        assert "simple.event" in agent.config.events_produced
        assert "custom.event" in agent.config.events_produced
        
        # Check that definitions are stored
        assert len(agent.config.event_definitions) == 2  # One from consumed, one from produced (same object)
        assert agent.config.event_definitions[0] == event_def

    @pytest.mark.asyncio
    async def test_agent_registers_events_on_start(self):
        """Test that the agent registers event definitions with the registry on start."""
        event_def = EventDefinition(
            event_name="custom.event",
            topic="business-facts",
            description="A custom event",
            payload_schema={"type": "object"}
        )

        agent = Agent(
            name="registration-agent",
            events_produced=[event_def]
        )

        # Mock the context and registry
        mock_context = MagicMock()
        mock_registry = AsyncMock()
        mock_context.registry = mock_registry
        mock_context.bus = AsyncMock()
        
        # Mock register_agent to return proper response
        from soorma_common import AgentRegistrationResponse
        mock_registry.register_agent = AsyncMock(return_value=AgentRegistrationResponse(
            agent_id="test",
            success=True,
            message="registered"
        ))

        # Mock _initialize_context to set our mock context
        with patch.object(agent, '_initialize_context', return_value=None):
            agent._context = mock_context

            # Mock other startup methods to avoid side effects
            with patch.object(agent, '_start_heartbeat', new_callable=AsyncMock), \
                 patch.object(agent, '_subscribe_to_events', new_callable=AsyncMock):
                
                await agent.start()

        # Verify register_event was called
        mock_registry.register_event.assert_called()
        # Verify register_agent was called
        mock_registry.register_agent.assert_called()

    @pytest.mark.asyncio
    async def test_planner_with_structured_capabilities(self):
        cap = AgentCapability(
            task_name="planning_cap",
            description="Planning capability",
            consumed_event="plan.request",
            produced_events=["plan.result"]
        )
        planner = Planner(name="test-planner", capabilities=[cap])
        
        assert cap in planner.capabilities
        # Planner specific check
        assert "action.request" in planner.config.events_produced

    def test_worker_with_structured_capabilities(self):
        """Test Worker with structured capabilities."""
        cap = AgentCapability(
            task_name="worker_cap",
            description="Worker capability",
            consumed_event="work.request",
            produced_events=["work.result"]
        )
        worker = Worker(name="test-worker", capabilities=[cap])
        
        assert cap in worker.capabilities
        # Worker specific check
        assert "action.request" in worker.config.events_consumed
        assert "action.result" in worker.config.events_produced

    def test_tool_with_structured_capabilities(self):
        """Test Tool with structured capabilities."""
        cap = AgentCapability(
            task_name="tool_cap",
            description="Tool capability",
            consumed_event="tool.request",
            produced_events=["tool.response"]
        )
        tool = Tool(name="test-tool", capabilities=[cap])
        
        assert cap in tool.capabilities
        # Tools do NOT have topic names in events lists (only actual event types)
        # Event types get added dynamically via @on_invoke() decorators
        assert "action-requests" not in tool.config.events_consumed
        assert "action-results" not in tool.config.events_produced
