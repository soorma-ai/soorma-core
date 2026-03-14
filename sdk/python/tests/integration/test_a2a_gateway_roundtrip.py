"""T15 – A2A Gateway round-trip integration tests.

Tests the gateway endpoint functions directly (without starting a TCP server
or connecting to NATS), focussing on:

  1. Agent Card aggregation — get_agent_card() composes all registered agents.
  2. No-agents 503 — get_agent_card() raises HTTPException when registry is empty.
  3. Task round-trip — send_task() publishes an event and returns an A2A response
     once the future is resolved by the mock EventClient.

The gateway module lives under examples/13-a2a-gateway/.  We add that path to
sys.path before importing so the tests stay self-contained.
"""

import asyncio
import sys
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from soorma_common.a2a import A2AMessage, A2APart, A2ATask
from soorma_common.events import EventEnvelope, EventTopic
from soorma_common.models import AgentDefinition, AgentCapability, EventDefinition

# ---------------------------------------------------------------------------
# Ensure examples/13-a2a-gateway is importable
# ---------------------------------------------------------------------------

_GATEWAY_DIR = str(
    Path(__file__).parents[4] / "examples" / "13-a2a-gateway"
)
if _GATEWAY_DIR not in sys.path:
    sys.path.insert(0, _GATEWAY_DIR)

import gateway_service  # noqa: E402 (path must be inserted first)

# ---------------------------------------------------------------------------
# Helper: minimal AgentDefinition for the mock registry
# ---------------------------------------------------------------------------


def _make_test_agent(
    agent_id: str = "research-worker",
    event_name: str = "research.requested",
) -> AgentDefinition:
    """Return a well-formed AgentDefinition for use in gateway tests."""
    return AgentDefinition(
        agent_id=agent_id,
        name="ResearchWorker",
        description="Worker that handles research tasks",
        capabilities=[
            AgentCapability(
                task_name="web_research",
                description="Performs web research for a given query",
                consumed_event=EventDefinition(
                    event_name=event_name,
                    topic="action-requests",
                    description="Research request",
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


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestA2AGatewayRoundtrip:
    """Integration tests for the A2A Gateway endpoint logic."""

    # ------------------------------------------------------------------
    # Agent Card tests
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_agent_card_aggregates_all_registered_agents(self) -> None:
        """get_agent_card() merges skills from all registry-registered agents.

        The gateway creates a fresh RegistryClient on each call, so we patch
        the RegistryClient class in the gateway module to intercept that
        instantiation and return our mock.
        """
        mock_registry = AsyncMock()
        mock_registry.query_agents.return_value = [_make_test_agent()]

        with patch.object(gateway_service, "RegistryClient", return_value=mock_registry):
            card: Dict[str, Any] = await gateway_service.get_agent_card()

        assert card["name"] == "Soorma A2A Gateway"
        assert len(card["skills"]) >= 1
        skill_ids = [s["id"] for s in card["skills"]]
        assert "web_research" in skill_ids

    @pytest.mark.asyncio
    async def test_agent_card_returns_503_when_no_agents(self) -> None:
        """get_agent_card() raises HTTPException 503 when no agents are registered."""
        mock_registry = AsyncMock()
        mock_registry.query_agents.return_value = []

        with patch.object(gateway_service, "RegistryClient", return_value=mock_registry):
            with pytest.raises(HTTPException) as exc_info:
                await gateway_service.get_agent_card()

        assert exc_info.value.status_code == 503

    # ------------------------------------------------------------------
    # Task round-trip test
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_a2a_task_roundtrip_via_mock_event_client(self) -> None:
        """send_task() publishes an event and returns a completed A2A response.

        The mock EventClient's publish() method resolves the asyncio.Future
        that send_task() creates, simulating an internal agent responding
        immediately.  This exercises the full request/response path without
        NATS or docker.
        """
        mock_ec = MagicMock()

        async def _resolve_pending_future(**kwargs: Any) -> None:
            """Side-effect: resolve the Future stored by send_task() for this correlation_id."""
            corr_id: str = kwargs.get("correlation_id", "")
            if corr_id and corr_id in gateway_service._pending_requests:
                future = gateway_service._pending_requests[corr_id]
                if not future.done():
                    future.set_result(
                        EventEnvelope(
                            source="mock-research-worker",
                            type="a2a.response",
                            topic=EventTopic.ACTION_RESULTS,
                            correlation_id=corr_id,
                            data={
                                "result": "Quantum computing is a paradigm that uses qubits.",
                                "sources": ["https://example.com/quantum"],
                            },
                        )
                    )

        mock_ec.publish = AsyncMock(side_effect=_resolve_pending_future)
        gateway_service._event_client = mock_ec

        try:
            task = A2ATask(
                id="task-qc-001",
                message=A2AMessage(
                    role="user",
                    parts=[A2APart(type="text", text="Research quantum computing")],
                ),
            )

            result: Dict[str, Any] = await gateway_service.send_task(task)

            # Verify the A2A response envelope
            assert result["id"] == "task-qc-001"
            assert result["status"] == "completed"
            # Message should carry the agent's data payload
            assert result["message"]["role"] == "agent"
            assert result["message"]["parts"][0]["type"] == "data"
            assert "result" in result["message"]["parts"][0]["data"]

        finally:
            # Always restore gateway state so other tests in the session are unaffected
            gateway_service._event_client = None

    @pytest.mark.asyncio
    async def test_a2a_task_returns_503_when_event_client_not_ready(self) -> None:
        """send_task() returns 503 immediately when EventClient is not connected."""
        # Ensure event client is None (gateway not started)
        original = gateway_service._event_client
        gateway_service._event_client = None

        try:
            task = A2ATask(
                id="task-no-ec",
                message=A2AMessage(
                    role="user",
                    parts=[A2APart(type="text", text="This should fail fast")],
                ),
            )
            with pytest.raises(HTTPException) as exc_info:
                await gateway_service.send_task(task)
            assert exc_info.value.status_code == 503
        finally:
            gateway_service._event_client = original
