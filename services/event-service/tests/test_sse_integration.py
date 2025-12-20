import pytest
import asyncio
import json
import uvicorn
from httpx import AsyncClient
from src.main import app
from src.services.event_manager import event_manager

@pytest.fixture
async def server():
    config = uvicorn.Config(app, host="127.0.0.1", port=8001, log_level="debug")
    server = uvicorn.Server(config)
    task = asyncio.create_task(server.serve())
    # Wait for server to start
    while not server.started:
        await asyncio.sleep(0.1)
    yield
    server.should_exit = True
    await task

@pytest.mark.asyncio
async def test_sse_stream_integration(server):
    """
    Test that an SSE stream receives published events.
    """
    agent_id = "test-subscriber"
    topics = "test.topic"
    
    # Ensure adapter is initialized
    if not event_manager.adapter or not event_manager.adapter.is_connected:
         await event_manager.initialize()

    # Background task to publish an event after a delay
    async def publish_delayed():
        await asyncio.sleep(2)
        await event_manager.publish("test.topic", {"foo": "bar"})

    asyncio.create_task(publish_delayed())

    # Start the stream request
    async with AsyncClient(base_url="http://127.0.0.1:8001") as client:
        async with client.stream("GET", f"/v1/events/stream?topics={topics}&agent_id={agent_id}") as response:
            assert response.status_code == 200
            
            lines = response.aiter_lines()
            
            found_connected = False
            found_message = False
            
            async for line in lines:
                if "event: connected" in line:
                    found_connected = True
                if "event: message" in line:
                    found_message = True
                    if found_connected:
                        break
            
            assert found_connected, "Did not receive connected event"
            assert found_message, "Did not receive message event"

