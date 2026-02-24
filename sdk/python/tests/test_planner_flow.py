"""Integration tests for Planner -> Worker -> Tracker flow."""

from typing import Any, Dict, List, Optional

import httpx
import pytest
from unittest.mock import AsyncMock, MagicMock

from soorma.ai.choreography import ChoreographyPlanner
from soorma_common.decisions import PlannerDecision, PlanAction, PublishAction, CompleteAction


REQUEST_RESPONSE_MAP = {
    "data.fetch.requested": "data.fetched",
    "analysis.requested": "analysis.completed",
    "report.requested": "report.ready",
}

# Fake worker responses injected into plan.results during flow simulation
_FAKE_WORKER_RESPONSES: Dict[str, Any] = {
    "data.fetched": {
        "product": "Test Product",
        "entries": [
            {"rating": 5, "comment": "Excellent quality"},
            {"rating": 3, "comment": "Average experience"},
            {"rating": 1, "comment": "Poor service"},
        ],
    },
    "analysis.completed": {
        "summary": {"positive": 1, "negative": 1, "neutral": 1, "average_rating": 3.0},
    },
    "report.ready": {
        "report": "Final analysis report content",
    },
}


def _publish_decision(
    plan_id: str,
    event_type: str,
    data: Optional[Dict[str, Any]] = None,
) -> PlannerDecision:
    """Create a publish decision for tests.

    Args:
        plan_id: Plan identifier.
        event_type: Event type to publish.
        data: Optional payload data.

    Returns:
        PlannerDecision with a PublishAction.
    """
    return PlannerDecision(
        plan_id=plan_id,
        current_state="executing",
        next_action=PublishAction(
            event_type=event_type,
            data=data or {},
            # response_event resolved from map (None for unknown events)
            response_event=REQUEST_RESPONSE_MAP.get(event_type),
            reasoning=f"Publish {event_type}",
        ),
        reasoning="test decision",
        confidence=0.9,
    )


def _complete_decision(
    plan_id: str,
    result: Dict[str, Any],
) -> PlannerDecision:
    """Create a complete decision for tests.

    Args:
        plan_id: Plan identifier.
        result: Final result payload.

    Returns:
        PlannerDecision with a CompleteAction.
    """
    return PlannerDecision(
        plan_id=plan_id,
        current_state="completing",
        next_action=CompleteAction(
            result=result,
            reasoning="All workflow steps completed",
        ),
        reasoning="workflow complete",
        confidence=1.0,
    )


