"""Unit tests for Semantic Memory Service layer."""

import pytest
from uuid import uuid4
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch

from memory_service.services.semantic_memory_service import SemanticMemoryService
from memory_service.models.memory import SemanticMemory
from soorma_common.models import SemanticMemoryCreate, SemanticMemoryResponse


class TestSemanticMemoryServiceToResponse:
    """Test suite for _to_response method."""

    def test_to_response_with_all_fields(self):
        """Test converting database model to response DTO with all fields."""
        # Create mock SemanticMemory model
        memory = Mock(spec=SemanticMemory)
        memory.id = uuid4()
        memory.tenant_id = uuid4()
        memory.user_id = "test_user_123"
        memory.content = "Python is a programming language"
        memory.external_id = None
        memory.is_public = False
        memory.memory_metadata = {"category": "programming", "language": "python"}
        memory.created_at = datetime(2026, 1, 22, 10, 0, 0)
        memory.updated_at = datetime(2026, 1, 22, 11, 0, 0)
        
        service = SemanticMemoryService()
        response = service._to_response(memory, score=0.85)
        
        assert response.id == str(memory.id)
        assert response.tenant_id == str(memory.tenant_id)
        assert response.content == "Python is a programming language"
        assert response.metadata == {"category": "programming", "language": "python"}
        assert response.created_at == "2026-01-22T10:00:00"
        assert response.updated_at == "2026-01-22T11:00:00"
        assert response.score == 0.85

    def test_to_response_without_score(self):
        """Test converting model to response without similarity score."""
        memory = Mock(spec=SemanticMemory)
        memory.id = uuid4()
        memory.tenant_id = uuid4()
        memory.user_id = "test_user_123"
        memory.content = "Test content"
        memory.external_id = None
        memory.is_public = False
        memory.memory_metadata = {}
        memory.created_at = datetime(2026, 1, 22, 10, 0, 0)
        memory.updated_at = datetime(2026, 1, 22, 10, 0, 0)
        
        service = SemanticMemoryService()
        response = service._to_response(memory, score=None)
        
        assert response.score is None
        assert response.content == "Test content"

    def test_to_response_with_empty_metadata(self):
        """Test that empty metadata dict is preserved (not None)."""
        memory = Mock(spec=SemanticMemory)
        memory.id = uuid4()
        memory.tenant_id = uuid4()
        memory.user_id = "test_user_123"
        memory.content = "Test"
        memory.external_id = None
        memory.is_public = False
        memory.memory_metadata = {}  # Empty dict
        memory.created_at = datetime.now(timezone.utc)
        memory.updated_at = datetime.now(timezone.utc)
        
        service = SemanticMemoryService()
        response = service._to_response(memory)
        
        assert response.metadata == {}
        assert response.metadata is not None

    def test_to_response_with_null_metadata(self):
        """Test handling of null metadata from database."""
        memory = Mock(spec=SemanticMemory)
        memory.id = uuid4()
        memory.tenant_id = uuid4()
        memory.user_id = "test_user_123"
        memory.content = "Test"
        memory.external_id = None
        memory.is_public = False
        memory.memory_metadata = None  # NULL from database
        memory.created_at = datetime.now(timezone.utc)
        memory.updated_at = datetime.now(timezone.utc)
        
        service = SemanticMemoryService()
        response = service._to_response(memory)
        
        # Should convert None to empty dict
        assert response.metadata == {}


class TestSemanticMemoryServiceIngest:
    """Test suite for ingest method."""

    @pytest.mark.asyncio
    async def test_ingest_success(self):
        """Test successful knowledge ingestion."""
        mock_db = AsyncMock()
        tenant_id = uuid4()
        data = SemanticMemoryCreate(
            content="FastAPI is a web framework",
            user_id="test_user_123",
            metadata={"framework": "fastapi"}
        )
        
        # Mock the CRUD response
        mock_memory = Mock(spec=SemanticMemory)
        mock_memory.id = uuid4()
        mock_memory.tenant_id = tenant_id
        mock_memory.user_id = "test_user_123"
        mock_memory.content = data.content
        mock_memory.external_id = None
        mock_memory.is_public = False
        mock_memory.memory_metadata = data.metadata
        mock_memory.created_at = datetime.now(timezone.utc)
        mock_memory.updated_at = datetime.now(timezone.utc)
        
        service = SemanticMemoryService()
        
        with patch('memory_service.crud.semantic.upsert_semantic_memory',
                   new_callable=AsyncMock, return_value=mock_memory):
            response = await service.ingest(mock_db, tenant_id, "test_user_123", data)
            
            # Verify commit was called
            mock_db.commit.assert_called_once()
            
            # Verify response
            assert response.content == "FastAPI is a web framework"
            assert response.metadata == {"framework": "fastapi"}

    @pytest.mark.asyncio
    async def test_ingest_with_empty_metadata(self):
        """Test ingestion with empty metadata dict."""
        mock_db = AsyncMock()
        tenant_id = uuid4()
        data = SemanticMemoryCreate(
            content="Test knowledge",
            user_id="test_user_123",
            metadata={}
        )
        
        mock_memory = Mock(spec=SemanticMemory)
        mock_memory.id = uuid4()
        mock_memory.tenant_id = tenant_id
        mock_memory.user_id = "test_user_123"
        mock_memory.content = data.content
        mock_memory.external_id = None
        mock_memory.is_public = False
        mock_memory.memory_metadata = {}
        mock_memory.created_at = datetime.now(timezone.utc)
        mock_memory.updated_at = datetime.now(timezone.utc)
        
        service = SemanticMemoryService()
        
        with patch('memory_service.crud.semantic.upsert_semantic_memory',
                   new_callable=AsyncMock, return_value=mock_memory):
            response = await service.ingest(mock_db, tenant_id, "test_user_123", data)
            
            assert response.metadata == {}


