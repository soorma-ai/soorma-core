"""A2AGatewayHelper — A2A protocol conversion helpers for Soorma agents.

Provides pure-static helpers to convert between Soorma DTOs and the
Google A2A (Agent-to-Agent) protocol:

  - ``agent_to_card`` — AgentDefinition  → A2AAgentCard
  - ``task_to_event``  — A2ATask         → EventEnvelope
  - ``event_to_response`` — EventEnvelope → A2ATaskResponse

These helpers have no runtime service dependencies — they perform only
in-memory DTO conversion, so no auth context or HTTP client is needed.

Reference: https://google.github.io/agent-to-agent/

Usage::

    card = A2AGatewayHelper.agent_to_card(
        agent=my_agent_def,
        gateway_url="https://gateway.example.com/a2a",
    )
    envelope = A2AGatewayHelper.task_to_event(
        task=incoming_task,
        event_type="research.requested",
    )
    response = A2AGatewayHelper.event_to_response(
        event=result_envelope,
        task_id=incoming_task.id,
    )
"""

from typing import Optional

from soorma_common import AgentDefinition
from soorma_common.events import EventEnvelope, EventTopic
from soorma_common.a2a import (
    A2AAgentCard,
    A2AAuthentication,
    A2AAuthType,
    A2AMessage,
    A2APart,
    A2ASkill,
    A2ATask,
    A2ATaskResponse,
    A2ATaskStatus,
)


class A2AGatewayHelper:
    """Static conversion helpers between Soorma and A2A protocol DTOs.

    All methods are ``@staticmethod`` — no constructor needed and no service
    calls are made.  This helper is safe to use from any async or sync context
    without setup.
    """

    @staticmethod
    def agent_to_card(
        agent: AgentDefinition,
        gateway_url: str,
        auth_type: A2AAuthType = A2AAuthType.NONE,
    ) -> A2AAgentCard:
        """Convert a Soorma AgentDefinition to an A2A Agent Card.

        Maps ``AgentDefinition.capabilities`` to A2A ``skills``. Parses
        the agent version from the ``name:version`` convention (e.g.
        ``"ResearchWorker:2.0.0"``). When no version suffix is present,
        defaults to ``"1.0.0"``.

        Args:
            agent: Soorma AgentDefinition to convert.
            gateway_url: Public URL where this agent can receive A2A tasks.
            auth_type: A2A authentication scheme (default: NONE).

        Returns:
            A2AAgentCard with skills derived from capabilities.
        """
        # Parse version from the Name:version convention (FDE-2)
        name_parts = agent.name.split(":")
        name = name_parts[0]
        version = name_parts[1] if len(name_parts) > 1 else "1.0.0"

        # Map each AgentCapability to an A2ASkill
        skills = []
        for capability in agent.capabilities:
            consumed = capability.consumed_event
            input_schema: dict | None = None
            # Reference the schema name if available (schema content fetched separately)
            if consumed.payload_schema_name is not None:
                input_schema = {"$ref": consumed.payload_schema_name}

            skill = A2ASkill(
                id=capability.task_name,
                name=capability.task_name,
                description=capability.description,
                tags=[],
                inputSchema=input_schema,
            )
            skills.append(skill)

        return A2AAgentCard(
            name=name,
            description=agent.description,
            url=gateway_url,
            version=version,
            skills=skills,
            authentication=A2AAuthentication(schemes=[auth_type]),
        )

    @staticmethod
    def task_to_event(
        task: A2ATask,
        event_type: str,
        topic: str = "action-requests",
        tenant_id: str = "00000000-0000-0000-0000-000000000000",
        user_id: str = "00000000-0000-0000-0000-000000000000",
    ) -> EventEnvelope:
        """Convert an A2A Task to a Soorma EventEnvelope.

        Extracts the first text part from ``task.message.parts`` as the
        event's ``data["input"]``.  Uses ``task.id`` as the
        ``correlation_id`` so responses can be traced back to the originating
        A2A task.

        Args:
            task: Incoming A2A task.
            event_type: Soorma event type to publish (e.g.
                        ``"research.requested"``).
            topic: Target event topic (default: ``"action-requests"``).
            tenant_id: Client tenant UUID (default: sentinel all-zeros UUID).
            user_id: End-user UUID (default: sentinel all-zeros UUID).

        Returns:
            EventEnvelope ready to publish via the Soorma event bus.
        """
        # Extract input text from the first text part of the A2A message
        input_text: str = ""
        for part in task.message.parts:
            if part.type == "text" and part.text is not None:
                input_text = part.text
                break

        # Use a string topic value for lookup; ActionRequestEvent uses EventTopic enum
        topic_enum = EventTopic(topic)

        return EventEnvelope(
            source="a2a-gateway",
            type=event_type,
            topic=topic_enum,
            data={"input": input_text},
            # Use task.id as correlation_id for response tracing
            correlation_id=task.id,
            tenant_id=tenant_id,
            user_id=user_id,
        )

    @staticmethod
    def event_to_response(
        event: EventEnvelope,
        task_id: str,
    ) -> A2ATaskResponse:
        """Convert a Soorma EventEnvelope to an A2A TaskResponse.

        Sets ``status`` to ``COMPLETED`` when the event carries a non-empty
        ``data`` payload, and ``FAILED`` otherwise.  The result data is
        serialised into the ``message`` field as a single ``data`` part so
        the A2A caller can inspect the actual output.

        Args:
            event: Soorma event envelope (typically a result event).
            task_id: ID of the originating A2A task.

        Returns:
            A2ATaskResponse with the appropriate status and message.
        """
        has_data = bool(event.data)
        status = A2ATaskStatus.COMPLETED if has_data else A2ATaskStatus.FAILED

        # Carry the result data back to the A2A caller via the message field.
        # Use a single "data" part so structured results are preserved as-is.
        message = None
        if has_data:
            message = A2AMessage(
                role="agent",
                parts=[A2APart(type="data", data=event.data)],
            )

        return A2ATaskResponse(
            id=task_id,
            status=status,
            message=message,
        )
