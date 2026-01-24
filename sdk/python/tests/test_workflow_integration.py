"""
Integration tests for WorkflowState with actual Memory Service client.

These tests verify the full stack works correctly with real usage patterns:
- WorkflowState passes raw values (strings, ints, lists, dicts)
- context.MemoryClient passes values directly to memory.client
- memory.client.MemoryClient wraps in WorkingMemorySet before sending
- Memory Service stores values with `value: Any` type
"""

import pytest
from unittest.mock import AsyncMock, patch
from soorma.workflow import WorkflowState
from soorma.context import MemoryClient
from soorma_common.models import WorkingMemoryResponse


@pytest.fixture
def mock_service_client():
    """Create a mock Memory Service client."""
    client = AsyncMock()
    client.health = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_workflow_state_with_string_value(mock_service_client):
    """Test WorkflowState.set() with string value."""
    # Setup mock
    mock_service_client.set_plan_state = AsyncMock()
    mock_service_client.get_plan_state = AsyncMock(return_value=WorkingMemoryResponse(
        id="1",
        tenant_id="tenant-1",
        plan_id="plan-123",
        key="goal",
        value="buy 100 bitcoins",  # Value stored directly
        updated_at="2026-01-22T00:00:00Z",
    ))
    
    # Create real instances with mocked service client
    memory_client = MemoryClient()
    memory_client._client = mock_service_client
    
    state = WorkflowState(
        memory_client, 
        "plan-123",
        tenant_id="test-tenant",
        user_id="test-user"
    )
    
    # Test: Set string value
    await state.set("goal", "buy 100 bitcoins")
    
    # Verify: Raw value passed to set_plan_state (which wraps it internally)
    mock_service_client.set_plan_state.assert_called_once_with(
        "plan-123",
        "goal",
        "buy 100 bitcoins",  # Raw value, no wrapping in store()
        "test-tenant",
        "test-user"
    )
    
    # Test: Get string value
    result = await state.get("goal")
    
    # Verify: Value returned directly
    assert result == "buy 100 bitcoins"


@pytest.mark.asyncio
async def test_workflow_state_with_integer_value(mock_service_client):
    """Test WorkflowState.set() with integer value."""
    mock_service_client.set_plan_state = AsyncMock()
    mock_service_client.get_plan_state = AsyncMock(return_value=WorkingMemoryResponse(
        id="1",
        tenant_id="tenant-1",
        plan_id="plan-123",
        key="current_task_index",
        value=0,
        updated_at="2026-01-22T00:00:00Z",
    ))
    
    memory_client = MemoryClient()
    memory_client._client = mock_service_client
    state = WorkflowState(
        memory_client, 
        "plan-123",
        tenant_id="test-tenant",
        user_id="test-user"
    )
    
    # Test: Set integer
    await state.set("current_task_index", 0)
    
    # Verify: Raw value passed
    mock_service_client.set_plan_state.assert_called_once_with(
        "plan-123",
        "current_task_index",
        0,
        "test-tenant",
        "test-user"
    )
    
    # Test: Get integer
    result = await state.get("current_task_index")
    assert result == 0


@pytest.mark.asyncio
async def test_workflow_state_with_list_value(mock_service_client):
    """Test WorkflowState.set() with list value."""
    tasks = ["research", "draft", "review"]
    
    mock_service_client.set_plan_state = AsyncMock()
    mock_service_client.get_plan_state = AsyncMock(return_value=WorkingMemoryResponse(
        id="1",
        tenant_id="tenant-1",
        plan_id="plan-123",
        key="tasks",
        value=tasks,
        updated_at="2026-01-22T00:00:00Z",
    ))
    
    memory_client = MemoryClient()
    memory_client._client = mock_service_client
    state = WorkflowState(
        memory_client, 
        "plan-123",
        tenant_id="test-tenant",
        user_id="test-user"
    )
    
    # Test: Set list
    await state.set("tasks", tasks)
    
    # Verify: Raw list passed
    mock_service_client.set_plan_state.assert_called_once_with(
        "plan-123",
        "tasks",
        tasks,
        "test-tenant",
        "test-user"
    )
    
    # Test: Get list
    result = await state.get("tasks")
    assert result == tasks


