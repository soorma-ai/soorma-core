"""
Tests for Planner decorators and handler registration.

Tests cover:
- @planner.on_goal() decorator
- @planner.on_transition() decorator
- GoalContext wrapper class
- Handler-only event registration (RF-SDK-023)
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from soorma.agents.planner import Planner, GoalContext
from soorma.plan_context import PlanContext
from soorma_common.events import EventEnvelope, EventTopic


class TestPlannerOnGoalDecorator:
    """Tests for @planner.on_goal() decorator."""
    
    def test_on_goal_registers_handler(self):
        """on_goal() should register goal handler."""
        planner = Planner(name="test-planner")
        
        @planner.on_goal("research.goal")
        async def handle_goal(goal, context):
            pass
        
        assert "research.goal" in planner._goal_handlers
        assert planner._goal_handlers["research.goal"] == handle_goal
    
    def test_on_goal_registers_event_consumed(self):
        """on_goal() should add event to events_consumed (RF-SDK-023)."""
        planner = Planner(name="test-planner")
        
        @planner.on_goal("research.goal")
        async def handle_goal(goal, context):
            pass
        
        # RF-SDK-023: Only goal event types registered, not topics
        assert "research.goal" in planner.config.events_consumed
        assert "action-requests" not in planner.config.events_consumed
        assert EventTopic.ACTION_REQUESTS not in planner.config.events_consumed
    
    @pytest.mark.asyncio
    async def test_on_goal_creates_goal_context(self):
        """on_goal handler should receive GoalContext."""
        planner = Planner(name="test-planner")
        
        received_goal = None
        
        @planner.on_goal("research.goal")
        async def handle_goal(goal, context):
            nonlocal received_goal
            received_goal = goal
        
        # Create mock event
        event = EventEnvelope(
            id="evt-123",
            source="test-source",
            type="research.goal",
            topic=EventTopic.ACTION_REQUESTS,
            data={"topic": "AI"},
            correlation_id="corr-123",
            response_event="research.completed",
            user_id="user-1",
            tenant_id="tenant-1",
        )
        
        context = MagicMock()
        
        # Call the underlying handler
        await planner._goal_handlers["research.goal"](
            GoalContext.from_event(event, context),
            context
        )
        
        # Verify GoalContext created
        assert received_goal is not None
        assert isinstance(received_goal, GoalContext)
        assert received_goal.event_type == "research.goal"
        assert received_goal.data == {"topic": "AI"}
        assert received_goal.correlation_id == "corr-123"
        assert received_goal.response_event == "research.completed"


class TestGoalContext:
    """Tests for GoalContext wrapper class."""
    
    def test_goal_context_from_event(self):
        """GoalContext.from_event() should extract all fields."""
        event = EventEnvelope(
            id="evt-123",
            source="test-source",
            type="test.goal",
            topic=EventTopic.ACTION_REQUESTS,
            data={"key": "value"},
            correlation_id="corr-456",
            response_event="test.completed",
            session_id="session-789",
            user_id="user-1",
            tenant_id="tenant-1",
        )
        
        context = MagicMock()
        
        goal = GoalContext.from_event(event, context)
        
        assert goal.event_type == "test.goal"
        assert goal.data == {"key": "value"}
        assert goal.correlation_id == "corr-456"
        assert goal.response_event == "test.completed"
        assert goal.session_id == "session-789"
        assert goal.user_id == "user-1"
        assert goal.tenant_id == "tenant-1"
        assert goal._raw_event is event
        assert goal._context is context


class TestPlannerOnTransitionDecorator:
    """Tests for @planner.on_transition() decorator."""
    
    def test_on_transition_registers_handler(self):
        """on_transition() should register transition handler."""
        planner = Planner(name="test-planner")
        
        @planner.on_transition()
        async def handle_transition(event, context, plan, next_state):
            pass
        
        assert planner._transition_handler is not None
        assert planner._transition_handler == handle_transition
    
    def test_on_transition_no_topics_in_events(self):
        """on_transition() should NOT add topics to events (RF-SDK-023)."""
        planner = Planner(name="test-planner")
        
        @planner.on_transition()
        async def handle_transition(event, context, plan, next_state):
            pass
        
        # RF-SDK-023: Topics are not event types
        assert "action-requests" not in planner.config.events_consumed
        assert "action-results" not in planner.config.events_consumed
        assert EventTopic.ACTION_REQUESTS not in planner.config.events_consumed
        assert EventTopic.ACTION_RESULTS not in planner.config.events_consumed
    
    @pytest.mark.asyncio
    async def test_transition_routes_by_correlation_id(self):
        """Transition handler should restore plan by correlation_id."""
        planner = Planner(name="test-planner")
        
        restored_plan = None
        received_next_state = None
        
        @planner.on_transition()
        async def handle_transition(event, context, plan, next_state):
            nonlocal restored_plan, received_next_state
            restored_plan = plan
            received_next_state = next_state
        
        # Mock event
        event = EventEnvelope(
            id="evt-456",
            source="test-source",
            type="search.completed",
            topic=EventTopic.ACTION_RESULTS,
            data={"results": []},
            correlation_id="plan-123",
            user_id="user-1",
            tenant_id="tenant-1",
        )
        
        context = MagicMock()
        
        # Mock plan with next_state
        mock_plan = MagicMock(plan_id="plan-123")
        mock_plan.get_next_state.return_value = "summarize"
        
        # Call handler directly with required params
        await planner._transition_handler(event, context, mock_plan, "summarize")
        
        # Verify plan received
        assert restored_plan is not None
        assert restored_plan.plan_id == "plan-123"
        assert received_next_state == "summarize"


class TestHandlerOnlyRegistration:
    """Tests for RF-SDK-023: Handler-only event registration."""
    
    def test_no_events_without_handlers(self):
        """Planner with no handlers should have empty events_consumed."""
        planner = Planner(
            name="test-planner",
            capabilities=["planning", "research"],
        )
        
        # RF-SDK-023: Capabilities don't generate events
        assert len(planner.config.events_consumed) == 0
    
    def test_only_goal_events_registered(self):
        """Only events with @on_goal handlers should be in events_consumed."""
        planner = Planner(name="test-planner")
        
        @planner.on_goal("research.goal")
        async def handle_research(goal, context):
            pass
        
        @planner.on_goal("analysis.goal")
        async def handle_analysis(goal, context):
            pass
        
        # Should have exactly 2 events
        assert len(planner.config.events_consumed) == 2
        assert "research.goal" in planner.config.events_consumed
        assert "analysis.goal" in planner.config.events_consumed
    
    def test_transition_handler_no_wildcard_events(self):
        """Transition handler should NOT register wildcard events."""
        planner = Planner(name="test-planner")
        
        @planner.on_transition()
        async def handle_transition(event, context):
            pass
        
        # Wildcard subscriptions don't add to events_consumed
        assert "*" not in planner.config.events_consumed
    
    def test_multiple_decorators_combined(self):
        """Planner with both decorators should only register goal events."""
        planner = Planner(name="test-planner")
        
        @planner.on_goal("test.goal")
        async def handle_goal(goal, context):
            pass
        
        @planner.on_transition()
        async def handle_transition(event, context, plan, next_state):
            pass
        
        # Only goal event should be registered
        assert len(planner.config.events_consumed) == 1
        assert "test.goal" in planner.config.events_consumed
