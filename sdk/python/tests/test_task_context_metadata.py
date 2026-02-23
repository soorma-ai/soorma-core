"""
Tests for TaskContext envelope metadata propagation.

Verifies that:
- plan_id and goal_id are read from EventEnvelope fields (not data payload)
- task.complete() passes plan_id as envelope metadata to bus.respond()
- Workers receiving events preserve plan traceability end-to-end

These guard against plan_id / goal_id being dropped from the event envelope,
which would break Tracker Service observability and cross-service goal tracing.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from soorma.task_context import TaskContext
from soorma_common.events import EventEnvelope, EventTopic


def _make_envelope(
    *,
    plan_id: str | None = None,
    goal_id: str | None = None,
    tenant_id: str = "tenant-1",
    user_id: str = "user-1",
    session_id: str = "session-1",
    task_id: str | None = None,
    response_event: str = "task.completed",
    correlation_id: str | None = None,
) -> EventEnvelope:
    """Build a minimal EventEnvelope with controllable metadata fields."""
    data: dict = {}
    if task_id:
        data["task_id"] = task_id

    return EventEnvelope(
        source="test-worker",
        type="task.requested",
        topic=EventTopic.ACTION_REQUESTS,
        data=data,
        tenant_id=tenant_id,
        user_id=user_id,
        session_id=session_id,
        plan_id=plan_id,
        goal_id=goal_id,
        response_event=response_event,
        correlation_id=correlation_id or str(uuid4()),
    )


class TestTaskContextFromEventEnvelope:
    """TaskContext.from_event() must read plan_id and goal_id from envelope, not data."""

    def test_from_event_reads_plan_id_from_envelope(self):
        """plan_id is taken from event.plan_id (envelope metadata)."""
        event = _make_envelope(plan_id="plan-abc")
        context = MagicMock()

        task = TaskContext.from_event(event, context)

        assert task.plan_id == "plan-abc"

    def test_from_event_reads_goal_id_from_envelope(self):
        """goal_id is taken from event.goal_id (envelope metadata)."""
        event = _make_envelope(goal_id="goal-xyz")
        context = MagicMock()

        task = TaskContext.from_event(event, context)

        assert task.goal_id == "goal-xyz"

    def test_from_event_plan_id_not_read_from_data(self):
        """plan_id injected into data payload is ignored; envelope field takes precedence."""
        event = _make_envelope(plan_id="plan-envelope")
        # Manually inject a conflicting plan_id into data to simulate old behaviour
        event.data["plan_id"] = "plan-data-smuggled"
        context = MagicMock()

        task = TaskContext.from_event(event, context)

        assert task.plan_id == "plan-envelope", \
            "Envelope plan_id must win over data-smuggled plan_id"

    def test_from_event_plan_id_is_none_when_not_in_envelope(self):
        """plan_id is None when event has no plan_id (non-choreography event)."""
        event = _make_envelope(plan_id=None)
        context = MagicMock()

        task = TaskContext.from_event(event, context)

        assert task.plan_id is None

    def test_from_event_goal_id_is_none_when_not_in_envelope(self):
        """goal_id is None when event has no goal_id."""
        event = _make_envelope(goal_id=None)
        context = MagicMock()

        task = TaskContext.from_event(event, context)

        assert task.goal_id is None

    def test_from_event_preserves_tenant_and_user_from_envelope(self):
        """Standard tenant/user fields still populated correctly."""
        event = _make_envelope(tenant_id="t-99", user_id="u-42", session_id="s-7")
        context = MagicMock()

        task = TaskContext.from_event(event, context)

        assert task.tenant_id == "t-99"
        assert task.user_id == "u-42"
        assert task.session_id == "s-7"

    def test_from_event_populates_all_envelope_metadata_together(self):
        """All envelope metadata fields are extracted in a single from_event() call."""
        event = _make_envelope(
            plan_id="plan-full",
            goal_id="goal-full",
            tenant_id="t-full",
            user_id="u-full",
            session_id="s-full",
        )
        context = MagicMock()

        task = TaskContext.from_event(event, context)

        assert task.plan_id == "plan-full"
        assert task.goal_id == "goal-full"
        assert task.tenant_id == "t-full"
        assert task.user_id == "u-full"
        assert task.session_id == "s-full"


class TestTaskContextCompleteEnvelopeMetadata:
    """TaskContext.complete() must propagate plan_id in the bus.respond() envelope."""

    @pytest.mark.asyncio
    async def test_complete_passes_plan_id_in_envelope(self):
        """complete() sends plan_id as kwarg to bus.respond() (envelope metadata)."""
        event = _make_envelope(plan_id="plan-123", response_event="task.done")
        mock_context = MagicMock()
        mock_context.bus.respond = AsyncMock()
        mock_context.memory.delete_task_context = AsyncMock()

        task = TaskContext.from_event(event, mock_context)
        await task.complete({"output": "result"})

        mock_context.bus.respond.assert_called_once()
        kwargs = mock_context.bus.respond.call_args.kwargs
        assert kwargs["plan_id"] == "plan-123", \
            "plan_id must flow from incoming envelope into outgoing respond envelope"

    @pytest.mark.asyncio
    async def test_complete_plan_id_not_in_data_payload(self):
        """complete() must not inject plan_id into the data dict."""
        event = _make_envelope(plan_id="plan-123", response_event="task.done")
        mock_context = MagicMock()
        mock_context.bus.respond = AsyncMock()
        mock_context.memory.delete_task_context = AsyncMock()

        task = TaskContext.from_event(event, mock_context)
        await task.complete({"output": "result"})

        kwargs = mock_context.bus.respond.call_args.kwargs
        assert "plan_id" not in kwargs["data"], \
            "plan_id must stay in envelope metadata, not data payload"

    @pytest.mark.asyncio
    async def test_complete_omits_plan_id_kwarg_when_none(self):
        """complete() passes plan_id=None when task has no plan_id (non-choreography)."""
        event = _make_envelope(plan_id=None, response_event="task.done")
        mock_context = MagicMock()
        mock_context.bus.respond = AsyncMock()
        mock_context.memory.delete_task_context = AsyncMock()

        task = TaskContext.from_event(event, mock_context)
        await task.complete({"output": "result"})

        kwargs = mock_context.bus.respond.call_args.kwargs
        # plan_id kwarg present but None — bus.respond ignores None values
        assert kwargs.get("plan_id") is None

    @pytest.mark.asyncio
    async def test_complete_response_data_unchanged(self):
        """complete() result dict is passed through to data.result unchanged."""
        event = _make_envelope(plan_id="plan-123", response_event="task.done")
        mock_context = MagicMock()
        mock_context.bus.respond = AsyncMock()
        mock_context.memory.delete_task_context = AsyncMock()

        task = TaskContext.from_event(event, mock_context)
        result = {"summary": "5 positive, 2 negative", "score": 3.4}
        await task.complete(result)

        kwargs = mock_context.bus.respond.call_args.kwargs
        assert kwargs["data"]["result"] == result
        assert kwargs["data"]["status"] == "completed"
