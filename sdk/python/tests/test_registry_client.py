"""
Tests for the RegistryClient and its dynamic capability handling.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from soorma.context import RegistryClient
from soorma_common import AgentCapability

@pytest.mark.asyncio
async def test_register_with_string_capabilities():
    """
    Test registering an agent with simple string capabilities (Legacy/Simple Mode).
    Verifies that strings are auto-converted to structured capabilities.
    """
    # Mock the HTTP client
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_client.post.return_value = mock_response

    registry = RegistryClient(base_url="http://test-registry")
    registry._http_client = mock_client

    # Register with string capabilities
    success = await registry.register(
        agent_id="test-agent-1",
        name="Test Agent",
        agent_type="worker",
        capabilities=["simple_task", "another_task"],
        events_consumed=["event.a"],
        events_produced=["event.b"],
        metadata={"description": "Simple agent"}
    )

    assert success is True

    # Verify the payload sent to the server
    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    url = call_args[0][0]
    kwargs = call_args[1]
    payload = kwargs["json"]

    assert url == "http://test-registry/v1/agents"
    
    # Check the structure
    assert "agent" in payload
    agent_def = payload["agent"]
    
    assert agent_def["agentId"] == "test-agent-1"
    assert agent_def["name"] == "Test Agent"
    
    # Verify capabilities were converted
    assert len(agent_def["capabilities"]) == 2
    
    cap1 = agent_def["capabilities"][0]
    assert cap1["taskName"] == "simple_task"
    assert cap1["description"] == "Capability: simple_task"
    assert cap1["consumedEvent"] == "unknown"
    
    cap2 = agent_def["capabilities"][1]
    assert cap2["taskName"] == "another_task"


@pytest.mark.asyncio
async def test_register_with_structured_capabilities():
    """
    Test registering an agent with full structured capabilities (Advanced Mode).
    Verifies that structured objects are passed through correctly.
    """
    # Mock the HTTP client
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_client.post.return_value = mock_response

    registry = RegistryClient(base_url="http://test-registry")
    registry._http_client = mock_client

    # Create structured capabilities using Pydantic model
    cap1 = AgentCapability(
        task_name="complex_task",
        description="A complex task",
        consumed_event="trigger.event",
        produced_events=["result.event"]
    )
    
    # Create structured capability as dict
    cap2 = {
        "taskName": "dict_task",
        "description": "Task defined as dict",
        "consumedEvent": "trigger.dict",
        "producedEvents": ["result.dict"]
    }

    # Register with mixed structured capabilities
    success = await registry.register(
        agent_id="test-agent-2",
        name="Advanced Agent",
        agent_type="planner",
        capabilities=[cap1, cap2],
        events_consumed=["trigger.event", "trigger.dict"],
        events_produced=["result.event", "result.dict"],
    )

    assert success is True

    # Verify the payload
    mock_client.post.assert_called_once()
    payload = mock_client.post.call_args[1]["json"]
    agent_def = payload["agent"]
    
    assert len(agent_def["capabilities"]) == 2
    
    # Check first capability (from Pydantic)
    # Note: Pydantic serialization should use camelCase aliases
    res_cap1 = agent_def["capabilities"][0]
    assert res_cap1["taskName"] == "complex_task"
    assert res_cap1["consumedEvent"] == "trigger.event"
    
    # Check second capability (from dict)
    res_cap2 = agent_def["capabilities"][1]
    assert res_cap2["taskName"] == "dict_task"
    assert res_cap2["consumedEvent"] == "trigger.dict"


@pytest.mark.asyncio
async def test_register_mixed_capabilities():
    """
    Test registering with a mix of strings and structured objects.
    """
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_client.post.return_value = mock_response

    registry = RegistryClient(base_url="http://test-registry")
    registry._http_client = mock_client

    success = await registry.register(
        agent_id="mixed-agent",
        name="Mixed Agent",
        agent_type="worker",
        capabilities=[
            "simple_string_task",
            {
                "taskName": "structured_task",
                "description": "Detailed description",
                "consumedEvent": "specific.event",
                "producedEvents": []
            }
        ],
        events_consumed=[],
        events_produced=[]
    )

    assert success is True
    
    payload = mock_client.post.call_args[1]["json"]
    caps = payload["agent"]["capabilities"]
    
    assert len(caps) == 2
    assert caps[0]["taskName"] == "simple_string_task"
    assert caps[0]["consumedEvent"] == "unknown"  # Auto-filled
    
    assert caps[1]["taskName"] == "structured_task"
    assert caps[1]["consumedEvent"] == "specific.event"  # Preserved
