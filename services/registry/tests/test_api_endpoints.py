"""
Integration tests for API endpoints.
These tests verify the actual API routes and responses.
"""
import pytest
from fastapi.testclient import TestClient
from registry_service.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


class TestHealthEndpoints:
    """Tests for health and root endpoints."""
    
    def test_root_endpoint(self, client):
        """Test the root endpoint returns service info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "version" in data
        assert "status" in data
        assert data["service"] == "registry-service"
        assert data["status"] == "operational"
    
    def test_health_check(self, client):
        """Test the health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestEventEndpoints:
    """Tests for event registry endpoints."""
    
    def test_register_event_endpoint(self, client):
        """Test POST /v1/events endpoint exists and works."""
        event_data = {
            "event": {
                "eventName": "test.event",
                "topic": "action-requests",
                "description": "Test event",
                "payloadSchema": {"type": "object"},
                "responseSchema": None
            }
        }
        
        response = client.post("/v1/events", json=event_data)
        assert response.status_code == 200
        data = response.json()
        print(f"Response data: {data}")  # Debug output
        assert data["success"] is True, f"Expected success=True, got: {data}"
        assert data["eventName"] == "test.event"
    
    def test_get_all_events_endpoint(self, client):
        """Test GET /v1/events endpoint exists."""
        response = client.get("/v1/events")
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert "count" in data
        assert isinstance(data["events"], list)
        assert isinstance(data["count"], int)
    
    def test_query_events_by_topic(self, client):
        """Test GET /v1/events?topic=... endpoint works."""
        # First register an event
        event_data = {
            "event": {
                "eventName": "topic.test.event",
                "topic": "business-facts",
                "description": "Test event for topic query",
                "payloadSchema": {"type": "object"}
            }
        }
        client.post("/v1/events", json=event_data)
        
        # Then query by topic
        response = client.get("/v1/events", params={"topic": "business-facts"})
        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 1
        # Verify at least one event has the correct topic
        topics = [event["topic"] for event in data["events"]]
        assert "business-facts" in topics
    
    def test_query_event_by_name(self, client):
        """Test GET /v1/events?event_name=... endpoint works."""
        # First register an event
        event_data = {
            "event": {
                "eventName": "specific.query.event",
                "topic": "action-requests",
                "description": "Test event for name query",
                "payloadSchema": {"type": "object"}
            }
        }
        client.post("/v1/events", json=event_data)
        
        # Then query by name
        response = client.get("/v1/events", params={"event_name": "specific.query.event"})
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["events"][0]["eventName"] == "specific.query.event"
    
    def test_api_path_is_correct(self, client):
        """Test that /v1/events is the correct path."""
        response = client.get("/v1/events")
        assert response.status_code == 200
        
        # Verify incorrect paths return 404
        response_wrong = client.get("/api/v1/events")
        assert response_wrong.status_code == 404


