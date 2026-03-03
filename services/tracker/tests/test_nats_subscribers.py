"""Tests for Tracker Service NATS subscriber integration (RED phase).

These tests assert REAL expected behavior of the NATS-based start/stop subscriber
functions. They FAIL with NotImplementedError in STUB phase and PASS in GREEN phase.

Constitution rule: Do NOT test for the stub. Test the real expected behavior.
All tests that call start_event_subscribers() FAIL in STUB phase with NotImplementedError.

RED Phase verification:
- Run: pytest tests/test_nats_subscribers.py -v
- Expected: lifecycle/dispatch tests FAIL with NotImplementedError
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call

from soorma_common.events import EventEnvelope, EventTopic
from soorma_nats import NATSClient

import tracker_service.subscribers.event_handlers as eh
from tracker_service.subscribers.event_handlers import (
    start_event_subscribers,
    stop_event_subscribers,
)


# ---------------------------------------------------------------------------
# Lifecycle tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_subscribers_creates_nats_client_with_url():
    """start_event_subscribers instantiates NATSClient with the given nats_url.

    GREEN phase: NATSClient(url=nats_url) is called.
    STUB phase: FAILS with NotImplementedError.
    """
    mock_nats = AsyncMock(spec=NATSClient)

    with patch(
        "tracker_service.subscribers.event_handlers.NATSClient",
        return_value=mock_nats,
    ) as MockClient:
        await start_event_subscribers("nats://nats:4222")

    MockClient.assert_called_once_with(url="nats://nats:4222")


@pytest.mark.asyncio
async def test_start_subscribers_calls_connect():
    """NATSClient.connect() is awaited during start_event_subscribers.

    GREEN phase: connect() is called once before subscribe().
    STUB phase: FAILS with NotImplementedError.
    """
    mock_nats = AsyncMock(spec=NATSClient)

    with patch(
        "tracker_service.subscribers.event_handlers.NATSClient",
        return_value=mock_nats,
    ):
        await start_event_subscribers("nats://localhost:4222")

    mock_nats.connect.assert_awaited_once()


@pytest.mark.asyncio
async def test_start_subscribers_subscribes_to_three_topics():
    """subscribe() is called with action-requests, action-results, system-events.

    GREEN phase: all three topics are passed in the topics list.
    STUB phase: FAILS with NotImplementedError.
    """
    mock_nats = AsyncMock(spec=NATSClient)

    with patch(
        "tracker_service.subscribers.event_handlers.NATSClient",
        return_value=mock_nats,
    ):
        await start_event_subscribers("nats://localhost:4222")

    mock_nats.subscribe.assert_awaited_once()
    call_kwargs = mock_nats.subscribe.call_args.kwargs
    topics = call_kwargs.get("topics") or mock_nats.subscribe.call_args.args[0]

    assert EventTopic.ACTION_REQUESTS.value in topics
    assert EventTopic.ACTION_RESULTS.value in topics
    assert EventTopic.SYSTEM_EVENTS.value in topics


@pytest.mark.asyncio
async def test_start_subscribers_sets_queue_group_tracker_service():
    """subscribe() uses queue_group='tracker-service' for load balancing.

    GREEN phase: queue_group parameter is 'tracker-service'.
    STUB phase: FAILS with NotImplementedError.
    """
    mock_nats = AsyncMock(spec=NATSClient)

    with patch(
        "tracker_service.subscribers.event_handlers.NATSClient",
        return_value=mock_nats,
    ):
        await start_event_subscribers("nats://localhost:4222")

    call_kwargs = mock_nats.subscribe.call_args.kwargs
    assert call_kwargs.get("queue_group") == "tracker-service"


@pytest.mark.asyncio
async def test_start_subscribers_stores_nats_client_in_global():
    """After start_event_subscribers, the global _nats_client is set.

    GREEN phase: eh._nats_client is the NATSClient instance.
    STUB phase: FAILS with NotImplementedError.
    """
    mock_nats = AsyncMock(spec=NATSClient)

    with patch(
        "tracker_service.subscribers.event_handlers.NATSClient",
        return_value=mock_nats,
    ):
        await start_event_subscribers("nats://localhost:4222")

    assert eh._nats_client is mock_nats


@pytest.mark.asyncio
async def test_stop_subscribers_calls_disconnect():
    """stop_event_subscribers calls disconnect() on the stored NATSClient.

    GREEN phase: disconnect() is awaited and _nats_client becomes None.
    STUB phase: start_event_subscribers raises NotImplementedError first.
    """
    mock_nats = AsyncMock(spec=NATSClient)

    with patch(
        "tracker_service.subscribers.event_handlers.NATSClient",
        return_value=mock_nats,
    ):
        await start_event_subscribers("nats://localhost:4222")

    await stop_event_subscribers()

    mock_nats.disconnect.assert_awaited_once()
    assert eh._nats_client is None


@pytest.mark.asyncio
async def test_stop_subscribers_noop_when_no_client():
    """stop_event_subscribers does not raise if _nats_client is None.

    This test passes in STUB phase because _nats_client is never set,
    and stop_event_subscribers explicitly checks for None.
    """
    eh._nats_client = None
    # Must complete without exception
    await stop_event_subscribers()


# ---------------------------------------------------------------------------
# Dispatcher routing tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dispatcher_routes_action_requests_to_handler():
    """NATS dispatcher routes action-requests subject to handle_action_request.

    GREEN phase: the callback passed to subscribe() routes correctly.
    STUB phase: FAILS with NotImplementedError from start_event_subscribers.
    """
    mock_nats = AsyncMock(spec=NATSClient)
    captured_callback = None

    async def capture_subscribe(topics, callback, queue_group=None):
        nonlocal captured_callback
        captured_callback = callback
        return "sub-id-1"

    mock_nats.subscribe.side_effect = capture_subscribe

    event_payload = {
        "id": "e1",
        "source": "worker",
        "type": "task.requested",
        "topic": "action-requests",
        "data": {"action_id": "a1"},
        "tenant_id": "t1",
        "user_id": "u1",
    }

    with patch(
        "tracker_service.subscribers.event_handlers.NATSClient",
        return_value=mock_nats,
    ), patch(
        "tracker_service.subscribers.event_handlers.handle_action_request"
    ) as mock_handler, patch(
        "tracker_service.subscribers.event_handlers._create_db_handler",
        return_value=AsyncMock(),
    ) as mock_db_wrap:
        await start_event_subscribers("nats://localhost:4222")
        # Dispatch must happen INSIDE the with block so patches are still active
        assert captured_callback is not None
        await captured_callback("soorma.events.action-requests", event_payload)
        mock_db_wrap.assert_called_once_with(mock_handler)


@pytest.mark.asyncio
async def test_dispatcher_routes_action_results_to_handler():
    """NATS dispatcher routes action-results subject to handle_action_result.

    GREEN phase: dispatcher picks the correct handler.
    STUB phase: FAILS with NotImplementedError.
    """
    mock_nats = AsyncMock(spec=NATSClient)
    captured_callback = None

    async def capture_subscribe(topics, callback, queue_group=None):
        nonlocal captured_callback
        captured_callback = callback
        return "sub-id-2"

    mock_nats.subscribe.side_effect = capture_subscribe

    event_payload = {
        "id": "e2",
        "source": "worker",
        "type": "task.completed",
        "topic": "action-results",
        "data": {"action_id": "a2"},
        "tenant_id": "t1",
        "user_id": "u1",
    }

    with patch(
        "tracker_service.subscribers.event_handlers.NATSClient",
        return_value=mock_nats,
    ), patch(
        "tracker_service.subscribers.event_handlers.handle_action_result"
    ) as mock_handler, patch(
        "tracker_service.subscribers.event_handlers._create_db_handler",
        return_value=AsyncMock(),
    ) as mock_db_wrap:
        await start_event_subscribers("nats://localhost:4222")
        assert captured_callback is not None
        await captured_callback("soorma.events.action-results", event_payload)
        mock_db_wrap.assert_called_once_with(mock_handler)


@pytest.mark.asyncio
async def test_dispatcher_routes_system_events_to_handler():
    """NATS dispatcher routes system-events subject to handle_plan_event.

    GREEN phase: dispatcher picks the correct handler.
    STUB phase: FAILS with NotImplementedError.
    """
    mock_nats = AsyncMock(spec=NATSClient)
    captured_callback = None

    async def capture_subscribe(topics, callback, queue_group=None):
        nonlocal captured_callback
        captured_callback = callback
        return "sub-id-3"

    mock_nats.subscribe.side_effect = capture_subscribe

    event_payload = {
        "id": "e3",
        "source": "planner",
        "type": "plan.started",
        "topic": "system-events",
        "data": {"plan_id": "p1"},
        "tenant_id": "t1",
        "user_id": "u1",
    }

    with patch(
        "tracker_service.subscribers.event_handlers.NATSClient",
        return_value=mock_nats,
    ), patch(
        "tracker_service.subscribers.event_handlers.handle_plan_event"
    ) as mock_handler, patch(
        "tracker_service.subscribers.event_handlers._create_db_handler",
        return_value=AsyncMock(),
    ) as mock_db_wrap:
        await start_event_subscribers("nats://localhost:4222")
        assert captured_callback is not None
        await captured_callback("soorma.events.system-events", event_payload)
        mock_db_wrap.assert_called_once_with(mock_handler)


@pytest.mark.asyncio
async def test_dispatcher_ignores_unknown_subjects():
    """NATS dispatcher silently ignores messages on unrecognized subjects.

    GREEN phase: no handler is called for unknown topics.
    STUB phase: FAILS with NotImplementedError.
    """
    mock_nats = AsyncMock(spec=NATSClient)
    captured_callback = None

    async def capture_subscribe(topics, callback, queue_group=None):
        nonlocal captured_callback
        captured_callback = callback
        return "sub-id-4"

    mock_nats.subscribe.side_effect = capture_subscribe

    with patch(
        "tracker_service.subscribers.event_handlers.NATSClient",
        return_value=mock_nats,
    ), patch(
        "tracker_service.subscribers.event_handlers._create_db_handler"
    ) as mock_db_wrap:
        await start_event_subscribers("nats://localhost:4222")
        assert captured_callback is not None
        await captured_callback("soorma.events.unknown-topic", {"id": "e_unknown"})
        # No db handler should have been called
        mock_db_wrap.assert_not_called()
