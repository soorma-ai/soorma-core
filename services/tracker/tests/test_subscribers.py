"""Tests for Tracker Service event subscribers."""

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from soorma_common.events import EventEnvelope, EventTopic

from tracker_service.subscribers.event_handlers import (
    _extract_identity_dimensions,
    handle_action_request,
    handle_action_result,
    handle_plan_event,
    start_event_subscribers,
    stop_event_subscribers,
)


def _base_event(**overrides) -> EventEnvelope:
    payload = {
        "id": "event-1",
        "source": "test-worker",
        "type": "test.event",
        "topic": EventTopic.SYSTEM_EVENTS,
        "data": {},
        "platform_tenant_id": "spt_tenant-1",
        "tenant_id": "st_tenant-1",
        "user_id": "su_user-1",
    }
    payload.update(overrides)
    return EventEnvelope(**payload)


@pytest.mark.asyncio
class TestEventSubscriberLifecycle:
    async def test_start_subscribers_creates_nats_client_and_subscribes(self):
        mock_nats = AsyncMock()
        with patch(
            "tracker_service.subscribers.event_handlers.NATSClient",
            return_value=mock_nats,
        ) as mock_client:
            await start_event_subscribers("nats://localhost:4222")

        mock_client.assert_called_once_with(url="nats://localhost:4222")
        mock_nats.connect.assert_awaited_once()
        mock_nats.subscribe.assert_awaited_once()

    async def test_stop_subscribers_disconnects_nats_client(self):
        mock_nats = AsyncMock()
        with patch(
            "tracker_service.subscribers.event_handlers.NATSClient",
            return_value=mock_nats,
        ):
            await start_event_subscribers("nats://localhost:4222")
            await stop_event_subscribers()

        mock_nats.disconnect.assert_awaited_once()


@pytest.mark.asyncio
class TestHandlers:
    async def test_handle_action_request_executes_db_work(self):
        db_session = AsyncMock(spec=AsyncSession)
        event = _base_event(
            type="process.data.requested",
            topic=EventTopic.ACTION_REQUESTS,
            data={"action_id": "action-456", "action_name": "Process customer data"},
            plan_id="plan-789",
        )

        await handle_action_request(event, db_session)
        assert db_session.execute.called

    async def test_handle_action_request_skips_without_plan_id(self):
        db_session = AsyncMock(spec=AsyncSession)
        db_session.execute = AsyncMock()
        event = _base_event(
            type="analyze.feedback",
            topic=EventTopic.ACTION_REQUESTS,
            data={"action_id": "act-unplanned"},
            plan_id=None,
        )

        await handle_action_request(event, db_session)
        assert not db_session.execute.called

    async def test_handle_action_result_executes_db_work(self):
        db_session = AsyncMock(spec=AsyncSession)
        result_proxy = AsyncMock()
        result_proxy.rowcount = 1
        db_session.execute = AsyncMock(return_value=result_proxy)

        event = _base_event(
            type="process.data.completed",
            topic=EventTopic.ACTION_RESULTS,
            data={"action_id": "action-789", "plan_id": "plan-789"},
            plan_id="plan-789",
        )

        await handle_action_result(event, db_session)
        assert db_session.execute.called

    async def test_handle_plan_event_executes_db_work_for_plan_started(self):
        db_session = AsyncMock(spec=AsyncSession)
        event = _base_event(
            type="plan.started",
            topic=EventTopic.SYSTEM_EVENTS,
            data={"plan_id": "plan-new", "plan_name": "Research Project", "total_actions": 5},
        )

        await handle_plan_event(event, db_session)
        assert db_session.execute.called


class TestIdentityExtraction:
    def test_extract_identity_dimensions_from_envelope(self):
        event = _base_event(
            platform_tenant_id="spt_platform",
            tenant_id="st_service",
            user_id="su_user",
        )
        platform_tenant_id, service_tenant_id, service_user_id = _extract_identity_dimensions(event)
        assert platform_tenant_id == "spt_platform"
        assert service_tenant_id == "st_service"
        assert service_user_id == "su_user"

    def test_extract_identity_dimensions_fails_without_platform_tenant(self):
        event = _base_event(platform_tenant_id=None)
        with pytest.raises(ValueError, match="event.platform_tenant_id is required"):
            _extract_identity_dimensions(event)
