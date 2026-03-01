"""
RED Phase tests for GET /v1/agents/discover endpoint.

These tests assert REAL expected behavior and currently FAIL because
AgentRegistryService.discover_agents() raises NotImplementedError (STUB phase).

Expected failures: 500 Internal Server Error (server-side NotImplementedError)
NOT ImportError / AttributeError — those would mean stubs were not created.
"""
import pytest
from uuid import UUID

TEST_TENANT_ID = UUID("00000000-0000-0000-0000-000000000000")


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _agent_payload(
    agent_id: str,
    consumed_event: str = "research.requested",
    produced_event: str = "research.completed",
    name: str | None = None,
) -> dict:
    """Build a valid POST /v1/agents body."""
    return {
        "agent": {
            "agentId": agent_id,
            "name": name or f"{agent_id} Agent",
            "description": f"Test agent {agent_id}",
            "capabilities": [
                {
                    "taskName": "main_task",
                    "description": "Main capability",
                    "consumedEvent": {
                        "eventName": consumed_event,
                        "topic": "action-requests",
                        "description": f"Triggers {agent_id}",
                    },
                    "producedEvents": [
                        {
                            "eventName": produced_event,
                            "topic": "action-results",
                            "description": f"Result from {agent_id}",
                        }
                    ],
                }
            ],
            "consumedEvents": [consumed_event],
            "producedEvents": [produced_event],
        }
    }


def _register_agent(client, agent_id: str, consumed_event: str = "research.requested") -> None:
    """Register an agent and assert success."""
    r = client.post("/v1/agents", json=_agent_payload(agent_id, consumed_event))
    assert r.status_code == 200, f"Agent registration failed: {r.text}"


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestDiscoverAgents:
    """Tests for GET /v1/agents/discover."""

    def test_discover_agents_by_consumed_event(self, client):
        """Agents that consume the given event are returned."""
        _register_agent(client, "research-worker-001", consumed_event="research.requested")
        _register_agent(client, "unrelated-worker-001", consumed_event="payment.requested")

        response = client.get("/v1/agents/discover?consumed_event=research.requested")
        assert response.status_code == 200
        data = response.json()
        agent_ids = {a["agentId"] for a in data["agents"]}
        assert "research-worker-001" in agent_ids
        assert "unrelated-worker-001" not in agent_ids

    def test_discover_agents_returns_count(self, client):
        """Response includes correct count field."""
        _register_agent(client, "count-worker-001", consumed_event="task.requested")
        _register_agent(client, "count-worker-002", consumed_event="task.requested")

        response = client.get("/v1/agents/discover?consumed_event=task.requested")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2

    def test_discover_agents_no_match_returns_empty(self, client):
        """No agents consume the event → empty agents list, count=0."""
        response = client.get("/v1/agents/discover?consumed_event=nobody.listens.to.this")
        assert response.status_code == 200
        data = response.json()
        assert data["agents"] == []
        assert data["count"] == 0

    def test_discover_agents_returns_full_capability_metadata(self, client):
        """Each returned agent includes capabilities with consumed_event metadata."""
        _register_agent(client, "meta-worker-001", consumed_event="meta.requested")

        response = client.get("/v1/agents/discover?consumed_event=meta.requested")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 1
        agent = next(a for a in data["agents"] if a["agentId"] == "meta-worker-001")
        # Full capability metadata must be present
        assert len(agent["capabilities"]) >= 1
        capability = agent["capabilities"][0]
        assert "taskName" in capability
        assert "consumedEvent" in capability
        assert "producedEvents" in capability

    def test_discover_agents_no_filter_returns_all_active(self, client):
        """Without consumed_event filter, all active agents are returned."""
        _register_agent(client, "all-worker-001", consumed_event="event.a")
        _register_agent(client, "all-worker-002", consumed_event="event.b")
        _register_agent(client, "all-worker-003", consumed_event="event.c")

        response = client.get("/v1/agents/discover")
        assert response.status_code == 200
        data = response.json()
        agent_ids = {a["agentId"] for a in data["agents"]}
        assert "all-worker-001" in agent_ids
        assert "all-worker-002" in agent_ids
        assert "all-worker-003" in agent_ids

    def test_discover_agents_requires_tenant_header(self):
        """GET /v1/agents/discover without X-Tenant-ID returns 422."""
        from fastapi.testclient import TestClient
        from registry_service.main import app
        no_auth_client = TestClient(app)
        response = no_auth_client.get("/v1/agents/discover")
        assert response.status_code == 422

    def test_discover_agents_multiple_consumers(self, client):
        """Multiple agents consuming the same event are all returned."""
        for i in range(3):
            _register_agent(client, f"multi-consumer-00{i}", consumed_event="shared.event")

        response = client.get("/v1/agents/discover?consumed_event=shared.event")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 3

    def test_discover_agents_cross_tenant_isolation(self):
        """Agent registered by Tenant A is not discoverable by Tenant B."""
        from fastapi.testclient import TestClient
        from registry_service.main import app

        tenant_a = UUID("11111111-1111-1111-1111-111111111111")
        tenant_b = UUID("22222222-2222-2222-2222-222222222222")
        client_a = TestClient(app, headers={"X-Tenant-ID": str(tenant_a)})
        client_b = TestClient(app, headers={"X-Tenant-ID": str(tenant_b)})

        # Register agent as Tenant A
        r = client_a.post(
            "/v1/agents",
            json=_agent_payload("private-worker-001", consumed_event="secret.event")
        )
        assert r.status_code == 200

        # Tenant B discovers — should NOT see Tenant A's agent
        response = client_b.get("/v1/agents/discover?consumed_event=secret.event")
        assert response.status_code == 200
        agent_ids = {a["agentId"] for a in response.json()["agents"]}
        assert "private-worker-001" not in agent_ids

    def test_discover_agents_response_schema_structure(self, client):
        """GET /v1/agents/discover matches AgentQueryResponse shape."""
        response = client.get("/v1/agents/discover")
        assert response.status_code == 200
        data = response.json()
        # Must have 'agents' list and 'count' int
        assert "agents" in data
        assert "count" in data
        assert isinstance(data["agents"], list)
        assert isinstance(data["count"], int)

    def test_discover_endpoint_is_separate_from_query(self, client):
        """GET /v1/agents/discover is a distinct endpoint from GET /v1/agents."""
        response = client.get("/v1/agents/discover")
        assert response.status_code == 200  # endpoint exists

        response2 = client.get("/v1/agents")
        assert response2.status_code == 200  # query also exists (not broken)
