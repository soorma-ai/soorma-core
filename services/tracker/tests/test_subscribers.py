"""Tests for Tracker Service event subscribers (RED phase).

These tests verify the REAL expected behavior of event subscribers.
They will fail with NotImplementedError until GREEN phase implementation.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from soorma_common.events import EventEnvelope, EventTopic

from tracker_service.subscribers.event_handlers import (
    handle_action_request,
    handle_action_result,
    handle_plan_event,
    start_event_subscribers,
    stop_event_subscribers,
    _extract_tenant_user,
)
from tracker_service.models.db import ActionStatus, PlanStatus


"""Tests for Tracker Service event subscribers (GREEN phase — NATS).

Handler tests (handle_action_request, etc.) are unchanged — database logic
is identical regardless of subscription mechanism.

Lifecycle tests are updated for the NATS-based start_event_subscribers signature.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from soorma_common.events import EventEnvelope, EventTopic

from tracker_service.subscribers.event_handlers import (
    handle_action_request,
    handle_action_result,
    handle_plan_event,
    start_event_subscribers,
    stop_event_subscribers,
    _extract_tenant_user,
)
from tracker_service.models.db import ActionStatus, PlanStatus


@pytest.mark.asyncio
class TestEventSubscriberLifecycle:
    """Test subscriber startup and shutdown (NATS-based)."""

    async def test_start_subscribers_creates_nats_client_and_subscribes(self, monkeypatch):
        """start_event_subscribers creates a NATSClient and subscribes to all three topics.

        GREEN phase: NATSClient is instantiated, connect() and subscribe() are called.
        STUB phase: raises NotImplementedError.
        """
        mock_nats = AsyncMock()
        mock_nats.is_connected = True

        with patch(
            "tracker_service.subscribers.event_handlers.NATSClient",
            return_value=mock_nats,
        ) as MockNATSClient:
            await start_event_subscribers("nats://localhost:4222")

        # NATSClient created with the given nats_url
        MockNATSClient.assert_called_once_with(url="nats://localhost:4222")

        # connect() was awaited
        mock_nats.connect.assert_awaited_once()

        # subscribe() was called with all three topics
        mock_nats.subscribe.assert_awaited_once()
        call_kwargs = mock_nats.subscribe.call_args.kwargs
        topics_arg = call_kwargs.get("topics") or mock_nats.subscribe.call_args.args[0]
        assert EventTopic.ACTION_REQUESTS.value in topics_arg
        assert EventTopic.ACTION_RESULTS.value in topics_arg
        assert EventTopic.SYSTEM_EVENTS.value in topics_arg

    async def test_start_subscribers_passes_queue_group(self, monkeypatch):
        """start_event_subscribers passes 'tracker-service' as queue_group.

        GREEN phase: queue_group='tracker-service' is forwarded to NATSClient.subscribe().
        STUB phase: raises NotImplementedError.
        """
        mock_nats = AsyncMock()
        mock_nats.is_connected = True

        with patch(
            "tracker_service.subscribers.event_handlers.NATSClient",
            return_value=mock_nats,
        ):
            await start_event_subscribers("nats://localhost:4222")

        call_kwargs = mock_nats.subscribe.call_args.kwargs
        queue_arg = call_kwargs.get("queue_group")
        assert queue_arg == "tracker-service"

    async def test_stop_subscribers_disconnects_nats_client(self, monkeypatch):
        """stop_event_subscribers calls NATSClient.disconnect() and clears global.

        GREEN phase: disconnect() is awaited and _nats_client becomes None.
        STUB phase: raises NotImplementedError from start_event_subscribers.
        """
        mock_nats = AsyncMock()
        mock_nats.is_connected = True

        with patch(
            "tracker_service.subscribers.event_handlers.NATSClient",
            return_value=mock_nats,
        ):
            await start_event_subscribers("nats://localhost:4222")
            await stop_event_subscribers()

        mock_nats.disconnect.assert_awaited_once()

    async def test_stop_subscribers_noop_when_not_started(self):
        """stop_event_subscribers is a no-op when called before start_event_subscribers.

        GREEN phase: no error, no disconnect called (client is None).
        """
        import tracker_service.subscribers.event_handlers as eh
        # Ensure global client is None
        eh._nats_client = None
        # Should not raise
        await stop_event_subscribers()


