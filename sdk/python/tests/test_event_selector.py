"""Tests for EventSelector (Task 3C, RF-SDK-017).

RED phase: all tests exercise real expected behaviour and fail with
NotImplementedError from the stub (not ImportError or AttributeError).

Run:
    pytest sdk/python/tests/test_event_selector.py -v
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

from soorma.ai.selection import EventSelector, EventSelectionError
from soorma_common.decisions import EventDecision
from soorma_common.events import EventTopic
from soorma_common import EventDefinition


# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

def _make_event_definition(name: str, topic: str = "action-requests") -> EventDefinition:
    """Minimal EventDefinition for test purposes."""
    return EventDefinition(
        event_name=name,
        topic=topic,
        description=f"Test event {name}",
        payload_schema={"type": "object", "properties": {"query": {"type": "string"}}},
    )


def _make_mock_context(events: list | None = None) -> MagicMock:
    """Build a mock PlatformContext with toolkit and bus attributes."""
    ctx = MagicMock()
    # context.toolkit.discover_events() returns a coroutine
    ctx.toolkit.discover_events = AsyncMock(return_value=events or [])
    # context.toolkit.format_for_llm() returns a list of dicts
    ctx.toolkit.format_for_llm = MagicMock(
        return_value=[{"name": e.event_name, "topic": e.topic} for e in (events or [])]
    )
    # context.bus.publish() returns a coroutine
    ctx.bus.publish = AsyncMock(return_value="event-id-001")
    return ctx


def _make_litellm_response(event_type: str, topic: str = "action-requests") -> MagicMock:
    """Build a mock LiteLLM completion response."""
    content = json.dumps({
        "event_type": event_type,
        "topic": topic,
        "payload": {"query": "test query"},
        "reasoning": "This event best matches the current state",
    })
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = content
    return response


# ---------------------------------------------------------------------------
# select_event() tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_select_event_returns_event_decision():
    """select_event() returns an EventDecision for valid LLM output."""
    events = [_make_event_definition("research.requested")]
    ctx = _make_mock_context(events)

    selector = EventSelector(context=ctx, topic=EventTopic.ACTION_REQUESTS)

    with patch("soorma.ai.selection.litellm") as mock_litellm:
        mock_litellm.acompletion = AsyncMock(
            return_value=_make_litellm_response("research.requested")
        )
        result = await selector.select_event(state={"goal": "research AI"})

    assert isinstance(result, EventDecision)
    assert result.event_type == "research.requested"
    assert result.topic == "action-requests"


@pytest.mark.asyncio
async def test_select_event_validates_event_exists_in_registry():
    """select_event() raises EventSelectionError if LLM picks an unlisted event."""
    events = [_make_event_definition("research.requested")]
    ctx = _make_mock_context(events)

    selector = EventSelector(context=ctx, topic=EventTopic.ACTION_REQUESTS)

    with patch("soorma.ai.selection.litellm") as mock_litellm:
        # LLM hallucinates an event not in our discovered list
        mock_litellm.acompletion = AsyncMock(
            return_value=_make_litellm_response("nonexistent.event")
        )
        with pytest.raises(EventSelectionError):
            await selector.select_event(state={"goal": "research AI"})


@pytest.mark.asyncio
async def test_select_event_uses_default_prompt_when_none_given():
    """When no custom prompt_template is given, the DEFAULT_SELECTOR_PROMPT is used."""
    from soorma.ai.selection import DEFAULT_SELECTOR_PROMPT

    events = [_make_event_definition("research.requested")]
    ctx = _make_mock_context(events)

    selector = EventSelector(context=ctx, topic=EventTopic.ACTION_REQUESTS)
    # Confirm the selector stores the default template
    assert selector.prompt_template == DEFAULT_SELECTOR_PROMPT


@pytest.mark.asyncio
async def test_select_event_uses_custom_prompt_template():
    """When custom prompt_template is provided it is stored on the selector."""
    custom = "State: {state_json}\nEvents: {events_json}\nRespond:"
    ctx = _make_mock_context([_make_event_definition("research.requested")])

    selector = EventSelector(
        context=ctx,
        topic=EventTopic.ACTION_REQUESTS,
        prompt_template=custom,
    )

    assert selector.prompt_template == custom


@pytest.mark.asyncio
async def test_select_event_llm_response_parsed_correctly():
    """LLM JSON response is correctly parsed into an EventDecision."""
    events = [_make_event_definition("search.requested")]
    ctx = _make_mock_context(events)

    selector = EventSelector(context=ctx, topic=EventTopic.ACTION_REQUESTS)

    with patch("soorma.ai.selection.litellm") as mock_litellm:
        mock_litellm.acompletion = AsyncMock(
            return_value=_make_litellm_response("search.requested")
        )
        result = await selector.select_event(state={"query": "AI trends"})

    assert result.event_type == "search.requested"
    assert result.payload == {"query": "test query"}
    assert "This event best matches" in result.reasoning


@pytest.mark.asyncio
async def test_select_event_llm_invalid_json_raises_error():
    """Malformed LLM output (non-JSON) raises EventSelectionError."""
    events = [_make_event_definition("research.requested")]
    ctx = _make_mock_context(events)

    selector = EventSelector(context=ctx, topic=EventTopic.ACTION_REQUESTS)

    broken_response = MagicMock()
    broken_response.choices = [MagicMock()]
    broken_response.choices[0].message.content = "I think the answer is research.requested but I forgot to format it"

    with patch("soorma.ai.selection.litellm") as mock_litellm:
        mock_litellm.acompletion = AsyncMock(return_value=broken_response)
        with pytest.raises(EventSelectionError):
            await selector.select_event(state={"goal": "research"})


@pytest.mark.asyncio
async def test_select_event_unknown_event_raises_error():
    """LLM references an event not in the discovered list — raises EventSelectionError."""
    events = [_make_event_definition("research.requested")]
    ctx = _make_mock_context(events)

    selector = EventSelector(context=ctx, topic=EventTopic.ACTION_REQUESTS)

    with patch("soorma.ai.selection.litellm") as mock_litellm:
        mock_litellm.acompletion = AsyncMock(
            return_value=_make_litellm_response("hallucinated.event")
        )
        with pytest.raises(EventSelectionError):
            await selector.select_event(state={"goal": "research"})


# ---------------------------------------------------------------------------
# publish_decision() tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_publish_decision_calls_context_bus():
    """publish_decision() calls context.bus.publish with correct event fields."""
    ctx = _make_mock_context([_make_event_definition("research.requested")])
    selector = EventSelector(context=ctx, topic=EventTopic.ACTION_REQUESTS)

    decision = EventDecision(
        event_type="research.requested",
        topic="action-requests",
        payload={"query": "AI"},
        reasoning="Best match",
    )

    await selector.publish_decision(decision, correlation_id="corr-123")

    ctx.bus.publish.assert_called_once()
    call_kwargs = ctx.bus.publish.call_args[1]
    assert call_kwargs["event_type"] == "research.requested"
    assert call_kwargs["topic"] == "action-requests"
    assert call_kwargs["correlation_id"] == "corr-123"


@pytest.mark.asyncio
async def test_publish_decision_passes_response_event():
    """publish_decision() forwards response_event to context.bus.publish."""
    ctx = _make_mock_context([_make_event_definition("research.requested")])
    selector = EventSelector(context=ctx, topic=EventTopic.ACTION_REQUESTS)

    decision = EventDecision(
        event_type="research.requested",
        topic="action-requests",
        payload={},
        reasoning="reason",
    )

    await selector.publish_decision(
        decision,
        correlation_id="corr-456",
        response_event="research.completed",
    )

    call_kwargs = ctx.bus.publish.call_args[1]
    assert call_kwargs.get("response_event") == "research.completed"


# ---------------------------------------------------------------------------
# Architecture compliance tests
# ---------------------------------------------------------------------------

def test_selector_reuses_context_toolkit():
    """EventSelector stores context and uses context.toolkit — no new RegistryClient."""
    ctx = _make_mock_context([])

    selector = EventSelector(context=ctx, topic=EventTopic.ACTION_REQUESTS)

    # Verify context is stored and toolkit access goes through context
    assert selector.context is ctx
    # EventSelector must NOT create its own RegistryClient
    from soorma.registry.client import RegistryClient
    assert not isinstance(getattr(selector, "_registry_client", None), RegistryClient)
