import pytest
import asyncio
import json
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from src.main import app
from src.services.event_manager import event_manager

# We need to import EventClient from the SDK
# Since SDK is in core/sdk/python, we might need to adjust python path or install it
# For this test, I'll mock the EventClient's network calls to hit our app directly

@pytest.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        if not event_manager.adapter or not event_manager.adapter.is_connected:
             await event_manager.initialize()
        yield ac

@pytest.mark.asyncio
async def test_hello_world_flow(async_client):
    """
    Simulate the Hello World flow:
    1. Client submits 'greeting.goal'
    2. Planner receives goal, creates plan, publishes 'action.request'
    3. Worker receives task, publishes 'action.result'
    4. Client receives result
    """
    
    # 1. Client submits goal
    goal_event = {
        "event": {
            "source": "hello-client",
            "type": "greeting.goal",
            "topic": "business-facts",
            "data": {"name": "TestUser"},
        }
    }
    
    # Publish goal
    response = await async_client.post("/v1/events/publish", json=goal_event)
    assert response.status_code == 200
    
    # In a real integration test, we would have the Planner running and listening.
    # Here, we can verify that the event was published to the adapter.
    # Since we are using MemoryAdapter, we can subscribe to verify receipt.
    
    received_events = []
    
    async def capture_event(topic, msg):
        received_events.append((topic, msg))
        
    # Subscribe to relevant topics
    await event_manager.adapter.subscribe(["business-facts", "action-requests", "action-results"], capture_event)
    
    # Publish again to capture it (since subscription happened after first publish)
    response = await async_client.post("/v1/events/publish", json=goal_event)
    assert response.status_code == 200
    
    # Verify Planner would receive it
    assert len(received_events) > 0
    topic, msg = received_events[-1]
    assert topic == "business-facts"
    assert msg["type"] == "greeting.goal"
    assert msg["data"]["name"] == "TestUser"
    
    # 2. Simulate Planner publishing action request
    task_event = {
        "event": {
            "source": "hello-planner",
            "type": "action.request",
            "topic": "action-requests",
            "data": {
                "task_name": "greet",
                "assigned_to": "hello-worker",
                "data": {"name": "TestUser"}
            }
        }
    }
    response = await async_client.post("/v1/events/publish", json=task_event)
    assert response.status_code == 200
    
    # Verify Worker would receive it
    topic, msg = received_events[-1]
    assert topic == "action-requests"
    assert msg["type"] == "action.request"
    
    # 3. Simulate Worker publishing result
    result_event = {
        "event": {
            "source": "hello-worker",
            "type": "action.result",
            "topic": "action-results",
            "data": {
                "result": {"greeting": "Hello, TestUser!"},
                "status": "completed"
            }
        }
    }
    response = await async_client.post("/v1/events/publish", json=result_event)
    assert response.status_code == 200
    
    # Verify Client would receive it
    topic, msg = received_events[-1]
    assert topic == "action-results"
    assert msg["data"]["result"]["greeting"] == "Hello, TestUser!"

