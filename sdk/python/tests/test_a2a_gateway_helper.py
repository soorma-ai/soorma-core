"""Tests for A2AGatewayHelper (Task 3D).

RED phase: all tests call stub methods that raise NotImplementedError.
Tests assert REAL expected behaviour.

Run:
    pytest sdk/python/tests/test_a2a_gateway_helper.py -v
"""
import pytest

from soorma.gateway import A2AGatewayHelper
from soorma_common import AgentDefinition, AgentCapability, EventDefinition
from soorma_common.events import EventEnvelope, EventTopic
from soorma_common.a2a import (
    A2AAgentCard,
    A2AAuthType,
    A2AMessage,
    A2APart,
    A2ASkill,
    A2ATask,
    A2ATaskResponse,
    A2ATaskStatus,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_agent_definition(name: str = "ResearchWorker:1.0.0") -> AgentDefinition:
    """Minimal valid AgentDefinition with one capability."""
    return AgentDefinition(
        agent_id="research-worker-001",
        name=name,
        description="Performs research tasks",
        capabilities=[
            AgentCapability(
                task_name="research_task",
                description="Conduct research on a topic",
                consumed_event=EventDefinition(
                    event_name="research.requested",
                    topic="action-requests",
                    description="Trigger research",
                    payload_schema_name="research_request_v1",
                ),
                produced_events=[
                    EventDefinition(
                        event_name="research.completed",
                        topic="action-results",
                        description="Research result",
                    )
                ],
            )
        ],
    )


def _make_a2a_task(
    task_id: str = "task-001",
    text: str = "Research AI trends",
) -> A2ATask:
    """Minimal A2ATask with one text part."""
    return A2ATask(
        id=task_id,
        message=A2AMessage(
            role="user",
            parts=[A2APart(type="text", text=text)],
        ),
    )


def _make_event_envelope(data: dict | None = None) -> EventEnvelope:
    """Minimal EventEnvelope, optionally with data payload."""
    return EventEnvelope(
        source="research-worker",
        type="research.completed",
        topic=EventTopic.ACTION_RESULTS,
        data=data,
        correlation_id="corr-001",
    )


# ---------------------------------------------------------------------------
# agent_to_card() tests
# ---------------------------------------------------------------------------

def test_agent_to_card_name_and_description():
    """agent_to_card() maps name and description from AgentDefinition."""
    agent = _make_agent_definition("ResearchWorker:1.0.0")

    card = A2AGatewayHelper.agent_to_card(
        agent=agent,
        gateway_url="https://gateway.example.com/a2a",
    )

    assert isinstance(card, A2AAgentCard)
    assert card.name == "ResearchWorker"
    assert card.description == "Performs research tasks"


def test_agent_to_card_sets_gateway_url():
    """agent_to_card() sets the url field from the gateway_url argument."""
    agent = _make_agent_definition()

    card = A2AGatewayHelper.agent_to_card(
        agent=agent,
        gateway_url="https://gateway.example.com/a2a/research",
    )

    assert card.url == "https://gateway.example.com/a2a/research"


def test_agent_to_card_capabilities_become_skills():
    """agent_to_card() converts each capability to an A2ASkill."""
    agent = _make_agent_definition()

    card = A2AGatewayHelper.agent_to_card(
        agent=agent,
        gateway_url="https://gateway.example.com/a2a",
    )

    assert len(card.skills) == 1
    assert isinstance(card.skills[0], A2ASkill)
    assert card.skills[0].name == "research_task"


def test_agent_to_card_skill_maps_schema_name():
    """Skill inputSchema reference matches the consumed event's payload_schema_name."""
    agent = _make_agent_definition()

    card = A2AGatewayHelper.agent_to_card(
        agent=agent,
        gateway_url="https://gateway.example.com/a2a",
    )

    skill = card.skills[0]
    # The schema name should be referenced in the skill
    assert skill.inputSchema is not None
    assert "research_request_v1" in str(skill.inputSchema)


def test_agent_to_card_parses_version_from_name():
    """agent_to_card() extracts version from 'Name:version' agent name format."""
    agent = _make_agent_definition("ResearchWorker:2.0.0")

    card = A2AGatewayHelper.agent_to_card(
        agent=agent,
        gateway_url="https://gateway.example.com/a2a",
    )

    assert card.version == "2.0.0"
    assert card.name == "ResearchWorker"


# ---------------------------------------------------------------------------
# task_to_event() tests
# ---------------------------------------------------------------------------

def test_task_to_event_sets_event_type():
    """task_to_event() sets the correct event type in the envelope."""
    task = _make_a2a_task()

    envelope = A2AGatewayHelper.task_to_event(
        task=task,
        event_type="research.requested",
    )

    assert isinstance(envelope, EventEnvelope)
    assert envelope.type == "research.requested"


def test_task_to_event_uses_task_id_as_correlation():
    """task_to_event() uses task.id as the correlation_id."""
    task = _make_a2a_task(task_id="task-xyz-123")

    envelope = A2AGatewayHelper.task_to_event(
        task=task,
        event_type="research.requested",
    )

    assert envelope.correlation_id == "task-xyz-123"


def test_task_to_event_text_part_in_data():
    """task_to_event() places the first text part in data['input']."""
    task = _make_a2a_task(text="Research AI trends in 2026")

    envelope = A2AGatewayHelper.task_to_event(
        task=task,
        event_type="research.requested",
    )

    assert envelope.data is not None
    assert envelope.data["input"] == "Research AI trends in 2026"


# ---------------------------------------------------------------------------
# event_to_response() tests
# ---------------------------------------------------------------------------

def test_event_to_response_completed_when_data_present():
    """event_to_response() returns COMPLETED status when event has data."""
    event = _make_event_envelope(data={"summary": "AI is growing fast"})

    response = A2AGatewayHelper.event_to_response(
        event=event,
        task_id="task-001",
    )

    assert isinstance(response, A2ATaskResponse)
    assert response.status == A2ATaskStatus.COMPLETED
    assert response.id == "task-001"


def test_event_to_response_failed_when_empty():
    """event_to_response() returns FAILED status when event has no data."""
    event = _make_event_envelope(data=None)

    response = A2AGatewayHelper.event_to_response(
        event=event,
        task_id="task-002",
    )

    assert response.status == A2ATaskStatus.FAILED
    assert response.id == "task-002"
