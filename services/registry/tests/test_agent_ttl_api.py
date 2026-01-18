"""
Integration tests for agent TTL and heartbeat API endpoints.
"""
import pytest
import time
from datetime import datetime, timezone, timedelta
from sqlalchemy import update, select

from registry_service.core.database import AsyncSessionLocal
from registry_service.crud import agents as agent_crud
from registry_service.models.agent import AgentTable
from soorma_common import AgentRegistrationRequest, AgentDefinition, AgentCapability


@pytest.fixture
def sample_agent_request():
    """Create a sample agent registration request (SDK format)."""
    return {
        "agent": {
            "agentId": "api-test-agent",
            "name": "API Test Agent",
            "description": "Agent for API testing",
            "capabilities": [
                {
                    "taskName": "api_task",
                    "description": "API Task",
                    "consumedEvent": "api.event",
                    "producedEvents": ["api.result"]
                }
            ],
            "consumedEvents": ["api.event"],
            "producedEvents": ["api.result"]
        }
    }


def test_register_agent_sets_heartbeat(client, sample_agent_request):
    """Test that registering an agent via API sets heartbeat."""
    # Register agent
    response = client.post(
        "/v1/agents",
        json=sample_agent_request
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    
    # Query the agent
    response = client.get(
        "/v1/agents",
        params={"agentId": "api-test-agent"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1


def test_heartbeat_endpoint(client, sample_agent_request):
    """Test the heartbeat refresh endpoint (PUT)."""
    # Register agent
    client.post(
        "/v1/agents",
        json=sample_agent_request
    )
    
    # Wait a tiny bit
    time.sleep(0.1)
    
    # Refresh heartbeat
    response = client.put("/v1/agents/api-test-agent/heartbeat")
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "refreshed successfully" in data["message"]


def test_heartbeat_post_endpoint(client, sample_agent_request):
    """Test the heartbeat refresh endpoint (POST)."""
    # Register agent
    client.post(
        "/v1/agents",
        json=sample_agent_request
    )
    
    # Refresh heartbeat via POST
    response = client.post("/v1/agents/api-test-agent/heartbeat")
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


def test_heartbeat_nonexistent_agent(client):
    """Test heartbeat endpoint with non-existent agent returns 404."""
    response = client.put("/v1/agents/nonexistent-agent/heartbeat")
    
    # After the auto-recovery fix, heartbeat failure should return 404
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "not found" in data["detail"].lower()


def test_query_with_include_expired_parameter(client, sample_agent_request):
    """Test querying agents with include_expired parameter."""
    # Register agent
    client.post(
        "/v1/agents",
        json=sample_agent_request
    )
    
    # Query with include_expired=false (default)
    response = client.get(
        "/v1/agents",
        params={"agentId": "api-test-agent", "includeExpired": False}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    
    # Query with include_expired=true
    response = client.get(
        "/v1/agents",
        params={"agentId": "api-test-agent", "includeExpired": True}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
def test_multiple_heartbeat_refreshes(client, sample_agent_request):
    """Test multiple heartbeat refreshes in sequence."""
    # Register agent
    client.post(
        "/v1/agents",
        json=sample_agent_request
    )
    
    # Refresh heartbeat multiple times
    for _ in range(3):
        time.sleep(0.05)
        response = client.put("/v1/agents/api-test-agent/heartbeat")
        assert response.status_code == 200
        assert response.json()["success"] is True
    
    # Agent should still be queryable
    response = client.get(
        "/v1/agents",
        params={"agentId": "api-test-agent"}
    )
    
    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_heartbeat_idempotency(client, sample_agent_request):
    """Test that heartbeat refresh is idempotent."""
    # Register agent
    client.post(
        "/v1/agents",
        json=sample_agent_request
    )
    
    # Refresh heartbeat twice with same result
    response1 = client.put("/v1/agents/api-test-agent/heartbeat")
    response2 = client.put("/v1/agents/api-test-agent/heartbeat")
    
    assert response1.status_code == 200
    assert response2.status_code == 200
    assert response1.json() == response2.json()


def test_heartbeat_idempotency(client, sample_agent_request):
    """Test that heartbeat refresh is idempotent."""
    # Register agent
    client.post(
        "/v1/agents",
        json=sample_agent_request
    )
    
    # Refresh heartbeat twice with same result
    response1 = client.put("/v1/agents/api-test-agent/heartbeat")
    response2 = client.put("/v1/agents/api-test-agent/heartbeat")
    
    assert response1.status_code == 200
    assert response2.status_code == 200
    assert response1.json() == response2.json()
    assert response2.json()["success"] is True
