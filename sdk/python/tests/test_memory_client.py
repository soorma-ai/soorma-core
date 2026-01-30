"""
Tests for Memory Service SDK client.

These tests verify the MemoryClient API wrapper works correctly.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from soorma.memory import MemoryClient
from soorma_common.models import (
    SemanticMemoryResponse,
    EpisodicMemoryResponse,
    ProceduralMemoryResponse,
    WorkingMemoryResponse,
)


@pytest.fixture
def memory_client():
    """Create a MemoryClient instance for testing."""
    return MemoryClient(base_url="http://localhost:8083")


@pytest.mark.asyncio
async def test_store_knowledge(memory_client):
    """Test storing knowledge in semantic memory."""
    # Mock the httpx client
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "id": "123",
        "tenantId": "tenant-1",
        "userId": "user-1",
        "content": "Test knowledge",
        "externalId": None,
        "isPublic": False,
        "metadata": {"source": "test"},
        "createdAt": "2025-12-23T00:00:00Z",
        "updatedAt": "2025-12-23T00:00:00Z",
    }
    mock_response.raise_for_status = MagicMock()
    
    memory_client._client = AsyncMock()
    memory_client._client.post = AsyncMock(return_value=mock_response)
    
    # Test
    result = await memory_client.store_knowledge(
        content="Test knowledge",
        user_id="user-1",
        metadata={"source": "test"}
    )
    
    # Verify
    assert isinstance(result, SemanticMemoryResponse)
    assert result.content == "Test knowledge"
    assert result.metadata == {"source": "test"}
    memory_client._client.post.assert_called_once()


@pytest.mark.asyncio
async def test_search_knowledge(memory_client):
    """Test searching semantic memory."""
    # Mock the httpx client
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {
            "id": "123",
            "tenantId": "tenant-1",
            "userId": "user-1",
            "content": "Test result",
            "externalId": None,
            "isPublic": False,
            "metadata": {},
            "createdAt": "2025-12-23T00:00:00Z",
            "updatedAt": "2025-12-23T00:00:00Z",
            "score": 0.95,
        }
    ]
    mock_response.raise_for_status = MagicMock()
    
    memory_client._client = AsyncMock()
    memory_client._client.post = AsyncMock(return_value=mock_response)
    
    # Test
    results = await memory_client.search_knowledge(query="test query", user_id="user-1", limit=5)
    
    # Verify
    assert len(results) == 1
    assert isinstance(results[0], SemanticMemoryResponse)
    assert results[0].content == "Test result"
    assert results[0].score == 0.95
    memory_client._client.post.assert_called_once()


@pytest.mark.asyncio
async def test_log_interaction(memory_client):
    """Test logging an interaction to episodic memory."""
    # Mock the httpx client
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "id": "456",
        "tenantId": "tenant-1",
        "userId": "user-1",
        "agentId": "agent-1",
        "role": "assistant",
        "content": "Test interaction",
        "metadata": {},
        "createdAt": "2025-12-23T00:00:00Z",
    }
    mock_response.raise_for_status = MagicMock()
    
    memory_client._client = AsyncMock()
    memory_client._client.post = AsyncMock(return_value=mock_response)
    
    # Test
    result = await memory_client.log_interaction(
        agent_id="agent-1",
        role="assistant",
        content="Test interaction",
        user_id="test-user"
    )
    
    # Verify
    assert isinstance(result, EpisodicMemoryResponse)
    assert result.agent_id == "agent-1"
    assert result.role == "assistant"
    assert result.content == "Test interaction"
    memory_client._client.post.assert_called_once()


@pytest.mark.asyncio
async def test_get_recent_history(memory_client):
    """Test getting recent interaction history."""
    # Mock the httpx client
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {
            "id": "456",
            "tenantId": "tenant-1",
            "userId": "user-1",
            "agentId": "agent-1",
            "role": "user",
            "content": "Hello",
            "metadata": {},
            "createdAt": "2025-12-23T00:00:00Z",
        },
        {
            "id": "457",
            "tenantId": "tenant-1",
            "userId": "user-1",
            "agentId": "agent-1",
            "role": "assistant",
            "content": "Hi there!",
            "metadata": {},
            "createdAt": "2025-12-23T00:01:00Z",
        }
    ]
    mock_response.raise_for_status = MagicMock()
    
    memory_client._client = AsyncMock()
    memory_client._client.get = AsyncMock(return_value=mock_response)
    
    # Test
    results = await memory_client.get_recent_history(
        agent_id="agent-1",
        user_id="test-user",
        limit=10
    )
    
    # Verify
    assert len(results) == 2
    assert isinstance(results[0], EpisodicMemoryResponse)
    assert results[0].role == "user"
    assert results[1].role == "assistant"
    memory_client._client.get.assert_called_once()


@pytest.mark.asyncio
async def test_search_interactions(memory_client):
    """Test searching episodic memory."""
    # Mock the httpx client
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {
            "id": "456",
            "tenantId": "tenant-1",
            "userId": "user-1",
            "agentId": "agent-1",
            "role": "assistant",
            "content": "Relevant interaction",
            "metadata": {},
            "createdAt": "2025-12-23T00:00:00Z",
            "score": 0.89,
        }
    ]
    mock_response.raise_for_status = MagicMock()
    
    memory_client._client = AsyncMock()
    memory_client._client.get = AsyncMock(return_value=mock_response)
    
    # Test
    results = await memory_client.search_interactions(
        agent_id="agent-1",
        query="relevant",
        user_id="test-user",
        limit=5
    )
    
    # Verify
    assert len(results) == 1
    assert isinstance(results[0], EpisodicMemoryResponse)
    assert results[0].content == "Relevant interaction"
    assert results[0].score == 0.89
    memory_client._client.get.assert_called_once()


@pytest.mark.asyncio
async def test_get_relevant_skills(memory_client):
    """Test getting relevant procedural knowledge."""
    # Mock the httpx client
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {
            "id": "789",
            "tenantId": "tenant-1",
            "userId": "user-1",
            "agentId": "agent-1",
            "triggerCondition": "billing question",
            "procedureType": "system_prompt",
            "content": "Always check Stripe first",
            "createdAt": "2025-12-23T00:00:00Z",
            "score": 0.92,
        }
    ]
    mock_response.raise_for_status = MagicMock()
    
    memory_client._client = AsyncMock()
    memory_client._client.get = AsyncMock(return_value=mock_response)
    
    # Test
    results = await memory_client.get_relevant_skills(
        agent_id="agent-1",
        context="user asks about billing",
        user_id="test-user",
        limit=3
    )
    
    # Verify
    assert len(results) == 1
    assert isinstance(results[0], ProceduralMemoryResponse)
    assert results[0].procedure_type == "system_prompt"
    assert results[0].content == "Always check Stripe first"
    assert results[0].score == 0.92
    memory_client._client.get.assert_called_once()


@pytest.mark.asyncio
async def test_set_plan_state(memory_client):
    """Test setting working memory state."""
    # Mock the httpx client
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "id": "101",
        "tenantId": "tenant-1",
        "planId": "plan-123",
        "key": "research_summary",
        "value": {"status": "completed"},
        "updatedAt": "2025-12-23T00:00:00Z",
    }
    mock_response.raise_for_status = MagicMock()
    
    memory_client._client = AsyncMock()
    memory_client._client.put = AsyncMock(return_value=mock_response)
    
    # Test
    result = await memory_client.set_plan_state(
        plan_id="plan-123",
        key="research_summary",
        value={"status": "completed"},
        tenant_id="test-tenant",
        user_id="test-user"
    )
    
    # Verify
    assert isinstance(result, WorkingMemoryResponse)
    assert result.plan_id == "plan-123"
    assert result.key == "research_summary"
    assert result.value == {"status": "completed"}
    memory_client._client.put.assert_called_once()


@pytest.mark.asyncio
async def test_get_plan_state(memory_client):
    """Test getting working memory state."""
    # Mock the httpx client
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "id": "101",
        "tenantId": "tenant-1",
        "planId": "plan-123",
        "key": "research_summary",
        "value": {"status": "completed"},
        "updatedAt": "2025-12-23T00:00:00Z",
    }
    mock_response.raise_for_status = MagicMock()
    
    memory_client._client = AsyncMock()
    memory_client._client.get = AsyncMock(return_value=mock_response)
    
    # Test
    result = await memory_client.get_plan_state(
        plan_id="plan-123",
        key="research_summary",
        tenant_id="test-tenant",
        user_id="test-user"
    )
    
    # Verify
    assert isinstance(result, WorkingMemoryResponse)
    assert result.plan_id == "plan-123"
    assert result.key == "research_summary"
    assert result.value == {"status": "completed"}
    memory_client._client.get.assert_called_once()


@pytest.mark.asyncio
async def test_health_check(memory_client):
    """Test health check endpoint."""
    # Mock the httpx client
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "status": "healthy",
        "service": "memory-service",
        "version": "0.5.0"
    }
    mock_response.raise_for_status = MagicMock()
    
    memory_client._client = AsyncMock()
    memory_client._client.get = AsyncMock(return_value=mock_response)
    
    # Test
    result = await memory_client.health()
    
    # Verify
    assert result["status"] == "healthy"
    assert result["service"] == "memory-service"
    memory_client._client.get.assert_called_once()


@pytest.mark.asyncio
async def test_close(memory_client):
    """Test closing the client."""
    memory_client._client = AsyncMock()
    memory_client._client.aclose = AsyncMock()
    
    # Test
    await memory_client.close()
    
    # Verify
    memory_client._client.aclose.assert_called_once()


@pytest.mark.asyncio
async def test_context_manager(memory_client):
    """Test using client as async context manager."""
    memory_client._client = AsyncMock()
    memory_client._client.aclose = AsyncMock()
    
    # Test
    async with memory_client as client:
        assert client == memory_client
    
    # Verify close was called
    memory_client._client.aclose.assert_called_once()

# Plans & Sessions Management Tests


@pytest.mark.asyncio
async def test_create_plan(memory_client):
    """Test creating a plan record."""
    # Mock the httpx client
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "tenantId": "tenant-1",
        "userId": "user-1",
        "planId": "plan-123",
        "sessionId": "session-456",
        "goalEvent": "chat.conversation",
        "goalData": {"type": "demo"},
        "status": "running",
        "createdAt": "2025-12-23T00:00:00Z",
        "updatedAt": "2025-12-23T00:00:00Z",
    }
    mock_response.raise_for_status = MagicMock()
    
    memory_client._client = AsyncMock()
    memory_client._client.post = AsyncMock(return_value=mock_response)
    
    # Test
    result = await memory_client.create_plan(
        plan_id="plan-123",
        goal_event="chat.conversation",
        goal_data={"type": "demo"},
        tenant_id="tenant-1",
        user_id="user-1",
        session_id="session-456"
    )
    
    # Verify
    assert result.plan_id == "plan-123"
    assert result.session_id == "session-456"
    assert result.goal_event == "chat.conversation"
    assert result.status == "running"
    
    # Verify headers were sent
    call_args = memory_client._client.post.call_args
    assert call_args.kwargs["headers"]["X-Tenant-ID"] == "tenant-1"
    assert call_args.kwargs["headers"]["X-User-ID"] == "user-1"
    memory_client._client.post.assert_called_once()


@pytest.mark.asyncio
async def test_delete_plan(memory_client):
    """Test deleting a plan record also deletes working memory."""
    # Mock the httpx client for successful deletion
    mock_delete_response = MagicMock()
    mock_delete_response.raise_for_status = MagicMock()
    mock_delete_response.json.return_value = {
        "success": True,
        "count_deleted": 2,
        "message": "Deleted 2 keys"
    }
    
    mock_plan_response = MagicMock()
    mock_plan_response.raise_for_status = MagicMock()
    
    memory_client._client = AsyncMock()
    memory_client._client.delete = AsyncMock(side_effect=[mock_delete_response, mock_plan_response])
    
    # Test successful deletion
    result = await memory_client.delete_plan(
        plan_id="plan-123",
        tenant_id="tenant-1",
        user_id="user-1"
    )
    
    # Verify
    assert result is True
    
    # Verify both delete calls were made (working memory + plan)
    assert memory_client._client.delete.call_count == 2
    
    # Check first call was to delete working memory
    first_call = memory_client._client.delete.call_args_list[0]
    assert "/working/plan-123" in str(first_call)
    
    # Check second call was to delete plan
    second_call = memory_client._client.delete.call_args_list[1]
    assert "/plans/plan-123" in str(second_call)
    assert second_call.kwargs["headers"]["X-Tenant-ID"] == "tenant-1"
    assert second_call.kwargs["headers"]["X-User-ID"] == "user-1"


@pytest.mark.asyncio
async def test_delete_plan_not_found(memory_client):
    """Test deleting a non-existent plan returns False."""
    # Mock 404 response
    import httpx
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Not found", request=MagicMock(), response=mock_response
    )
    
    memory_client._client = AsyncMock()
    memory_client._client.delete = AsyncMock(return_value=mock_response)
    
    # Test
    result = await memory_client.delete_plan(
        plan_id="nonexistent",
        tenant_id="tenant-1",
        user_id="user-1"
    )
    
    # Verify returns False for 404
    assert result is False


@pytest.mark.asyncio
async def test_list_plans(memory_client):
    """Test listing plans with tenant_id and user_id."""
    # Mock the httpx client
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {
            "tenantId": "tenant-1",
            "userId": "user-1",
            "planId": "plan-123",
            "sessionId": "session-456",
            "goalEvent": "chat.conversation",
            "goalData": {"type": "demo"},
            "status": "running",
            "createdAt": "2025-12-23T00:00:00Z",
            "updatedAt": "2025-12-23T00:00:00Z",
        },
        {
            "tenantId": "tenant-1",
            "userId": "user-1",
            "planId": "plan-124",
            "sessionId": "session-456",
            "goalEvent": "task.analyze",
            "goalData": {"task": "review"},
            "status": "completed",
            "createdAt": "2025-12-23T01:00:00Z",
            "updatedAt": "2025-12-23T01:30:00Z",
        }
    ]
    mock_response.raise_for_status = MagicMock()
    
    memory_client._client = AsyncMock()
    memory_client._client.get = AsyncMock(return_value=mock_response)
    
    # Test
    results = await memory_client.list_plans(
        tenant_id="tenant-1",
        user_id="user-1",
        status="running",
        limit=10
    )
    
    # Verify
    assert len(results) == 2
    assert results[0].plan_id == "plan-123"
    assert results[0].status == "running"
    assert results[1].plan_id == "plan-124"
    assert results[1].status == "completed"
    
    # Verify headers were sent
    call_args = memory_client._client.get.call_args
    assert call_args.kwargs["headers"]["X-Tenant-ID"] == "tenant-1"
    assert call_args.kwargs["headers"]["X-User-ID"] == "user-1"
    assert call_args.kwargs["params"]["status"] == "running"
    assert call_args.kwargs["params"]["limit"] == 10
    memory_client._client.get.assert_called_once()


@pytest.mark.asyncio
async def test_list_plans_without_tenant_user(memory_client):
    """Test listing plans without tenant_id/user_id headers."""
    # Mock the httpx client
    mock_response = MagicMock()
    mock_response.json.return_value = []
    mock_response.raise_for_status = MagicMock()
    
    memory_client._client = AsyncMock()
    memory_client._client.get = AsyncMock(return_value=mock_response)
    
    # Test
    results = await memory_client.list_plans(limit=20)
    
    # Verify
    assert len(results) == 0
    
    # Verify no headers were sent (or None was sent)
    call_args = memory_client._client.get.call_args
    headers = call_args.kwargs.get("headers")
    assert headers is None or headers == {}
    memory_client._client.get.assert_called_once()


@pytest.mark.asyncio
async def test_create_session(memory_client):
    """Test creating a session record."""
    # Mock the httpx client
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "tenantId": "tenant-1",
        "userId": "user-1",
        "sessionId": "session-789",
        "name": "Test Session",
        "metadata": {"context": "testing"},
        "createdAt": "2025-12-23T00:00:00Z",
        "lastInteraction": "2025-12-23T00:00:00Z",
    }
    mock_response.raise_for_status = MagicMock()
    
    memory_client._client = AsyncMock()
    memory_client._client.post = AsyncMock(return_value=mock_response)
    
    # Test
    result = await memory_client.create_session(
        session_id="session-789",
        name="Test Session",
        metadata={"context": "testing"}
    )
    
    # Verify
    assert result.session_id == "session-789"
    assert result.name == "Test Session"
    assert result.metadata == {"context": "testing"}
    memory_client._client.post.assert_called_once()


@pytest.mark.asyncio
async def test_list_sessions(memory_client):
    """Test listing sessions."""
    # Mock the httpx client
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {
            "tenantId": "tenant-1",
            "userId": "user-1",
            "sessionId": "session-789",
            "name": "Test Session",
            "metadata": {"context": "testing"},
            "createdAt": "2025-12-23T00:00:00Z",
            "lastInteraction": "2025-12-23T00:00:00Z",
        },
        {
            "tenantId": "tenant-1",
            "userId": "user-1",
            "sessionId": "session-790",
            "name": "Another Session",
            "metadata": {},
            "createdAt": "2025-12-23T01:00:00Z",
            "lastInteraction": "2025-12-23T01:00:00Z",
        }
    ]
    mock_response.raise_for_status = MagicMock()
    
    memory_client._client = AsyncMock()
    memory_client._client.get = AsyncMock(return_value=mock_response)
    
    # Test
    results = await memory_client.list_sessions(limit=10)
    
    # Verify
    assert len(results) == 2
    assert results[0].session_id == "session-789"
    assert results[0].name == "Test Session"
    assert results[1].session_id == "session-790"
    assert results[1].name == "Another Session"
    memory_client._client.get.assert_called_once()