"""Unit tests for Episodic Memory Service layer."""

import pytest
from uuid import uuid4
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch

from memory_service.services.episodic_memory_service import EpisodicMemoryService
from memory_service.models.memory import EpisodicMemory
from soorma_common.models import EpisodicMemoryCreate, EpisodicMemoryResponse


class TestEpisodicMemoryServiceToResponse:
    """Test suite for _to_response method."""

    def test_to_response_with_all_fields(self):
        """Test converting database model to response DTO with all fields."""
        # Create mock EpisodicMemory model
        memory = Mock(spec=EpisodicMemory)
        memory.id = uuid4()
        memory.tenant_id = uuid4()
        memory.user_id = uuid4()
        memory.agent_id = "chat-agent"
        memory.role = "user"
        memory.content = "How do I reset my password?"
        memory.memory_metadata = {"session_id": "session-123", "source": "web"}
        memory.created_at = datetime(2026, 1, 22, 10, 0, 0)
        
        service = EpisodicMemoryService()
        response = service._to_response(memory, score=0.92)
        
        assert response.id == str(memory.id)
        assert response.tenant_id == str(memory.tenant_id)
        assert response.user_id == str(memory.user_id)
        assert response.agent_id == "chat-agent"
        assert response.role == "user"
        assert response.content == "How do I reset my password?"
        assert response.metadata == {"session_id": "session-123", "source": "web"}
        assert response.created_at == "2026-01-22T10:00:00"
        assert response.score == 0.92

    def test_to_response_without_score(self):
        """Test converting model to response without similarity score."""
        memory = Mock(spec=EpisodicMemory)
        memory.id = uuid4()
        memory.tenant_id = uuid4()
        memory.user_id = uuid4()
        memory.agent_id = "test-agent"
        memory.role = "assistant"
        memory.content = "Test response"
        memory.memory_metadata = {}
        memory.created_at = datetime(2026, 1, 22, 10, 0, 0)
        
        service = EpisodicMemoryService()
        response = service._to_response(memory, score=None)
        
        assert response.score is None
        assert response.content == "Test response"
        assert response.role == "assistant"

    def test_to_response_with_empty_metadata(self):
        """Test that empty metadata dict is preserved (not None)."""
        memory = Mock(spec=EpisodicMemory)
        memory.id = uuid4()
        memory.tenant_id = uuid4()
        memory.user_id = uuid4()
        memory.agent_id = "agent"
        memory.role = "system"
        memory.content = "System message"
        memory.memory_metadata = {}  # Empty dict
        memory.created_at = datetime.now(timezone.utc)
        
        service = EpisodicMemoryService()
        response = service._to_response(memory)
        
        assert response.metadata == {}
        assert response.metadata is not None

    def test_to_response_with_null_metadata(self):
        """Test handling of null metadata from database."""
        memory = Mock(spec=EpisodicMemory)
        memory.id = uuid4()
        memory.tenant_id = uuid4()
        memory.user_id = uuid4()
        memory.agent_id = "agent"
        memory.role = "tool"
        memory.content = "Tool output"
        memory.memory_metadata = None  # NULL from database
        memory.created_at = datetime.now(timezone.utc)
        
        service = EpisodicMemoryService()
        response = service._to_response(memory)
        
        # Should convert None to empty dict
        assert response.metadata == {}

    def test_to_response_preserves_all_roles(self):
        """Test that all valid roles are preserved."""
        roles = ["user", "assistant", "system", "tool"]
        
        for role in roles:
            memory = Mock(spec=EpisodicMemory)
            memory.id = uuid4()
            memory.tenant_id = uuid4()
            memory.user_id = uuid4()
            memory.agent_id = "agent"
            memory.role = role
            memory.content = f"Content for {role}"
            memory.memory_metadata = {}
            memory.created_at = datetime.now(timezone.utc)
            
            service = EpisodicMemoryService()
            response = service._to_response(memory)
            
            assert response.role == role


class TestEpisodicMemoryServiceLog:
    """Test suite for log method."""

    @pytest.mark.asyncio
    async def test_log_commits_transaction(self):
        """Test that log commits transaction after successful operation."""
        from memory_service.crud.episodic import create_episodic_memory
        
        service = EpisodicMemoryService()
        mock_db = AsyncMock()
        tenant_id = uuid4()
        user_id = uuid4()
        
        # Mock CRUD response
        mock_memory = Mock(spec=EpisodicMemory)
        mock_memory.id = uuid4()
        mock_memory.tenant_id = tenant_id
        mock_memory.user_id = user_id
        mock_memory.agent_id = "agent-1"
        mock_memory.role = "user"
        mock_memory.content = "Test message"
        mock_memory.memory_metadata = {}
        mock_memory.created_at = datetime.now(timezone.utc)
        
        data = EpisodicMemoryCreate(
            agent_id="agent-1",
            role="user",
            content="Test message",
            metadata={}
        )
        
        with patch('memory_service.services.episodic_memory_service.crud_log', return_value=mock_memory):
            result = await service.log(mock_db, tenant_id, user_id, data)
            
            # Verify commit was called
            mock_db.commit.assert_called_once()
            
            # Verify response format
            assert isinstance(result, EpisodicMemoryResponse)
            assert result.agent_id == "agent-1"
            assert result.content == "Test message"

    @pytest.mark.asyncio
    async def test_log_with_metadata(self):
        """Test logging interaction with metadata."""
        from memory_service.crud.episodic import create_episodic_memory
        
        service = EpisodicMemoryService()
        mock_db = AsyncMock()
        tenant_id = uuid4()
        user_id = uuid4()
        
        mock_memory = Mock(spec=EpisodicMemory)
        mock_memory.id = uuid4()
        mock_memory.tenant_id = tenant_id
        mock_memory.user_id = user_id
        mock_memory.agent_id = "chat-bot"
        mock_memory.role = "assistant"
        mock_memory.content = "Response text"
        mock_memory.memory_metadata = {"session_id": "abc123", "sentiment": "positive"}
        mock_memory.created_at = datetime.now(timezone.utc)
        
        data = EpisodicMemoryCreate(
            agent_id="chat-bot",
            role="assistant",
            content="Response text",
            metadata={"session_id": "abc123", "sentiment": "positive"}
        )
        
        with patch('memory_service.services.episodic_memory_service.crud_log', return_value=mock_memory):
            result = await service.log(mock_db, tenant_id, user_id, data)
            
            assert result.metadata == {"session_id": "abc123", "sentiment": "positive"}


