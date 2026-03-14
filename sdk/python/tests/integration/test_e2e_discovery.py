"""T13 – End-to-end discovery integration tests.

These tests exercise the full register → discover → deregister lifecycle
against the real Registry service running in-process via SQLite.

All HTTP requests go through httpx.ASGITransport (no TCP socket, no docker).
"""

import pytest
from soorma_common.models import AgentDefinition, AgentCapability, EventDefinition, PayloadSchema

from tests.integration.conftest import make_registry_client


# ---------------------------------------------------------------------------
# Shared test fixtures
# ---------------------------------------------------------------------------


def _make_schema(name: str = "research_request", version: str = "1.0.0") -> PayloadSchema:
    """Return a minimal PayloadSchema for testing."""
    return PayloadSchema(
        schema_name=f"{name}_{version.replace('.', '_')}",
        version=version,
        json_schema={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
        description=f"Test schema {name} v{version}",
    )


def _make_agent(
    agent_id: str = "test-research-worker",
    event_name: str = "research.requested",
) -> AgentDefinition:
    """Return a minimal AgentDefinition with one capability."""
    return AgentDefinition(
        agent_id=agent_id,
        name="TestResearchWorker",
        description="Test worker that handles research tasks",
        capabilities=[
            AgentCapability(
                task_name="web_research",
                description="Performs web research given a query",
                consumed_event=EventDefinition(
                    event_name=event_name,
                    topic="action-requests",
                    description="Research request event",
                ),
                produced_events=[
                    EventDefinition(
                        event_name="research.completed",
                        topic="action-results",
                        description="Research result event",
                    )
                ],
            )
        ],
    )


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestE2EDiscovery:
    """End-to-end tests for the register → discover → deregister lifecycle."""

    @pytest.mark.asyncio
    async def test_register_schema_and_retrieve(self) -> None:
        """Registered schema is returned by the registry query."""
        client = make_registry_client()
        schema = _make_schema(name="research_request", version="1.0.0")

        response = await client.register_schema(schema)

        assert response is not None
        assert response.schema_name == schema.schema_name
        assert response.version == schema.version

    @pytest.mark.asyncio
    async def test_register_agent_and_discover_by_capability(self) -> None:
        """Registered agent is returned when discovering by consumed event name."""
        client = make_registry_client()
        agent = _make_agent(event_name="discovery.smoke_test")

        reg_response = await client.register_agent(agent)
        assert reg_response is not None

        # discover() filters by capability task_name, not raw event name
        discovered = await client.discover(requirements=["web_research"])

        assert len(discovered) == 1
        assert discovered[0].agent_id == agent.agent_id
        # DiscoveredAgent.name strips the ":version" suffix that the registry appends
        assert discovered[0].name == "TestResearchWorker"

    @pytest.mark.asyncio
    async def test_schema_versioning_coexistence(self) -> None:
        """Registering v1 and v2 of the same schema name creates two distinct entries."""
        client = make_registry_client()

        schema_v1 = _make_schema(name="versioned_schema", version="1.0.0")
        schema_v2 = _make_schema(name="versioned_schema", version="2.0.0")

        resp_v1 = await client.register_schema(schema_v1)
        resp_v2 = await client.register_schema(schema_v2)

        assert resp_v1.schema_name == "versioned_schema_1_0_0"
        assert resp_v2.schema_name == "versioned_schema_2_0_0"
        # Both versions are persisted independently
        assert resp_v1.version != resp_v2.version

    @pytest.mark.asyncio
    async def test_deregister_removes_agent_from_discover(self) -> None:
        """Deregistered agent no longer appears in discover results."""
        client = make_registry_client()
        agent = _make_agent(agent_id="temp-worker", event_name="deregister.test_event")

        await client.register_agent(agent)

        # Verify agent is discoverable before deregistration
        # discover() filters by capability task_name
        before = await client.discover(requirements=["web_research"])
        assert len(before) == 1

        deregistered = await client.deregister_agent(agent.agent_id)
        assert deregistered is True

        # Agent should no longer appear in discover
        after = await client.discover(requirements=["web_research"])
        assert len(after) == 0

    @pytest.mark.asyncio
    async def test_discover_returns_empty_for_unknown_capability(self) -> None:
        """Discovering an event that no agent is registered for returns an empty list."""
        client = make_registry_client()

        # 'completely_unknown_task' doesn't match any registered task_name
        discovered = await client.discover(requirements=["completely_unknown_task"])

        assert discovered == []
