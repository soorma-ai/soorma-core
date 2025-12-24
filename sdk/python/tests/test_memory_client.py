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
        "content": "Test knowledge",
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
            "content": "Test result",
            "metadata": {},
            "createdAt": "2025-12-23T00:00:00Z",
            "updatedAt": "2025-12-23T00:00:00Z",
            "score": 0.95,
        }
    ]
    mock_response.raise_for_status = MagicMock()
    
    memory_client._client = AsyncMock()
    memory_client._client.get = AsyncMock(return_value=mock_response)
    
    # Test
    results = await memory_client.search_knowledge(query="test query", limit=5)
    
    # Verify
    assert len(results) == 1
    assert isinstance(results[0], SemanticMemoryResponse)
    assert results[0].content == "Test result"
    assert results[0].score == 0.95
    memory_client._client.get.assert_called_once()


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
        content="Test interaction"
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
    results = await memory_client.get_recent_history(agent_id="agent-1", limit=10)
    
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
        value={"status": "completed"}
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
        key="research_summary"
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
