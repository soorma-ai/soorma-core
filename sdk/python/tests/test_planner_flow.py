"""Integration tests for Planner -> Worker -> Tracker flow."""

from typing import Any, Dict, List, Optional

import httpx
import pytest

from soorma_common.decisions import PlannerDecision


REQUEST_RESPONSE_MAP = {
    "data.fetch.requested": "data.fetched",
    "analysis.requested": "analysis.completed",
    "report.requested": "report.ready",
}


def _publish_decision(
    plan_id: str,
    event_type: str,
    data: Optional[Dict[str, Any]] = None,
) -> PlannerDecision:
    """Create a publish decision for tests (stub).

    Args:
        plan_id: Plan identifier.
        event_type: Event type to publish.
        data: Optional payload data.

    Returns:
        PlannerDecision instance.
    """
    raise NotImplementedError("publish decision helper not implemented")


def _complete_decision(
    plan_id: str,
    result: Dict[str, Any],
) -> PlannerDecision:
    """Create a complete decision for tests (stub).

    Args:
        plan_id: Plan identifier.
        result: Final result payload.

    Returns:
        PlannerDecision instance.
    """
    raise NotImplementedError("complete decision helper not implemented")


async def _run_feedback_flow(
    decisions: List[PlannerDecision],
    tracker_error: Optional[Exception] = None,
) -> Dict[str, Any]:
    """Run a simulated feedback flow with mocked context (stub).

    Args:
        decisions: Ordered PlannerDecision list to execute.
        tracker_error: Optional tracker exception to raise.

    Returns:
        Dictionary with context, plan, and captured calls.
    """
    raise NotImplementedError("flow helper not implemented")


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
