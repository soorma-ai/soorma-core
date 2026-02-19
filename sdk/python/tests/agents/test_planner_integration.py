"""Integration tests for Planner with PlanContext.

These tests verify end-to-end integration of:
- @on_goal decorator creating plans
- @on_transition decorator routing events  
- PlanContext lifecycle (create, persist, execute)

Note: Detailed state machine behavior is tested in test_plan_context.py.
      These integration tests focus on decorator-level orchestration.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from soorma.agents.planner import Planner, GoalContext
from soorma.plan_context import PlanContext
from soorma.context import PlatformContext
from soorma_common.events import EventEnvelope, EventTopic
from soorma_common.state import StateConfig, StateAction, StateTransition


@pytest.mark.asyncio
class TestPlannerIntegration:
    """Integration tests for Planner decorators and PlanContext."""

    async def test_goal_decorator_creates_and_persists_plan(self):
        """Test @on_goal decorator creates plan and persists it.
        
        Verifies:
        - Goal handler receives GoalContext wrapper
        - PlanContext can be created and saved
        - Memory service receives persist call
        """
        # Setup planner
        config = MagicMock()
        config.agent_id = "test-planner"
        config.events_consumed = []
        
        planner = Planner(config)
        
        # Mock context
        context = MagicMock(spec=PlatformContext)
        context.memory = MagicMock()
        context.memory.store_plan_context = AsyncMock()
        
        # Track plan creation
        created_plan =None
        
        @planner.on_goal("test.goal")
        async def handle_goal(goal: GoalContext, ctx: PlatformContext) -> None:
            """Goal handler that creates a plan."""
            nonlocal created_plan
            
            # Create simple plan
            states = {
                "start": StateConfig(
                    state_name="start",
                    description="Initial state",
                    is_terminal=True,
                )
            }
            
            created_plan = PlanContext(
                plan_id=str(uuid4()),
                goal_event=goal.event_type,
                goal_data=goal.data,
                response_event=goal.response_event,
                state_machine=states,
                current_state="start",
                status="pending",
                results={},
                _context=ctx,
            )
            
            await created_plan.save()
        
        # Send goal event
        goal_event = EventEnvelope(
            id=str(uuid4()),
            source="test-user",
            type="test.goal",
            topic=EventTopic.ACTION_REQUESTS,
            data={"input": "test"},
            response_event="test.result",
        )
        
        # Trigger handler
        goal_ctx = GoalContext.from_event(goal_event, context)
        await planner._goal_handlers["test.goal"](goal_ctx, context)
        
        # Verify plan created and persisted
        assert created_plan is not None
        assert created_plan.goal_event == "test.goal"
        assert created_plan.goal_data == {"input": "test"}
        context.memory.store_plan_context.assert_called_once()

    @pytest.mark.skip(reason="GoalContext requires full event - covered by unit tests")
    async def test_multiple_goals_registered_independently(self):
        """Test multiple @on_goal decorators register separately.
        
        Verifies:
        - Each goal gets its own handler
        - Handlers don't interfere with each other
        """
        config = MagicMock()
        config.agent_id = "test-planner"
        config.events_consumed = []
        
        planner = Planner(config)
        
        # Track which handlers were called
        calls = []
        
        @planner.on_goal("goal.one")
        async def handle_one(goal: GoalContext, ctx: PlatformContext) -> None:
            calls.append("one")
        
        @planner.on_goal("goal.two")
        async def handle_two(goal: GoalContext, ctx: PlatformContext) -> None:
            calls.append("two")
        
        # Verify both registered
        assert "goal.one" in planner._goal_handlers
        assert "goal.two" in planner._goal_handlers
        
        # Call handlers
        context = MagicMock()
        goal1 = GoalContext(event_type="goal.one", data={}, correlation_id="c1", response_event="r1")
        goal2 = GoalContext(event_type="goal.two", data={}, correlation_id="c2", response_event="r2")
        
        await planner._goal_handlers["goal.one"](goal1, context)
        await planner._goal_handlers["goal.two"](goal2, context)
        
        assert calls == ["one", "two"]

    @pytest.mark.skip(reason="Plan restoration details covered by unit tests")
    async def test_transition_decorator_routes_by_correlation_id(self):
        """Test @on_transition decorator loads plan by correlation_id.
        
        Verifies:
        - Transition handler registered
        - Plan restoration by correlation_id works
        - State transitions execute
        """
        config = MagicMock()
        config.agent_id = "test-planner"
        config.events_consumed = []
        
        planner = Planner(config)
        
        # Mock context
        context = MagicMock(spec=PlatformContext)
        context.memory = MagicMock()
        
        # Create mock plan data
        plan_data = {
            "plan_id": "plan-123",
            "goal_event": "test.goal",
            "goal_data": {},
            "response_event": "test.result",
            "status": "running",
            "state_machine": {
                "start": {
                    "state_name": "start",
                    "description": "Start",
                    "is_terminal": True,
                    "default_next": None,
                    "action": None,
                    "transitions": []
                }
            },
            "current_state": "start",
            "results": {},
            "parent_plan_id": None,
            "session_id": None,
            "user_id": "",
            "tenant_id": "",
        }
        
        context.memory.get_plan_by_correlation = AsyncMock(return_value=plan_data)
        
        # Track handler calls
        handled_plan = None
        
        @planner.on_transition()
        async def handle_transition(event: EventEnvelope, ctx: PlatformContext, plan: PlanContext, next_state: str) -> None:
            """Transition handler that receives plan."""
            nonlocal handled_plan
            handled_plan = plan
        
        # Verify handler registered
        assert planner._transition_handler is not None
        
        # Send event with correlation_id
        event = EventEnvelope(
            id=str(uuid4()),
            source="worker",
            type="task.complete",
            topic=EventTopic.ACTION_RESULTS,
            correlation_id="plan-123",
        )
        
        # Trigger handler
        await planner._transition_handler(event, context)
        
        # Verify plan restored via decorator
        assert handled_plan is not None
        assert handled_plan.plan_id == "plan-123"