class TestSemanticMemoryServiceSearch:
    """Test suite for search method."""

    @pytest.mark.asyncio
    async def test_search_returns_crud_results(self):
        """Test that search method returns CRUD layer results directly."""
        mock_db = AsyncMock()
        tenant_id = uuid4()
        query = "Python programming"
        limit = 5
        
        # Mock CRUD search returning SemanticMemoryResponse objects (not tuples!)
        mock_results = [
            SemanticMemoryResponse(
                id=str(uuid4()),
                tenant_id=str(tenant_id),
                user_id="test_user_123",
                content="Python is a programming language",
                external_id=None,
                is_public=False,
                metadata={"category": "programming"},
                created_at=datetime.now(timezone.utc).isoformat(),
                updated_at=datetime.now(timezone.utc).isoformat(),
                score=0.92
            ),
            SemanticMemoryResponse(
                id=str(uuid4()),
                tenant_id=str(tenant_id),
                user_id="test_user_123",
                content="Python was created by Guido van Rossum",
                external_id=None,
                is_public=False,
                metadata={"category": "history"},
                created_at=datetime.now(timezone.utc).isoformat(),
                updated_at=datetime.now(timezone.utc).isoformat(),
                score=0.85
            )
        ]
        
        service = SemanticMemoryService()
        
        with patch('memory_service.crud.semantic.search_semantic_memory',
                   new_callable=AsyncMock, return_value=mock_results):
            results = await service.search(mock_db, tenant_id, "test_user_123", query, limit)
            
            # Verify results are returned as-is (CRUD already returns Response DTOs)
            assert len(results) == 2
            assert results[0].score == 0.92
            assert results[1].score == 0.85
            assert results[0].content == "Python is a programming language"
            assert isinstance(results[0], SemanticMemoryResponse)

    @pytest.mark.asyncio
    async def test_search_empty_results(self):
        """Test search with no matching results."""
        mock_db = AsyncMock()
        tenant_id = uuid4()
        
        service = SemanticMemoryService()
        
        with patch('memory_service.crud.semantic.search_semantic_memory',
                   new_callable=AsyncMock, return_value=[]):
            results = await service.search(mock_db, tenant_id, "test_user_123", "nonexistent", 5)
            
            assert results == []

    @pytest.mark.asyncio
    async def test_search_with_limit_1(self):
        """Test search with limit=1 returns single result."""
        mock_db = AsyncMock()
        tenant_id = uuid4()
        
        mock_result = SemanticMemoryResponse(
            id=str(uuid4()),
            tenant_id=str(tenant_id),
            user_id="test_user_123",
            content="Test content",
            external_id=None,
            is_public=False,
            metadata={},
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
            score=1.0
        )
        
        service = SemanticMemoryService()
        
        with patch('memory_service.crud.semantic.search_semantic_memory',
                   new_callable=AsyncMock, return_value=[mock_result]):
            results = await service.search(mock_db, tenant_id, "test_user_123", "test", limit=1)
            
            assert len(results) == 1
            assert results[0].score == 1.0

    @pytest.mark.asyncio
    async def test_search_preserves_scores_order(self):
        """Test that search results maintain score ordering from CRUD layer."""
        mock_db = AsyncMock()
        tenant_id = uuid4()
        
        # CRUD returns results ordered by score (highest first)
        mock_results = [
            SemanticMemoryResponse(
                id=str(uuid4()), tenant_id=str(tenant_id),
                user_id="test_user_123",
                content="High score", 
                external_id=None,
                is_public=False,
                metadata={},
                created_at=datetime.now(timezone.utc).isoformat(),
                updated_at=datetime.now(timezone.utc).isoformat(),
                score=0.95
            ),
            SemanticMemoryResponse(
                id=str(uuid4()), tenant_id=str(tenant_id),
                user_id="test_user_123",
                content="Medium score", 
                external_id=None,
                is_public=False,
                metadata={},
                created_at=datetime.now(timezone.utc).isoformat(),
                updated_at=datetime.now(timezone.utc).isoformat(),
                score=0.75
            ),
            SemanticMemoryResponse(
                id=str(uuid4()), tenant_id=str(tenant_id),
                user_id="test_user_123",
                content="Low score", 
                external_id=None,
                is_public=False,
                metadata={},
                created_at=datetime.now(timezone.utc).isoformat(),
                updated_at=datetime.now(timezone.utc).isoformat(),
                score=0.45
            )
        ]
        
        service = SemanticMemoryService()
        
        with patch('memory_service.crud.semantic.search_semantic_memory',
                   new_callable=AsyncMock, return_value=mock_results):
            results = await service.search(mock_db, tenant_id, "test_user_123", "test", 3)
            
            # Verify order is preserved
            assert results[0].score == 0.95
            assert results[1].score == 0.75
            assert results[2].score == 0.45