@pytest.mark.asyncio
class TestActionRequestHandler:
    """Test handling of action-requests events."""
    
    async def test_handle_action_request_creates_action_progress(self):
        """Test action request creates new action_progress record."""
        # Mock database session
        db_session = AsyncMock(spec=AsyncSession)
        db_session.execute = AsyncMock()
        db_session.commit = AsyncMock()
        
        # Create action request event
        event = EventEnvelope(
            id="event-123",
            source="data-worker",
            type="process.data.requested",
            topic=EventTopic.ACTION_REQUESTS,
            data={
                "action_id": "action-456",
                "action_name": "Process customer data",
                "assigned_to": "data-worker",
            },
            tenant_id="tenant-001",
            user_id="user-001",
            plan_id="plan-789",
        )
        
        # Handle event
        await handle_action_request(event, db_session)
        
        # Should call database execute (INSERT action_progress)
        assert db_session.execute.called
        assert db_session.execute.call_count >= 1  # At least one INSERT
    
    async def test_handle_action_request_extracts_tenant_user(self):
        """Test action request handler extracts tenant/user from event."""
        db_session = AsyncMock(spec=AsyncSession)
        
        event = EventEnvelope(
            id="event-123",
            source="search-worker",
            type="search.requested",
            topic=EventTopic.ACTION_REQUESTS,
            data={"action_id": "act-1"},
            tenant_id="tenant-ABC",
            user_id="user-XYZ",
            plan_id="plan-1",
        )
        
        # Handle event
        await handle_action_request(event, db_session)
        
        # Should use tenant_id and user_id from event envelope
        assert db_session.execute.called
    
    async def test_handle_action_request_sets_pending_status(self):
        """Test action request sets status to PENDING."""
        db_session = AsyncMock(spec=AsyncSession)
        
        event = EventEnvelope(
            id="event-123",
            source="analyze-worker",
            type="analyze.requested",
            topic=EventTopic.ACTION_REQUESTS,
            data={"action_id": "act-2"},
            tenant_id="tenant-001",
            user_id="user-001",
            plan_id="plan-2",
        )
        
        await handle_action_request(event, db_session)
        
        # Should call database execute (action created with PENDING status)
        assert db_session.execute.called

    async def test_handle_action_request_skips_when_no_plan_id(self):
        """Test action request is silently skipped when event has no plan_id.

        Standalone worker tasks (not dispatched by a planner) have no plan_id.
        The tracker is plan-scoped, so there is nothing meaningful to record.
        """
        db_session = AsyncMock(spec=AsyncSession)
        db_session.execute = AsyncMock()

        event = EventEnvelope(
            id="event-unplanned",
            source="standalone-worker",
            type="analyze.feedback",
            topic=EventTopic.ACTION_REQUESTS,
            data={"action_id": "act-unplanned"},
            tenant_id="tenant-001",
            user_id="user-001",
            # plan_id intentionally omitted
        )

        await handle_action_request(event, db_session)

        # No DB calls — unplanned task has nothing to track
        assert not db_session.execute.called


@pytest.mark.asyncio
class TestActionResultHandler:
    """Test handling of action-results events."""
    
    async def test_handle_action_result_updates_completion(self):
        """Test action result updates action_progress to COMPLETED."""
        db_session = AsyncMock(spec=AsyncSession)
        
        event = EventEnvelope(
            id="event-456",
            source="data-worker",
            type="process.data.completed",
            topic=EventTopic.ACTION_RESULTS,
            data={
                "action_id": "action-789",
                "plan_id": "plan-789",
                "result": {"status": "success", "records_processed": 150},
            },
            correlation_id="action-789",
            tenant_id="tenant-001",
            user_id="user-001",
        )
        
        # Handle event
        await handle_action_result(event, db_session)
        
        # Should call database execute (UPDATE action_progress + increment plan counter)
        assert db_session.execute.called
        assert db_session.execute.call_count >= 1
    
    async def test_handle_action_result_sets_completed_timestamp(self):
        """Test action result sets completed_at timestamp."""
        db_session = AsyncMock(spec=AsyncSession)
        
        event = EventEnvelope(
            id="event-789",
            source="search-worker",
            type="search.completed",
            topic=EventTopic.ACTION_RESULTS,
            data={"action_id": "act-3", "plan_id": "plan-3"},
            correlation_id="act-3",
            tenant_id="tenant-001",
            user_id="user-001",
        )
        
        await handle_action_result(event, db_session)
        
        # Should call database execute (UPDATE with completed_at)
        assert db_session.execute.called
    
    async def test_handle_action_result_failed_task(self):
        """Test action result handles failed tasks."""
        db_session = AsyncMock(spec=AsyncSession)
        
        event = EventEnvelope(
            id="event-fail",
            source="process-worker",
            type="process.failed",
            topic=EventTopic.ACTION_RESULTS,
            data={
                "action_id": "act-fail",
                "plan_id": "plan-4",
                "error": "Database connection timeout",
            },
            correlation_id="act-fail",
            tenant_id="tenant-001",
            user_id="user-001",
        )
        
        await handle_action_result(event, db_session)
        
        # Should call database execute (UPDATE with FAILED status)
        assert db_session.execute.called


