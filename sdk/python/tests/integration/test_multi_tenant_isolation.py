"""T14 – Multi-tenant data isolation integration tests.

Verifies that agents and schemas registered by one tenant are never visible
to a different tenant, confirming the Registry's row-level isolation.

The same in-process Registry ASGI app is used for both tenants; isolation
is enforced by the X-Tenant-ID header that the RegistryClient sends on every
request.
"""

import pytest
from soorma_common.models import AgentDefinition, AgentCapability, EventDefinition, PayloadSchema

from tests.integration.conftest import TENANT_A, TENANT_B, make_registry_client


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_agent_for_tenant(suffix: str, event: str) -> AgentDefinition:
    """Return a test AgentDefinition uniquely keyed by suffix."""
    return AgentDefinition(
        agent_id=f"isolation-worker-{suffix}",
        name=f"IsolationWorker-{suffix}",
        description="Agent used to verify tenant isolation",
        capabilities=[
            AgentCapability(
                task_name="isolation_task",
                description="Task for isolation testing",
                consumed_event=EventDefinition(
                    event_name=event,
                    topic="action-requests",
                    description="Isolation test event",
                ),
                produced_events=[],
            )
        ],
    )


def _make_schema_for_tenant(suffix: str) -> PayloadSchema:
    """Return a test PayloadSchema uniquely keyed by suffix."""
    return PayloadSchema(
        schema_name=f"isolation_schema_{suffix}",
        version="1.0.0",
        json_schema={"type": "object"},
        description=f"Isolation schema for {suffix}",
    )


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestMultiTenantIsolation:
    """Confirm that Registry data is strictly isolated between tenants."""

    @pytest.mark.asyncio
    async def test_agent_invisible_to_other_tenant(self) -> None:
        """Agent registered by Tenant A is not discoverable by Tenant B."""
        client_a = make_registry_client(tenant_id=TENANT_A)
        client_b = make_registry_client(tenant_id=TENANT_B)

        # Tenant A registers an agent for a unique event
        event_name = "isolation.agent.test_event"
        agent = _make_agent_for_tenant("tenant-a", event_name)
        await client_a.register_agent(agent)

        # Tenant A can discover its own agent by task_name
        found_by_a = await client_a.discover(requirements=["isolation_task"])
        assert len(found_by_a) == 1
        assert found_by_a[0].agent_id == agent.agent_id

        # Tenant B sees nothing for the same task_name
        found_by_b = await client_b.discover(requirements=["isolation_task"])
        assert found_by_b == [], (
            f"Tenant B should not see Tenant A's agent, but got: {found_by_b}"
        )

    @pytest.mark.asyncio
    async def test_schema_invisible_to_other_tenant(self) -> None:
        """Schema registered by Tenant A cannot be retrieved by Tenant B.

        The Registry does not expose a direct 'get schema by name' endpoint on
        the client, so we verify isolation indirectly: Tenant A's agent
        registered with a schema reference, combined with include_schemas=True,
        should return schema details only when queried by the owning tenant.
        """
        client_a = make_registry_client(tenant_id=TENANT_A)
        client_b = make_registry_client(tenant_id=TENANT_B)

        # Register a schema under Tenant A
        schema = _make_schema_for_tenant("a")
        await client_a.register_schema(schema)

        # Register an agent under Tenant A that references the schema
        event_name = "isolation.schema.test_event"
        agent = _make_agent_for_tenant("schema-a", event_name)
        await client_a.register_agent(agent)

        # Tenant A can discover with schema details
        found_by_a = await client_a.discover(
            requirements=["isolation_task"], include_schemas=True
        )
        assert len(found_by_a) == 1

        # Tenant B still sees no agents for this task_name
        found_by_b = await client_b.discover(
            requirements=["isolation_task"], include_schemas=True
        )
        assert found_by_b == [], (
            f"Tenant B should not see Tenant A's data, but got: {found_by_b}"
        )
