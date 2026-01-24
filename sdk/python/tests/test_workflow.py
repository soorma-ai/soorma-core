"""Tests for WorkflowState helper class."""

import pytest
from unittest.mock import AsyncMock
from soorma.workflow import WorkflowState


@pytest.fixture
def mock_memory_client():
    """Create a mock MemoryClient."""
    client = AsyncMock()
    return client


@pytest.fixture
def workflow_state(mock_memory_client):
    """Create a WorkflowState instance."""
    return WorkflowState(
        mock_memory_client, 
        "plan-123",
        tenant_id="test-tenant",
        user_id="test-user"
    )


@pytest.mark.asyncio
async def test_record_action_new_history(workflow_state, mock_memory_client):
    """Test recording action with new history."""
    # Mock retrieve to return None (key doesn't exist)
    mock_memory_client.retrieve.return_value = None
    
    await workflow_state.record_action("research.started")
    
    # Verify retrieve was called
    mock_memory_client.retrieve.assert_called_once_with(
        "_action_history",
        plan_id="plan-123",
        tenant_id="test-tenant",
        user_id="test-user",
    )
    
    # Verify store was called with correct data
    mock_memory_client.store.assert_called_once_with(
        "_action_history",
        {"actions": ["research.started"]},
        plan_id="plan-123",
        tenant_id="test-tenant",
        user_id="test-user",
    )


@pytest.mark.asyncio
async def test_record_action_existing_history(workflow_state, mock_memory_client):
    """Test recording action with existing history."""
    # Mock retrieve to return existing history
    mock_memory_client.retrieve.return_value = {"actions": ["research.started"]}
    
    await workflow_state.record_action("research.completed")
    
    # Verify store was called with updated history
    mock_memory_client.store.assert_called_once_with(
        "_action_history",
        {"actions": ["research.started", "research.completed"]},
        plan_id="plan-123",
        tenant_id="test-tenant",
        user_id="test-user",
    )


@pytest.mark.asyncio
async def test_get_action_history(workflow_state, mock_memory_client):
    """Test getting action history."""
    mock_memory_client.retrieve.return_value = {"actions": ["action1", "action2"]}
    
    history = await workflow_state.get_action_history()
    
    assert history == ["action1", "action2"]
    mock_memory_client.retrieve.assert_called_once_with(
        "_action_history",
        plan_id="plan-123",
        tenant_id="test-tenant",
        user_id="test-user",
    )


@pytest.mark.asyncio
async def test_get_action_history_empty(workflow_state, mock_memory_client):
    """Test getting action history when none exists."""
    mock_memory_client.retrieve.return_value = None
    
    history = await workflow_state.get_action_history()
    
    assert history == []


@pytest.mark.asyncio
async def test_set_and_get(workflow_state, mock_memory_client):
    """Test setting and getting a value."""
    await workflow_state.set("test_key", "test_value")
    
    # Verify store was called correctly
    mock_memory_client.store.assert_called_once_with(
        "test_key",
        "test_value",
        plan_id="plan-123",
        tenant_id="test-tenant",
        user_id="test-user",
    )
    
    # Mock retrieve
    mock_memory_client.retrieve.return_value = "test_value"
    
    value = await workflow_state.get("test_key")
    
    assert value == "test_value"
    mock_memory_client.retrieve.assert_called_once_with(
        "test_key",
        plan_id="plan-123",
        tenant_id="test-tenant",
        user_id="test-user",
    )


@pytest.mark.asyncio
async def test_get_default(workflow_state, mock_memory_client):
    """Test getting with default value."""
    mock_memory_client.retrieve.return_value = None
    
    value = await workflow_state.get("missing_key", default="default_value")
    
    assert value == "default_value"


@pytest.mark.asyncio
async def test_has(workflow_state, mock_memory_client):
    """Test checking if key exists."""
    # Key exists
    mock_memory_client.retrieve.return_value = "some_value"
    
    exists = await workflow_state.has("existing_key")
    assert exists is True
    
    # Key doesn't exist
    mock_memory_client.retrieve.return_value = None
    
    exists = await workflow_state.has("missing_key")
    assert exists is False


@pytest.mark.asyncio
async def test_increment(workflow_state, mock_memory_client):
    """Test incrementing a counter."""
    # Mock retrieve (existing counter)
    mock_memory_client.retrieve.return_value = 5
    
    new_value = await workflow_state.increment("counter")
    
    assert new_value == 6
    mock_memory_client.store.assert_called_once_with(
        "counter",
        6,
        plan_id="plan-123",
        tenant_id="test-tenant",
        user_id="test-user",
    )


@pytest.mark.asyncio
async def test_increment_new_counter(workflow_state, mock_memory_client):
    """Test incrementing a new counter."""
    # Mock retrieve (counter doesn't exist)
    mock_memory_client.retrieve.return_value = None
    
    new_value = await workflow_state.increment("new_counter")
    
    assert new_value == 1
    mock_memory_client.store.assert_called_once_with(
        "new_counter",
        1,
        plan_id="plan-123",
        tenant_id="test-tenant",
        user_id="test-user",
    )


@pytest.mark.asyncio
async def test_append(workflow_state, mock_memory_client):
    """Test appending to a list."""
    # Mock retrieve (existing list)
    mock_memory_client.retrieve.return_value = ["item1", "item2"]
    
    new_list = await workflow_state.append("items", "item3")
    
    assert new_list == ["item1", "item2", "item3"]
    mock_memory_client.store.assert_called_once_with(
        "items",
        ["item1", "item2", "item3"],
        plan_id="plan-123",
        tenant_id="test-tenant",
        user_id="test-user",
    )


@pytest.mark.asyncio
async def test_extend(workflow_state, mock_memory_client):
    """Test extending a list."""
    # Mock retrieve (existing list)
    mock_memory_client.retrieve.return_value = ["item1"]
    
    new_list = await workflow_state.extend("items", ["item2", "item3"])
    
    assert new_list == ["item1", "item2", "item3"]
    mock_memory_client.store.assert_called_once_with(
        "items",
        ["item1", "item2", "item3"],
        plan_id="plan-123",
        tenant_id="test-tenant",
        user_id="test-user",
    )


@pytest.mark.asyncio
async def test_update_dict(workflow_state, mock_memory_client):
    """Test updating a dictionary."""
    # Mock retrieve (existing dict)
    mock_memory_client.retrieve.return_value = {"key1": "value1"}
    
    new_dict = await workflow_state.update_dict("config", {"key2": "value2"})
    
    assert new_dict == {"key1": "value1", "key2": "value2"}
    mock_memory_client.store.assert_called_once_with(
        "config",
        {"key1": "value1", "key2": "value2"},
        plan_id="plan-123",
        tenant_id="test-tenant",
        user_id="test-user",
    )
