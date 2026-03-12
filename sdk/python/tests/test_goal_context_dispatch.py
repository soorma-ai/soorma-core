"""
TDD tests for GoalContext.dispatch().

The dispatch() method is the planner-side mirror of TaskContext.delegate():
it wraps context.bus.request() and auto-propagates tenant_id, user_id,
correlation_id, and session_id from the GoalContext so callers never pass
them manually.

RED phase: these tests describe the REAL expected behaviour and will fail
with NotImplementedError until dispatch() is implemented.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from dataclasses import dataclass

from soorma.agents.planner import GoalContext
from soorma.context import PlatformContext
from soorma_common.events import EventEnvelope


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_goal_context(
    correlation_id: str = "corr-123",
    tenant_id: str = "tenant-abc",
    user_id: str = "user-xyz",
    session_id: str = "sess-1",
    response_event: str = "research.completed",
    response_schema_name: str | None = None,
) -> tuple[GoalContext, MagicMock]:
    """Build a GoalContext with a mocked PlatformContext and return both."""
    mock_context = MagicMock(spec=PlatformContext)
    mock_context.bus = MagicMock()
    mock_context.bus.request = AsyncMock(return_value="event-id-999")

    raw_event = MagicMock(spec=EventEnvelope)
    raw_event.type = "research.goal"
    raw_event.data = {"description": "AI trends"}
    raw_event.correlation_id = correlation_id
    raw_event.response_event = response_event
    raw_event.response_schema_name = response_schema_name
    raw_event.session_id = session_id
    raw_event.user_id = user_id
    raw_event.tenant_id = tenant_id

    goal = GoalContext.from_event(raw_event, mock_context)
    return goal, mock_context


# ---------------------------------------------------------------------------
# TestGoalContextDispatch
# ---------------------------------------------------------------------------

class TestGoalContextDispatch:
    """GoalContext.dispatch() automatically propagates routing context."""

    @pytest.mark.asyncio
    async def test_dispatch_calls_bus_request(self):
        """dispatch() delegates to context.bus.request()."""
        goal, mock_context = _make_goal_context()

        await goal.dispatch(
            event_type="research.requested",
            data={"topic": "AI trends"},
            response_event="research.worker.completed",
        )

        mock_context.bus.request.assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatch_propagates_tenant_id(self):
        """dispatch() passes tenant_id from goal envelope — never requires manual passing."""
        goal, mock_context = _make_goal_context(tenant_id="tenant-abc")

        await goal.dispatch(
            event_type="research.requested",
            data={},
            response_event="research.worker.completed",
        )

        call_kwargs = mock_context.bus.request.call_args[1]
        assert call_kwargs["tenant_id"] == "tenant-abc"

    @pytest.mark.asyncio
    async def test_dispatch_propagates_user_id(self):
        """dispatch() passes user_id from goal envelope."""
        goal, mock_context = _make_goal_context(user_id="user-xyz")

        await goal.dispatch(
            event_type="research.requested",
            data={},
            response_event="research.worker.completed",
        )

        call_kwargs = mock_context.bus.request.call_args[1]
        assert call_kwargs["user_id"] == "user-xyz"

    @pytest.mark.asyncio
    async def test_dispatch_propagates_correlation_id(self):
        """dispatch() threads the goal's correlation_id so result handler can correlate."""
        goal, mock_context = _make_goal_context(correlation_id="corr-123")

        await goal.dispatch(
            event_type="research.requested",
            data={},
            response_event="research.worker.completed",
        )

        call_kwargs = mock_context.bus.request.call_args[1]
        assert call_kwargs["correlation_id"] == "corr-123"

    @pytest.mark.asyncio
    async def test_dispatch_passes_response_event(self):
        """dispatch() passes the caller-supplied response_event through."""
        goal, mock_context = _make_goal_context()

        await goal.dispatch(
            event_type="research.requested",
            data={},
            response_event="research.worker.completed",
        )

        call_kwargs = mock_context.bus.request.call_args[1]
        assert call_kwargs["response_event"] == "research.worker.completed"

    @pytest.mark.asyncio
    async def test_dispatch_passes_event_type_and_data(self):
        """dispatch() forwards event_type and data to bus.request()."""
        goal, mock_context = _make_goal_context()

        await goal.dispatch(
            event_type="research.requested",
            data={"topic": "quantum computing", "max_results": 5},
            response_event="research.worker.completed",
        )

        call_kwargs = mock_context.bus.request.call_args[1]
        assert call_kwargs["event_type"] == "research.requested"
        assert call_kwargs["data"] == {"topic": "quantum computing", "max_results": 5}

    @pytest.mark.asyncio
    async def test_dispatch_default_response_topic(self):
        """dispatch() defaults response_topic to action-results."""
        goal, mock_context = _make_goal_context()

        await goal.dispatch(
            event_type="research.requested",
            data={},
            response_event="research.worker.completed",
        )

        call_kwargs = mock_context.bus.request.call_args[1]
        assert call_kwargs["response_topic"] == "action-results"

    @pytest.mark.asyncio
    async def test_dispatch_custom_response_topic(self):
        """dispatch() passes a caller-supplied response_topic through."""
        goal, mock_context = _make_goal_context()

        await goal.dispatch(
            event_type="research.requested",
            data={},
            response_event="research.worker.completed",
            response_topic="custom-results",
        )

        call_kwargs = mock_context.bus.request.call_args[1]
        assert call_kwargs["response_topic"] == "custom-results"

    @pytest.mark.asyncio
    async def test_dispatch_returns_event_id(self):
        """dispatch() returns the event ID from bus.request()."""
        goal, mock_context = _make_goal_context()

        result = await goal.dispatch(
            event_type="research.requested",
            data={},
            response_event="research.worker.completed",
        )

        assert result == "event-id-999"

    @pytest.mark.asyncio
    async def test_dispatch_propagates_session_id(self):
        """dispatch() passes session_id from goal envelope."""
        goal, mock_context = _make_goal_context(session_id="sess-1")

        await goal.dispatch(
            event_type="research.requested",
            data={},
            response_event="research.worker.completed",
        )

        call_kwargs = mock_context.bus.request.call_args[1]
        assert call_kwargs.get("session_id") == "sess-1"