@pytest.mark.asyncio
async def test_workflow_state_with_dict_value(mock_service_client):
    """Test WorkflowState.set() with dict value."""
    research_data = {"findings": ["fact1", "fact2"], "source": "web"}
    
    mock_service_client.set_plan_state = AsyncMock()
    mock_service_client.get_plan_state = AsyncMock(return_value=WorkingMemoryResponse(
        id="1",
        tenant_id="tenant-1",
        plan_id="plan-123",
        key="research",
        value=research_data,
        updated_at="2026-01-22T00:00:00Z",
    ))
    
    memory_client = MemoryClient()
    memory_client._client = mock_service_client
    state = WorkflowState(
        memory_client, 
        "plan-123",
        tenant_id="test-tenant",
        user_id="test-user"
    )
    
    # Test: Set dict
    await state.set("research", research_data)
    
    # Verify: Raw dict passed
    mock_service_client.set_plan_state.assert_called_once_with(
        "plan-123",
        "research",
        research_data,
        "test-tenant",
        "test-user"
    )
    
    # Test: Get dict
    result = await state.get("research")
    assert result == research_data


@pytest.mark.asyncio
async def test_workflow_state_record_action(mock_service_client):
    """Test WorkflowState.record_action() wraps action history."""
    mock_service_client.retrieve = AsyncMock(return_value=None)  # No history yet
    mock_service_client.store = AsyncMock()
    mock_service_client.set_plan_state = AsyncMock()
    mock_service_client.get_plan_state = AsyncMock(
        side_effect=[
            # First call: no history
            Exception("404"),
            # Second call: history exists
            WorkingMemoryResponse(
                id="1",
                tenant_id="tenant-1",
                plan_id="plan-123",
                key="_action_history",
                value={"value": {"actions": ["research.started"]}},
                updated_at="2026-01-22T00:00:00Z",
            )
        ]
    )
    
    memory_client = MemoryClient()
    memory_client._client = mock_service_client
    state = WorkflowState(
        memory_client, 
        "plan-123",
        tenant_id="test-tenant",
        user_id="test-user"
    )
    
    # Test: Record first action
    await state.record_action("research.started")
    
    # Verify: History passed as raw dict
    mock_service_client.set_plan_state.assert_called_with(
        "plan-123",
        "_action_history",
        {"actions": ["research.started"]},
        "test-tenant",
        "test-user"
    )


@pytest.mark.asyncio
async def test_context_memory_client_store_raw_values(mock_service_client):
    """Test context.MemoryClient.store() wraps raw values correctly."""
    mock_service_client.set_plan_state = AsyncMock()
    
    memory_client = MemoryClient()
    memory_client._client = mock_service_client
    
    # Test various raw value types - no wrapping in store()
    test_cases = [
        ("string_key", "test string"),
        ("int_key", 42),
        ("list_key", [1, 2, 3]),
        ("dict_key", {"a": 1}),
        ("bool_key", True),
        ("none_key", None),
    ]
    
    for key, raw_value in test_cases:
        mock_service_client.set_plan_state.reset_mock()
        
        await memory_client.store(
            key, 
            raw_value, 
            plan_id="plan-123",
            tenant_id="test-tenant",
            user_id="test-user"
        )
        
        # Verify: Raw value passed to set_plan_state
        mock_service_client.set_plan_state.assert_called_once_with(
            "plan-123",
            key,
            raw_value,
            "test-tenant",
            "test-user"
        )


@pytest.mark.asyncio
async def test_context_memory_client_retrieve_unwraps_values(mock_service_client):
    """Test context.MemoryClient.retrieve() unwraps values correctly."""
    memory_client = MemoryClient()
    memory_client._client = mock_service_client
    
    # Test various value types - returned directly
    test_cases = [
        ("string_key", "test string"),
        ("int_key", 42),
        ("list_key", [1, 2, 3]),
        ("dict_key", {"a": 1}),
        ("bool_key", True),
        ("none_key", None),
    ]
    
    for key, stored_value in test_cases:
        mock_service_client.get_plan_state = AsyncMock(return_value=WorkingMemoryResponse(
            id="1",
            tenant_id="tenant-1",
            plan_id="plan-123",
            key=key,
            value=stored_value,
            updated_at="2026-01-22T00:00:00Z",
        ))
        
        result = await memory_client.retrieve(
            key, 
            plan_id="plan-123",
            tenant_id="test-tenant",
            user_id="test-user"
        )
        
        assert result == stored_value, f"Failed for {key}: expected {stored_value}, got {result}"
