"""Tests for WorkflowState helper class."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from soorma.workflow import WorkflowState
from soorma_common.models import WorkingMemoryResponse


@pytest.fixture
def mock_memory_client():
    """Create a mock MemoryClient."""
    client = AsyncMock()
    return client


@pytest.fixture
def workflow_state(mock_memory_client):
    """Create a WorkflowState instance."""
    return WorkflowState(mock_memory_client, "plan-123")


@pytest.mark.asyncio
async def test_record_action_new_history(workflow_state, mock_memory_client):
    """Test recording action with new history."""
    # Mock get_plan_state to raise exception (key doesn't exist)
    mock_memory_client.get_plan_state.side_effect = Exception("Not found")
    
    # Mock set_plan_state
    mock_memory_client.set_plan_state.return_value = WorkingMemoryResponse(
        id="1",
        tenant_id="tenant-1",
        plan_id="plan-123",
        key="_action_history",
        value={"actions": ["research.started"]},
        updated_at="2026-01-21T00:00:00Z",
    )
    
    await workflow_state.record_action("research.started")
    
    # Verify set_plan_state was called with correct data
    mock_memory_client.set_plan_state.assert_called_once_with(
        "plan-123",
        "_action_history",
        {"actions": ["research.started"]},
    )


@pytest.mark.asyncio
async def test_record_action_existing_history(workflow_state, mock_memory_client):
    """Test recording action with existing history."""
    # Mock get_plan_state to return existing history
    mock_memory_client.get_plan_state.return_value = WorkingMemoryResponse(
        id="1",
        tenant_id="tenant-1",
        plan_id="plan-123",
        key="_action_history",
        value={"actions": ["research.started"]},
        updated_at="2026-01-21T00:00:00Z",
    )
    
    await workflow_state.record_action("research.completed")
    
    # Verify set_plan_state was called with updated history
    mock_memory_client.set_plan_state.assert_called_once_with(
        "plan-123",
        "_action_history",
        {"actions": ["research.started", "research.completed"]},
    )


@pytest.mark.asyncio
async def test_get_action_history(workflow_state, mock_memory_client):
    """Test getting action history."""
    mock_memory_client.get_plan_state.return_value = WorkingMemoryResponse(
        id="1",
        tenant_id="tenant-1",
        plan_id="plan-123",
        key="_action_history",
        value={"actions": ["action1", "action2"]},
        updated_at="2026-01-21T00:00:00Z",
    )
    
    history = await workflow_state.get_action_history()
    
    assert history == ["action1", "action2"]


@pytest.mark.asyncio
async def test_get_action_history_empty(workflow_state, mock_memory_client):
    """Test getting action history when none exists."""
    mock_memory_client.get_plan_state.side_effect = Exception("Not found")
    
    history = await workflow_state.get_action_history()
    
    assert history == []


@pytest.mark.asyncio
async def test_set_and_get(workflow_state, mock_memory_client):
    """Test setting and getting a value."""
    # Mock set
    mock_memory_client.set_plan_state.return_value = WorkingMemoryResponse(
        id="1",
        tenant_id="tenant-1",
        plan_id="plan-123",
        key="test_key",
        value={"value": "test_value"},
        updated_at="2026-01-21T00:00:00Z",
    )
    
    await workflow_state.set("test_key", "test_value")
    
    # Verify set
    mock_memory_client.set_plan_state.assert_called_once_with(
        "plan-123",
        "test_key",
        {"value": "test_value"},
    )
    
    # Mock get
    mock_memory_client.get_plan_state.return_value = WorkingMemoryResponse(
        id="1",
        tenant_id="tenant-1",
        plan_id="plan-123",
        key="test_key",
        value={"value": "test_value"},
        updated_at="2026-01-21T00:00:00Z",
    )
    
    value = await workflow_state.get("test_key")
    
    assert value == "test_value"


@pytest.mark.asyncio
async def test_get_default(workflow_state, mock_memory_client):
    """Test getting with default value."""
    mock_memory_client.get_plan_state.side_effect = Exception("Not found")
    
    value = await workflow_state.get("missing_key", default="default_value")
    
    assert value == "default_value"


@pytest.mark.asyncio
async def test_has(workflow_state, mock_memory_client):
    """Test checking if key exists."""
    # Key exists
    mock_memory_client.get_plan_state.return_value = WorkingMemoryResponse(
        id="1",
        tenant_id="tenant-1",
        plan_id="plan-123",
        key="existing_key",
        value={"value": "value"},
        updated_at="2026-01-21T00:00:00Z",
    )
    
    exists = await workflow_state.has("existing_key")
    assert exists is True
    
    # Key doesn't exist
    mock_memory_client.get_plan_state.side_effect = Exception("Not found")
    
    exists = await workflow_state.has("missing_key")
    assert exists is False


@pytest.mark.asyncio
async def test_increment(workflow_state, mock_memory_client):
    """Test incrementing a counter."""
    # Mock get (existing counter)
    mock_memory_client.get_plan_state.return_value = WorkingMemoryResponse(
        id="1",
        tenant_id="tenant-1",
        plan_id="plan-123",
        key="counter",
        value={"value": 5},
        updated_at="2026-01-21T00:00:00Z",
    )
    
    # Mock set
    mock_memory_client.set_plan_state.return_value = WorkingMemoryResponse(
        id="1",
        tenant_id="tenant-1",
        plan_id="plan-123",
        key="counter",
        value={"value": 6},
        updated_at="2026-01-21T00:00:00Z",
    )
    
    new_value = await workflow_state.increment("counter")
    
    assert new_value == 6
    mock_memory_client.set_plan_state.assert_called_once_with(
        "plan-123",
        "counter",
        {"value": 6},
    )


@pytest.mark.asyncio
async def test_increment_new_counter(workflow_state, mock_memory_client):
    """Test incrementing a new counter."""
    # Mock get (counter doesn't exist)
    mock_memory_client.get_plan_state.side_effect = Exception("Not found")
    
    # Mock set
    mock_memory_client.set_plan_state.return_value = WorkingMemoryResponse(
        id="1",
        tenant_id="tenant-1",
        plan_id="plan-123",
        key="new_counter",
        value={"value": 1},
        updated_at="2026-01-21T00:00:00Z",
    )
    
    new_value = await workflow_state.increment("new_counter")
    
    assert new_value == 1


@pytest.mark.asyncio
async def test_append(workflow_state, mock_memory_client):
    """Test appending to a list."""
    # Mock get (existing list)
    mock_memory_client.get_plan_state.return_value = WorkingMemoryResponse(
        id="1",
        tenant_id="tenant-1",
        plan_id="plan-123",
        key="items",
        value={"value": ["item1", "item2"]},
        updated_at="2026-01-21T00:00:00Z",
    )
    
    # Mock set
    mock_memory_client.set_plan_state.return_value = WorkingMemoryResponse(
        id="1",
        tenant_id="tenant-1",
        plan_id="plan-123",
        key="items",
        value={"value": ["item1", "item2", "item3"]},
        updated_at="2026-01-21T00:00:00Z",
    )
    
    new_list = await workflow_state.append("items", "item3")
    
    assert new_list == ["item1", "item2", "item3"]


@pytest.mark.asyncio
async def test_extend(workflow_state, mock_memory_client):
    """Test extending a list."""
    # Mock get (existing list)
    mock_memory_client.get_plan_state.return_value = WorkingMemoryResponse(
        id="1",
        tenant_id="tenant-1",
        plan_id="plan-123",
        key="items",
        value={"value": ["item1"]},
        updated_at="2026-01-21T00:00:00Z",
    )
    
    # Mock set
    mock_memory_client.set_plan_state.return_value = WorkingMemoryResponse(
        id="1",
        tenant_id="tenant-1",
        plan_id="plan-123",
        key="items",
        value={"value": ["item1", "item2", "item3"]},
        updated_at="2026-01-21T00:00:00Z",
    )
    
    new_list = await workflow_state.extend("items", ["item2", "item3"])
    
    assert new_list == ["item1", "item2", "item3"]


@pytest.mark.asyncio
async def test_update_dict(workflow_state, mock_memory_client):
    """Test updating a dictionary."""
    # Mock get (existing dict)
    mock_memory_client.get_plan_state.return_value = WorkingMemoryResponse(
        id="1",
        tenant_id="tenant-1",
        plan_id="plan-123",
        key="config",
        value={"value": {"key1": "value1"}},
        updated_at="2026-01-21T00:00:00Z",
    )
    
    # Mock set
    mock_memory_client.set_plan_state.return_value = WorkingMemoryResponse(
        id="1",
        tenant_id="tenant-1",
        plan_id="plan-123",
        key="config",
        value={"value": {"key1": "value1", "key2": "value2"}},
        updated_at="2026-01-21T00:00:00Z",
    )
    
    new_dict = await workflow_state.update_dict("config", {"key2": "value2"})
    
    assert new_dict == {"key1": "value1", "key2": "value2"}
