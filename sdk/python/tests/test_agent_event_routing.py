"""Tests for Agent event routing behavior."""
from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict, List, Optional
from unittest.mock import MagicMock

import pytest

from soorma.agents.planner import Planner
from soorma_common.events import EventEnvelope, EventTopic
import soorma.agents.base as base_module
import soorma.agents.planner as planner_module


class FakeEventClient:
    """Fake EventClient for capturing handler registration and dispatch."""

    def __init__(
        self,
        event_service_url: str = "http://localhost:8082",
        agent_id: Optional[str] = None,
        source: Optional[str] = None,
        tenant_id: Optional[str] = None,
        session_id: Optional[str] = None,
        max_reconnect_attempts: int = -1,
        reconnect_base_delay: float = 1.0,
        reconnect_max_delay: float = 60.0,
    ) -> None:
        self.event_service_url = event_service_url
        self.agent_id = agent_id
        self.source = source
        self.tenant_id = tenant_id
        self.session_id = session_id
        self._handlers: Dict[str, List[Callable[[EventEnvelope], Awaitable[None]]]] = {}
        # Each entry is (handler, topic_filter) — topic_filter=None means all topics
        self._catch_all_handlers: List[tuple] = []

    def on_event(
        self,
        event_type: str,
        *,
        topic: Optional[EventTopic] = None,
    ) -> Callable[[Callable[[EventEnvelope], Awaitable[None]]], Callable[[EventEnvelope], Awaitable[None]]]:
        """Register a handler for a specific event type."""

        def decorator(func: Callable[[EventEnvelope], Awaitable[None]]) -> Callable[[EventEnvelope], Awaitable[None]]:
            if event_type == "*":
                # Wildcard: store with topic so dispatch can filter
                self._catch_all_handlers.append((func, topic))
            else:
                self._handlers.setdefault(event_type, []).append(func)
            return func

        return decorator

    def on_all_events(
        self,
        func: Callable[[EventEnvelope], Awaitable[None]],
    ) -> Callable[[EventEnvelope], Awaitable[None]]:
        """Register a catch-all handler (no topic filter)."""
        self._catch_all_handlers.append((func, None))
        return func

    async def dispatch(self, event: EventEnvelope) -> None:
        """Dispatch an event to registered handlers, respecting topic filters."""
        for handler in self._handlers.get(event.type, []):
            await handler(event)
        for handler, topic in self._catch_all_handlers:
            # Only fire if no topic restriction, or topics match
            if topic is None or event.topic == topic:
                await handler(event)


def _make_event(event_type: str, topic: EventTopic) -> EventEnvelope:
    """Create a basic EventEnvelope for tests."""
    return EventEnvelope(
        id="evt-123",
        source="tester",
        type=event_type,
        topic=topic,
        data={"ok": True},
        correlation_id="corr-123",
        tenant_id="tenant-1",
        user_id="user-1",
    )


@pytest.mark.asyncio
async def test_on_transition_wildcard_respects_topic(monkeypatch: pytest.MonkeyPatch) -> None:
    """Wildcard transition handler should receive only matching topics."""
    monkeypatch.setattr(base_module, "EventClient", FakeEventClient)

    async def mock_restore(*args: Any, **kwargs: Any) -> Any:
        plan = MagicMock()
        plan.get_next_state.return_value = "complete"
        plan.is_complete.return_value = False
        return plan

    monkeypatch.setattr(planner_module.PlanContext, "restore_by_correlation", mock_restore)

    planner = Planner(name="test-planner")
    received: List[EventEnvelope] = []

    @planner.on_transition()
    async def handle_transition(
        event: EventEnvelope,
        context: Any,
        plan: Any,
        next_state: str,
    ) -> None:
        received.append(event)

    await planner._initialize_context()
    client = planner.context.bus.event_client

    await client.dispatch(_make_event("research.complete", EventTopic.BUSINESS_FACTS))
    await client.dispatch(_make_event("research.complete", EventTopic.ACTION_RESULTS))

    assert len(received) == 1
    assert received[0].topic == EventTopic.ACTION_RESULTS


@pytest.mark.asyncio
async def test_on_transition_filters_by_transition_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Transition handler should only run for matching state transitions."""
    monkeypatch.setattr(base_module, "EventClient", FakeEventClient)

    plan = MagicMock()
    plan.is_complete.return_value = False

    def next_state_for_event(event: EventEnvelope) -> Optional[str]:
        if event.type == "research.complete":
            return "complete"
        return None

    plan.get_next_state.side_effect = next_state_for_event

    async def mock_restore(*args: Any, **kwargs: Any) -> Any:
        return plan

    monkeypatch.setattr(planner_module.PlanContext, "restore_by_correlation", mock_restore)

    planner = Planner(name="test-planner")
    received: List[str] = []

    @planner.on_transition()
    async def handle_transition(
        event: EventEnvelope,
        context: Any,
        restored_plan: Any,
        next_state: str,
    ) -> None:
        received.append(event.type)

    await planner._initialize_context()
    client = planner.context.bus.event_client

    await client.dispatch(_make_event("research.ignored", EventTopic.ACTION_RESULTS))
    await client.dispatch(_make_event("research.complete", EventTopic.ACTION_RESULTS))

    assert received == ["research.complete"]


@pytest.mark.asyncio
async def test_on_event_filters_by_topic(monkeypatch: pytest.MonkeyPatch) -> None:
    """Event handlers should respect the topic filter when provided."""
    monkeypatch.setattr(base_module, "EventClient", FakeEventClient)

    planner = Planner(name="test-planner")
    received: List[EventEnvelope] = []

    @planner.on_event("test.event", topic=EventTopic.ACTION_RESULTS)
    async def handle_event(event: EventEnvelope, context: Any) -> None:
        received.append(event)

    await planner._initialize_context()
    client = planner.context.bus.event_client

    await client.dispatch(_make_event("test.event", EventTopic.ACTION_REQUESTS))
    await client.dispatch(_make_event("test.event", EventTopic.ACTION_RESULTS))

    assert len(received) == 1
    assert received[0].topic == EventTopic.ACTION_RESULTS


@pytest.mark.asyncio
async def test_on_event_binds_identity_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    """Event dispatch should bind/reset identity metadata around handler execution."""
    monkeypatch.setattr(base_module, "EventClient", FakeEventClient)

    planner = Planner(name="identity-bind-planner")

    @planner.on_event("identity.test", topic=EventTopic.ACTION_RESULTS)
    async def handle_event(event: EventEnvelope, context: Any) -> None:
        return None

    await planner._initialize_context()
    planner.context.identity.bind_event_metadata = MagicMock(return_value="identity-token")
    planner.context.identity.reset_event_metadata = MagicMock()

    client = planner.context.bus.event_client
    await client.dispatch(_make_event("identity.test", EventTopic.ACTION_RESULTS))

    planner.context.identity.bind_event_metadata.assert_called_once()
    planner.context.identity.reset_event_metadata.assert_called_once_with("identity-token")