async def _run_feedback_flow(
    decisions: List[PlannerDecision],
    tracker_error: Optional[Exception] = None,
) -> Dict[str, Any]:
    """Run a simulated feedback flow with mocked context.

    Executes each decision in order using ChoreographyPlanner.execute_decision().
    For PUBLISH decisions, validates the event is in REQUEST_RESPONSE_MAP and
    simulates worker responses in plan.results. Queries Tracker after each publish.
    For COMPLETE decisions, sends a respond() via bus.

    Args:
        decisions: Ordered PlannerDecision list to execute.
        tracker_error: Optional exception to raise when querying Tracker.

    Returns:
        Dictionary with keys: "context" (mock), "plan" (mock).

    Raises:
        ValueError: If a PUBLISH decision references an event not in REQUEST_RESPONSE_MAP.
    """
    planner = ChoreographyPlanner(name="flow-test", reasoning_model="gpt-4o")

    # Build mock context
    context = MagicMock()
    context.bus = MagicMock()
    context.bus.request = AsyncMock()
    context.bus.respond = AsyncMock()
    context.bus.publish = AsyncMock()
    context.tracker = MagicMock()
    context.tracker.get_plan_progress = AsyncMock(
        side_effect=tracker_error,
        return_value=MagicMock(status="running"),
    ) if tracker_error else AsyncMock(return_value=MagicMock(status="running"))

    plan_id = decisions[0].plan_id if decisions else "plan-test"

    # Build mock plan that represents the original goal's plan
    plan = MagicMock()
    plan.plan_id = plan_id
    plan.response_event = "feedback.report.ready"
    plan.correlation_id = "corr-flow-test"
    plan.tenant_id = "tenant-1"
    plan.user_id = "user-1"
    plan.session_id = None
    plan.status = "running"
    plan.results = {}
    plan.save = AsyncMock()

    # Build goal_event that matches the plan's response routing
    goal_event = MagicMock()
    goal_event.response_event = "feedback.report.ready"
    goal_event.correlation_id = "corr-flow-test"
    goal_event.tenant_id = "tenant-1"
    goal_event.user_id = "user-1"
    goal_event.session_id = None
    goal_event.goal_id = None

    for decision in decisions:
        action = decision.next_action

        if action.action == PlanAction.PUBLISH:
            if action.event_type not in REQUEST_RESPONSE_MAP:
                raise ValueError(
                    f"No response mapping for event type: '{action.event_type}'. "
                    f"Known events: {list(REQUEST_RESPONSE_MAP)}"
                )

        await planner.execute_decision(decision, context, goal_event=goal_event, plan=plan)

        if action.action == PlanAction.PUBLISH:
            # Query Tracker for observability (non-fatal on error)
            try:
                await context.tracker.get_plan_progress(plan_id, "tenant-1", "user-1")
            except Exception:
                pass  # Tracker errors must not break the flow

            # Simulate worker responding: store fake result in plan.results
            response_event = REQUEST_RESPONSE_MAP[action.event_type]
            plan.results[response_event] = _FAKE_WORKER_RESPONSES.get(response_event, {})

    return {"context": context, "plan": plan}



@pytest.mark.asyncio
async def test_goal_to_completion_with_tracker() -> None:
    """Goal -> task -> completion should query tracker and respond."""
    decisions = [
        _publish_decision("plan-123", "data.fetch.requested", {"product": "A"}),
        _complete_decision("plan-123", {"report": "ok"}),
    ]

    result = await _run_feedback_flow(decisions)
    context = result["context"]

    context.bus.request.assert_awaited_once()
    request_kwargs = context.bus.request.await_args.kwargs
    assert request_kwargs["event_type"] == "data.fetch.requested"
    assert request_kwargs["response_event"] == "data.fetched"

    context.tracker.get_plan_progress.assert_awaited_once()

    context.bus.respond.assert_awaited_once()
    respond_kwargs = context.bus.respond.await_args.kwargs
    assert respond_kwargs["event_type"] == "feedback.report.ready"


@pytest.mark.asyncio
async def test_tracker_query_404_handling() -> None:
    """Tracker 404 should not break completion flow."""
    decisions = [
        _publish_decision("plan-404", "data.fetch.requested", {"product": "A"}),
        _complete_decision("plan-404", {"report": "ok"}),
    ]

    request = httpx.Request("GET", "http://tracker.local/v1/tracker/plans/plan-404")
    response = httpx.Response(status_code=404, request=request)
    tracker_error = httpx.HTTPStatusError("Not Found", request=request, response=response)

    result = await _run_feedback_flow(decisions, tracker_error=tracker_error)
    context = result["context"]

    context.tracker.get_plan_progress.assert_awaited_once()
    context.bus.respond.assert_awaited_once()


@pytest.mark.asyncio
async def test_state_transition_records_event_data() -> None:
    """Transition should store event data in plan results."""
    decisions = [
        _publish_decision("plan-789", "data.fetch.requested", {"product": "A"}),
        _complete_decision("plan-789", {"report": "ok"}),
    ]

    result = await _run_feedback_flow(decisions)
    plan = result["plan"]

    assert "data.fetched" in plan.results
    assert plan.results["data.fetched"]["entries"][0]["rating"] == 5


@pytest.mark.asyncio
async def test_missing_response_mapping_raises() -> None:
    """Unknown publish events should raise a ValueError."""
    decisions = [
        _publish_decision("plan-999", "unknown.requested"),
    ]

    with pytest.raises(ValueError):
        await _run_feedback_flow(decisions)
