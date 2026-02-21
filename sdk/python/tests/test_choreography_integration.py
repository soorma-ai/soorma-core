"""Integration tests for ChoreographyPlanner end-to-end flows.

These tests validate the complete workflow of using ChoreographyPlanner
for autonomous orchestration.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from soorma.ai.choreography import ChoreographyPlanner
from soorma.plan_context import PlanContext
from soorma_common.decisions import PlanAction
from soorma_common.state import StateConfig


class TestChoreographyPlannerIntegration:
    """Integration tests for complete ChoreographyPlanner workflows."""
    
    @pytest.mark.asyncio
    async def test_choreography_planner_autonomous_flow(self):
        """End-to-end: Goal → Discovery → LLM → Execution (PUBLISH action)."""
        # Setup planner
        planner = ChoreographyPlanner(
            name="autonomous-test",
            reasoning_model="gpt-4o",
        )
        
        # Mock context
        context = MagicMock()
        context.toolkit.discover_actionable_events = AsyncMock(return_value=[
            MagicMock(event_name="search.requested", description="Search for info"),
        ])
        context.bus.publish = AsyncMock()
        
        # Mock LLM to return PUBLISH decision
        mock_litellm = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='''{
                        "plan_id": "plan-123",
                        "current_state": "search",
                        "next_action": {
                            "action": "publish",
                            "event_type": "search.requested",
                            "data": {"query": "AI agents"},
                            "reasoning": "Need to search"
                        },
                        "reasoning": "Starting search phase",
                        "confidence": 0.95
                    }'''
                )
            )
        ]
        mock_litellm.acompletion = AsyncMock(return_value=mock_response)
        planner._litellm = mock_litellm
        
        # Execute: Reason + Execute
        decision = await planner.reason_next_action(
            trigger="New goal received",
            context=context,
        )
        
        # Verify decision
        assert decision.next_action.action == PlanAction.PUBLISH
        assert decision.next_action.event_type == "search.requested"
        
        # Execute decision
        await planner.execute_decision(decision, context)
        
        # Verify event published
        context.bus.publish.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_choreography_planner_with_plan_context(self):
        """Integration: ChoreographyPlanner + PlanContext creation."""
        planner = ChoreographyPlanner(
            name="integration-test",
            reasoning_model="gpt-4o",
        )
        
        # Mock context
        context = MagicMock()
        context.memory.create_plan = AsyncMock(return_value=MagicMock(plan_id="plan-456"))
        context.memory.store_plan_context = AsyncMock()
        context.toolkit.discover_actionable_events = AsyncMock(return_value=[])
        context.bus.respond = AsyncMock()
        
        # Mock goal
        goal = MagicMock()
        goal.correlation_id = "corr-456"
        goal.data = {"topic": "AI"}
        goal.response_event = "research.completed"
        goal.session_id = "session-1"
        goal.user_id = "user-1"
        goal.tenant_id = "tenant-1"
        goal.event_type = "research.goal"
        
        # Mock LLM to return COMPLETE decision
        mock_litellm = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='''{
                        "plan_id": "plan-456",
                        "current_state": "done",
                        "next_action": {
                            "action": "complete",
                            "result": {"summary": "Research completed"},
                            "reasoning": "Goal achieved"
                        },
                        "reasoning": "All tasks done",
                        "confidence": 1.0
                    }'''
                )
            )
        ]
        mock_litellm.acompletion = AsyncMock(return_value=mock_response)
        planner._litellm = mock_litellm
        
        # Create plan using PlanContext.create_from_goal
        plan = await PlanContext.create_from_goal(
            goal=goal,
            context=context,
            state_machine={},  # ChoreographyPlanner doesn't use state machine
            current_state="reasoning",
            status="running",
        )
        
        # Verify plan created
        assert plan.plan_id == "corr-456"
        assert plan.goal_event == "research.goal"
        
        # Reason and execute
        decision = await planner.reason_next_action(
            trigger="Goal created",
            context=context,
        )
        
        await planner.execute_decision(decision, context, goal_event=goal, plan=plan)
        
        # Verify response sent
        context.bus.respond.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_choreography_planner_wait_and_resume_flow(self):
        """Integration: WAIT action pauses plan, external event resumes."""
        planner = ChoreographyPlanner(
            name="wait-test",
            reasoning_model="gpt-4o",
        )
        
        # Mock context
        context = MagicMock()
        context.toolkit.discover_actionable_events = AsyncMock(return_value=[])
        context.bus.publish = AsyncMock()
        
        # Mock plan
        plan = MagicMock()
        plan.plan_id = "plan-wait"
        plan.correlation_id = "corr-wait"
        plan.results = {}
        plan.pause = AsyncMock()
        plan.save = AsyncMock()
        
        # Mock LLM to return WAIT decision
        mock_litellm = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='''{
                        "plan_id": "plan-wait",
                        "current_state": "approval",
                        "next_action": {
                            "action": "wait",
                            "reason": "Need manager approval",
                            "expected_event": "approval.granted",
                            "timeout_seconds": 3600
                        },
                        "reasoning": "Amount exceeds threshold",
                        "confidence": 0.9
                    }'''
                )
            )
        ]
        mock_litellm.acompletion = AsyncMock(return_value=mock_response)
        planner._litellm = mock_litellm
        
        # Phase 1: WAIT decision
        decision = await planner.reason_next_action(
            trigger="Order $10000 received",
            context=context,
        )
        
        assert decision.next_action.action == PlanAction.WAIT
        
        # Execute WAIT
        await planner.execute_decision(decision, context, plan=plan)
        
        # Verify plan paused
        plan.pause.assert_called_once()
        assert plan.results["_waiting_for"] == "approval.granted"
        
        # Verify notification published
        call_args = context.bus.publish.call_args
        assert call_args.kwargs["event_type"] == "plan.waiting_for_input"
        assert call_args.kwargs["data"]["expected_event"] == "approval.granted"
    
    @pytest.mark.asyncio
    async def test_decision_validation_prevents_hallucinations(self):
        """Integration: LLM hallucination detection prevents invalid event publish."""
        planner = ChoreographyPlanner(
            name="validation-test",
            reasoning_model="gpt-4o",
        )
        
        # Mock context with limited events
        context = MagicMock()
        context.toolkit.discover_actionable_events = AsyncMock(return_value=[
            MagicMock(event_name="real.event", description="Real event"),
        ])
        
        # Mock LLM to return hallucinated event
        mock_litellm = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='''{
                        "plan_id": "plan-bad",
                        "current_state": "search",
                        "next_action": {
                            "action": "publish",
                            "event_type": "hallucinated.event",
                            "data": {},
                            "reasoning": "Trying non-existent event"
                        },
                        "reasoning": "Test hallucination",
                        "confidence": 0.5
                    }'''
                )
            )
        ]
        mock_litellm.acompletion = AsyncMock(return_value=mock_response)
        planner._litellm = mock_litellm
        
        # Attempt to reason (should detect hallucination)
        with pytest.raises(ValueError, match="not found in Registry"):
            await planner.reason_next_action(
                trigger="Bad event test",
                context=context,
            )