class TestEpisodicMemoryServiceGetRecent:
    """Test suite for get_recent method."""

    @pytest.mark.asyncio
    async def test_get_recent_returns_list(self):
        """Test that get_recent returns list of responses from CRUD."""
        from memory_service.crud.episodic import get_recent_episodic_memory
        
        service = EpisodicMemoryService()
        mock_db = AsyncMock()
        tenant_id = uuid4()
        user_id = uuid4()
        
        # CRUD layer returns EpisodicMemoryResponse objects directly
        mock_responses = [
            EpisodicMemoryResponse(
                id=str(uuid4()),
                tenant_id=str(tenant_id),
                user_id=str(user_id),
                agent_id="agent-1",
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
                metadata={},
                created_at="2026-01-23T10:00:00"
            )
            for i in range(3)
        ]
        
        with patch('memory_service.services.episodic_memory_service.crud_get_recent', return_value=mock_responses):
            results = await service.get_recent(mock_db, tenant_id, user_id, "agent-1", limit=10)
            
            # Service returns CRUD response directly (no double conversion)
            assert len(results) == 3
            assert all(isinstance(r, EpisodicMemoryResponse) for r in results)
            assert results[0].content == "Message 0"
            assert results[1].content == "Message 1"

    @pytest.mark.asyncio
    async def test_get_recent_empty_results(self):
        """Test that get_recent handles empty results."""
        from memory_service.crud.episodic import get_recent_episodic_memory
        
        service = EpisodicMemoryService()
        mock_db = AsyncMock()
        
        with patch('memory_service.services.episodic_memory_service.crud_get_recent', return_value=[]):
            results = await service.get_recent(mock_db, uuid4(), uuid4(), "agent-1", limit=10)
            
            assert results == []


class TestEpisodicMemoryServiceSearch:
    """Test suite for search method."""

    @pytest.mark.asyncio
    async def test_search_returns_scored_results(self):
        """Test that search returns results with scores from CRUD."""
        from memory_service.crud.episodic import search_episodic_memory
        
        service = EpisodicMemoryService()
        mock_db = AsyncMock()
        tenant_id = uuid4()
        user_id = uuid4()
        
        # CRUD returns EpisodicMemoryResponse with scores
        mock_responses = [
            EpisodicMemoryResponse(
                id=str(uuid4()),
                tenant_id=str(tenant_id),
                user_id=str(user_id),
                agent_id="agent-1",
                role="user",
                content=f"Query-relevant message {i}",
                metadata={},
                created_at="2026-01-23T10:00:00",
                score=score
            )
            for i, score in enumerate([0.95, 0.87, 0.72])
        ]
        
        with patch('memory_service.services.episodic_memory_service.crud_search', return_value=mock_responses):
            results = await service.search(mock_db, tenant_id, user_id, "password reset", agent_id="agent-1")
            
            # Service returns CRUD responses directly
            assert len(results) == 3
            assert results[0].score == 0.95
            assert results[1].score == 0.87
            assert results[2].score == 0.72
            # Verify ordering is preserved (highest score first)
            assert results[0].score > results[1].score > results[2].score

    @pytest.mark.asyncio
    async def test_search_respects_limit(self):
        """Test that search respects limit parameter."""
        from memory_service.crud.episodic import search_episodic_memory
        
        service = EpisodicMemoryService()
        mock_db = AsyncMock()
        tenant_id = uuid4()
        user_id = uuid4()
        
        # Mock returns 3 results (limit applied in CRUD)
        mock_responses = [
            EpisodicMemoryResponse(
                id=str(uuid4()),
                tenant_id=str(tenant_id),
                user_id=str(user_id),
                agent_id="agent",
                role="user",
                content="test",
                metadata={},
                created_at="2026-01-23T10:00:00",
                score=0.9
            )
            for _ in range(3)
        ]
        
        with patch('memory_service.services.episodic_memory_service.crud_search', return_value=mock_responses):
            results = await service.search(mock_db, tenant_id, user_id, "query", limit=3)
            
            assert len(results) == 3
