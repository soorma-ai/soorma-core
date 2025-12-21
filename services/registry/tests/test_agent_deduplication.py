import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import time

def test_agent_deduplication_by_name(client: TestClient):
    """
    Test that multiple agents with the same name are deduplicated in the query results.
    Only the most recently active instance should be returned.
    """
    # 1. Register first instance of planner-agent
    planner1 = {
        "agent": {
            "agentId": "planner-1",
            "name": "planner-agent",
            "description": "Planner Instance 1",
            "capabilities": [
                {
                    "taskName": "planning",
                    "description": "Planning capability",
                    "consumedEvent": "goal.created",
                    "producedEvents": ["task.created"]
                }
            ],
            "consumedEvents": ["goal.created"],
            "producedEvents": ["task.created"]
        }
    }
    response = client.post("/v1/agents", json=planner1)
    assert response.status_code == 200

    # 2. Register second instance of planner-agent
    # We add a small delay to ensure timestamps might differ if the DB has high precision,
    # though the logic relies on last_heartbeat which is set on registration.
    planner2 = {
        "agent": {
            "agentId": "planner-2",
            "name": "planner-agent",
            "description": "Planner Instance 2",
            "capabilities": [
                {
                    "taskName": "planning",
                    "description": "Planning capability",
                    "consumedEvent": "goal.created",
                    "producedEvents": ["task.created"]
                }
            ],
            "consumedEvents": ["goal.created"],
            "producedEvents": ["task.created"]
        }
    }
    response = client.post("/v1/agents", json=planner2)
    assert response.status_code == 200

    # 3. Register a different agent type
    worker1 = {
        "agent": {
            "agentId": "worker-1",
            "name": "worker-agent",
            "description": "Worker Instance 1",
            "capabilities": [
                {
                    "taskName": "execution",
                    "description": "Execution capability",
                    "consumedEvent": "task.created",
                    "producedEvents": ["task.completed"]
                }
            ],
            "consumedEvents": ["task.created"],
            "producedEvents": ["task.completed"]
        }
    }
    response = client.post("/v1/agents", json=worker1)
    assert response.status_code == 200

    # 4. Query all agents
    response = client.get("/v1/agents")
    assert response.status_code == 200
    data = response.json()
    
    # Should have 2 agents total (1 planner, 1 worker)
    assert len(data["agents"]) == 2
    
    names = [a["name"] for a in data["agents"]]
    assert "planner-agent" in names
    assert "worker-agent" in names
    
    # Verify we got the latest planner (planner-2 was registered last)
    # Note: In a real concurrent scenario, we'd rely on heartbeat updates.
    # Since we just registered them sequentially, planner-2 should have a slightly later or equal timestamp.
    # The deduplication logic keeps the one with > heartbeat. If equal, it keeps the first one encountered in the list.
    # The list order from DB is usually insertion order or ID order.
    
    # Let's explicitly update heartbeat of planner-1 to make it the "latest"
    # Wait a second to ensure clock tick
    time.sleep(1.1) 
    response = client.post("/v1/agents/planner-1/heartbeat")
    assert response.status_code == 200
    
    # Query again
    response = client.get("/v1/agents")
    data = response.json()
    assert len(data["agents"]) == 2
    
    # Find the planner agent in the response
    planner_entry = next(a for a in data["agents"] if a["name"] == "planner-agent")
    assert planner_entry["agentId"] == "planner-1"

    # Now update planner-2
    time.sleep(1.1)
    response = client.post("/v1/agents/planner-2/heartbeat")
    assert response.status_code == 200
    
    # Query again
    response = client.get("/v1/agents")
    data = response.json()
    
    planner_entry = next(a for a in data["agents"] if a["name"] == "planner-agent")
    assert planner_entry["agentId"] == "planner-2"