class TestAgentEndpoints:
    """Tests for agent registry endpoints."""
    
    def test_register_agent_endpoint(self, client):
        """Test POST /v1/agents endpoint exists and works with SDK format."""
        agent_data = {
            "agent_id": "test-agent-v1",
            "name": "Test Agent",
            "agent_type": "worker",
            "capabilities": ["test_task"],
            "events_consumed": ["test.event"],
            "events_produced": ["test.response"],
            "metadata": {"description": "Test agent"}
        }
        
        response = client.post("/v1/agents", json=agent_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["agentId"] == "test-agent-v1"
    
    def test_delete_agent_endpoint(self, client):
        """Test DELETE /v1/agents/{agent_id} endpoint."""
        # Register first
        agent_data = {
            "agent_id": "delete-test-agent",
            "name": "Delete Test Agent",
            "agent_type": "worker",
            "capabilities": ["test_task"],
            "events_consumed": [],
            "events_produced": [],
            "metadata": {}
        }
        client.post("/v1/agents", json=agent_data)
        
        # Delete
        response = client.delete("/v1/agents/delete-test-agent")
        assert response.status_code == 204
        
        # Verify gone
        response = client.get("/v1/agents", params={"agentId": "delete-test-agent"})
        data = response.json()
        assert data["count"] == 0

    def test_heartbeat_post_endpoint(self, client):
        """Test POST /v1/agents/{agent_id}/heartbeat endpoint."""
        # Register first
        agent_data = {
            "agent_id": "heartbeat-test-agent",
            "name": "Heartbeat Test Agent",
            "agent_type": "worker",
            "capabilities": [],
            "events_consumed": [],
            "events_produced": [],
            "metadata": {}
        }
        client.post("/v1/agents", json=agent_data)
        
        # Heartbeat via POST
        response = client.post("/v1/agents/heartbeat-test-agent/heartbeat")
        assert response.status_code == 200
        assert response.json()["success"] is True
    
    def test_get_all_agents_endpoint(self, client):
        """Test GET /v1/agents endpoint exists."""
        response = client.get("/v1/agents")
        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert "count" in data
        assert isinstance(data["agents"], list)
        assert isinstance(data["count"], int)
    
    def test_query_agents_by_agent_id(self, client):
        """Test GET /v1/agents?agent_id=... endpoint works."""
        # First register an agent
        agent_data = {
            "agent_id": "query-test-agent-v1",
            "name": "Query Test Agent",
            "agent_type": "worker",
            "capabilities": ["query_test"],
            "events_consumed": ["query.test.event"],
            "events_produced": ["query.test.response"],
            "metadata": {"description": "Test agent for queries"}
        }
        client.post("/v1/agents", json=agent_data)
        
        # Then query by agent_id
        response = client.get("/v1/agents", params={"agent_id": "query-test-agent-v1"})
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["agents"][0]["agentId"] == "query-test-agent-v1"
    
    def test_query_agents_by_consumed_event(self, client):
        """Test GET /v1/agents?consumed_event=... endpoint works."""
        # First register an agent
        agent_data = {
            "agent_id": "consumer-test-agent-v1",
            "name": "Consumer Test Agent",
            "agent_type": "worker",
            "capabilities": ["consume"],
            "events_consumed": ["unique.consumed.event"],
            "events_produced": ["result.event"],
            "metadata": {"description": "Test agent that consumes events"}
        }
        client.post("/v1/agents", json=agent_data)
        
        # Then query by consumed event
        response = client.get("/v1/agents", params={"consumed_event": "unique.consumed.event"})
        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 1
        # Verify at least one agent consumes the event
        for agent in data["agents"]:
            if agent["agentId"] == "consumer-test-agent-v1":
                assert "unique.consumed.event" in agent["consumedEvents"]
                break
        else:
            pytest.fail("Agent not found in results")
    
    def test_query_agents_by_produced_event(self, client):
        """Test GET /v1/agents?produced_event=... endpoint works."""
        # First register an agent
        agent_data = {
            "agent_id": "producer-test-agent-v1",
            "name": "Producer Test Agent",
            "agent_type": "worker",
            "capabilities": ["produce"],
            "events_consumed": ["input.event"],
            "events_produced": ["unique.produced.event"],
            "metadata": {"description": "Test agent that produces events"}
        }
        client.post("/v1/agents", json=agent_data)
        
        # Then query by produced event
        response = client.get("/v1/agents", params={"produced_event": "unique.produced.event"})
        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 1
        # Verify at least one agent produces the event
        for agent in data["agents"]:
            if agent["agentId"] == "producer-test-agent-v1":
                assert "unique.produced.event" in agent["producedEvents"]
                break
        else:
            pytest.fail("Agent not found in results")
    
    def test_api_path_is_correct(self, client):
        """Test that /v1/agents is the correct path."""
        response = client.get("/v1/agents")
        assert response.status_code == 200
        
        # Verify incorrect paths return 404
        response_wrong = client.get("/api/v1/agents")
        assert response_wrong.status_code == 404