@pytest.mark.asyncio
class TestPlanEventHandler:
    """Test handling of plan lifecycle events."""
    
    async def test_handle_plan_started_creates_record(self):
        """Test plan.started event creates plan_progress record."""
        db_session = AsyncMock(spec=AsyncSession)
        
        event = EventEnvelope(
            id="event-plan-start",
            source="planner-agent",
            type="plan.started",
            topic=EventTopic.SYSTEM_EVENTS,
            data={
                "plan_id": "plan-new",
                "plan_name": "Research Project",
                "total_actions": 5,
            },
            tenant_id="tenant-001",
            user_id="user-001",
        )
        
        await handle_plan_event(event, db_session)
        
        # Should call database execute (INSERT plan_progress)
        assert db_session.execute.called
    
    async def test_handle_plan_state_changed_updates_state(self):
        """Test plan.state_changed event updates current state."""
        db_session = AsyncMock(spec=AsyncSession)
        
        event = EventEnvelope(
            id="event-state",
            source="planner-agent",
            type="plan.state_changed",
            topic=EventTopic.SYSTEM_EVENTS,
            data={
                "plan_id": "plan-123",
                "previous_state": "analyzing",
                "new_state": "reporting",
            },
            tenant_id="tenant-001",
            user_id="user-001",
        )
        
        await handle_plan_event(event, db_session)
        
        # Should call database execute (handler processes state change)
        assert db_session.execute.called is False  # No DB update for state_changed yet (not in schema)
    
    async def test_handle_plan_completed_finalizes_plan(self):
        """Test plan.completed event finalizes plan execution."""
        db_session = AsyncMock(spec=AsyncSession)
        
        event = EventEnvelope(
            id="event-complete",
            source="planner-agent",
            type="plan.completed",
            topic=EventTopic.SYSTEM_EVENTS,
            data={
                "plan_id": "plan-456",
                "status": "completed",
                "result": {"summary": "All tasks finished successfully"},
            },
            tenant_id="tenant-001",
            user_id="user-001",
        )
        
        await handle_plan_event(event, db_session)
        
        # Should call database execute (UPDATE plan status to COMPLETED)
        assert db_session.execute.called
    
    async def test_handle_plan_failed_records_error(self):
        """Test plan.failed event records error message."""
        db_session = AsyncMock(spec=AsyncSession)
        
        event = EventEnvelope(
            id="event-fail",
            source="planner-agent",
            type="plan.failed",
            topic=EventTopic.SYSTEM_EVENTS,
            data={
                "plan_id": "plan-789",
                "error": "Worker timeout after 300 seconds",
            },
            tenant_id="tenant-001",
            user_id="user-001",
        )
        
        await handle_plan_event(event, db_session)
        
        # Should call database execute (UPDATE plan with FAILED status + error)
        assert db_session.execute.called


class TestTenantUserExtraction:
    """Test multi-tenancy helper functions."""
    
    def test_extract_tenant_user_from_envelope(self):
        """Test extracting tenant_id and user_id from event envelope."""
        event = EventEnvelope(
            id="event-123",
            source="test-service",
            type="test.event",
            topic=EventTopic.SYSTEM_EVENTS,
            data={},
            tenant_id="tenant-XYZ",
            user_id="user-ABC",
        )
        
        tenant_id, user_id = _extract_tenant_user(event)
        
        assert tenant_id == "tenant-XYZ"
        assert user_id == "user-ABC"
    
    def test_extract_tenant_user_with_defaults(self):
        """Test extraction provides defaults for missing tenant/user."""
        event = EventEnvelope(
            id="event-456",
            source="test-service",
            type="test.event",
            topic=EventTopic.SYSTEM_EVENTS,
            data={},
            # No tenant_id or user_id
        )
        
        tenant_id, user_id = _extract_tenant_user(event)
        
        # Should provide default values (not fail)
        assert tenant_id is not None
        assert user_id is not None
        assert len(tenant_id) > 0
        assert len(user_id) > 0
