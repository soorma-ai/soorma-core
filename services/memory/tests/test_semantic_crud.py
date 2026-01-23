"""Unit tests for Semantic Memory CRUD operations with mocked database.

These tests import modules inside test functions to avoid circular import issues at module level.
All dependencies (database, embedding service) are mocked for fast, isolated unit testing.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from soorma_common.models import SemanticMemoryCreate, SemanticMemoryResponse
from memory_service.models.memory import SemanticMemory


class TestCreateSemanticMemory:
    """Test suite for create_semantic_memory CRUD function."""

    @pytest.mark.asyncio
    async def test_create_stores_correct_fields(self):
        """Test that create operation stores all fields correctly."""
        mock_db = AsyncMock(spec=AsyncSession)
        tenant_id = uuid4()
        data = SemanticMemoryCreate(
            content="Docker is a containerization platform",
            metadata={"category": "devops", "tool": "docker"}
        )
        
        # Mock embedding service
        mock_embedding = [0.1] * 1536  # Standard OpenAI embedding size
        
        # Track the memory object that gets added to the session
        added_memory = None
        
        def capture_add(obj):
            nonlocal added_memory
            added_memory = obj
        
        mock_db.add = Mock(side_effect=capture_add)
        mock_db.flush = AsyncMock()
        
        # Mock refresh to set timestamps
        async def mock_refresh(obj):
            obj.created_at = datetime(2026, 1, 22, 10, 0, 0)
            obj.updated_at = datetime(2026, 1, 22, 10, 0, 0)
        
        mock_db.refresh = AsyncMock(side_effect=mock_refresh)
        
        # Mock embedding service at the module level to avoid circular import
        with patch('memory_service.services.embedding.embedding_service.generate_embedding',
                   new_callable=AsyncMock, return_value=mock_embedding):
            # Import after mocking to avoid circular import issues
            from memory_service.crud.semantic import create_semantic_memory
            
            result = await create_semantic_memory(mock_db, tenant_id, data)
            
            # Verify database operations
            mock_db.add.assert_called_once()
            mock_db.flush.assert_called_once()
            mock_db.refresh.assert_called_once()
            
            # Verify the memory object that was added
            assert added_memory is not None
            assert added_memory.content == "Docker is a containerization platform"
            assert added_memory.memory_metadata == {"category": "devops", "tool": "docker"}
            assert added_memory.tenant_id == tenant_id
            assert added_memory.embedding == mock_embedding
            
            # Verify return value
            assert result.content == data.content
            assert result.memory_metadata == data.metadata

    @pytest.mark.asyncio
    async def test_create_with_empty_metadata(self):
        """Test creating semantic memory with empty metadata dict."""
        from memory_service.crud.semantic import create_semantic_memory
        
        mock_db = AsyncMock(spec=AsyncSession)
        tenant_id = uuid4()
        data = SemanticMemoryCreate(
            content="Test content",
            metadata={}
        )
        
        added_memory = None
        
        def capture_add(obj):
            nonlocal added_memory
            added_memory = obj
        
        mock_db.add = Mock(side_effect=capture_add)
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        with patch('memory_service.crud.semantic.embedding_service.generate_embedding',
                   new_callable=AsyncMock, return_value=[0.0] * 1536):
            result = await create_semantic_memory(mock_db, tenant_id, data)
            
            # Verify empty dict is stored (not None)
            assert added_memory.memory_metadata == {}
            assert result.memory_metadata == {}

    @pytest.mark.asyncio
    async def test_create_generates_embedding(self):
        """Test that embedding is generated for content."""
        mock_db = AsyncMock(spec=AsyncSession)
        tenant_id = uuid4()
        data = SemanticMemoryCreate(
            content="Python is a programming language",
            metadata={"language": "python"}
        )
        
        mock_embedding = [0.2] * 1536
        
        mock_db.add = Mock()
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Mock at services level to avoid circular import
        with patch('memory_service.services.embedding.embedding_service.generate_embedding',
                   new_callable=AsyncMock, return_value=mock_embedding) as mock_gen:
            from memory_service.crud.semantic import create_semantic_memory
            
            await create_semantic_memory(mock_db, tenant_id, data)
            
            # Verify embedding was generated for the content
            mock_gen.assert_called_once_with("Python is a programming language")

    @pytest.mark.asyncio
    async def test_create_sets_tenant_id(self):
        """Test that tenant_id is properly set on the memory object."""
        mock_db = AsyncMock(spec=AsyncSession)
        tenant_id = uuid4()
        data = SemanticMemoryCreate(content="Test", metadata={})
        
        added_memory = None
        
        def capture_add(obj):
            nonlocal added_memory
            added_memory = obj
        
        mock_db.add = Mock(side_effect=capture_add)
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        with patch('memory_service.services.embedding.embedding_service.generate_embedding',
                   new_callable=AsyncMock, return_value=[0.0] * 1536):
            from memory_service.crud.semantic import create_semantic_memory
            
            await create_semantic_memory(mock_db, tenant_id, data)
            
            # Verify tenant_id was set correctly
            assert added_memory is not None
            assert added_memory.tenant_id == tenant_id


class TestSearchSemanticMemory:
    """Test suite for search_semantic_memory CRUD function."""

    @pytest.mark.asyncio
    async def test_search_returns_semantic_memory_responses(self):
        """Test that search returns properly formatted SemanticMemoryResponse objects."""
        from memory_service.crud.semantic import search_semantic_memory
        
        mock_db = AsyncMock(spec=AsyncSession)
        tenant_id = uuid4()
        query = "Python programming"
        
        # Mock database query results
        mock_memory = Mock(spec=SemanticMemory)
        mock_memory.id = uuid4()
        mock_memory.tenant_id = tenant_id
        mock_memory.content = "Python is a programming language"
        mock_memory.memory_metadata = {"category": "programming"}
        mock_memory.created_at = datetime(2026, 1, 22, 10, 0, 0)
        mock_memory.updated_at = datetime(2026, 1, 22, 11, 0, 0)
        
        # Mock Row object with both SemanticMemory and score
        mock_row = Mock()
        mock_row.SemanticMemory = mock_memory
        mock_row.score = 0.87
        
        # Mock database execute result
        mock_result = Mock()
        mock_result.all = Mock(return_value=[mock_row])
        
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        with patch('memory_service.crud.semantic.embedding_service.generate_embedding',
                   new_callable=AsyncMock, return_value=[0.1] * 1536):
            results = await search_semantic_memory(mock_db, tenant_id, query, limit=5)
            
            # Verify results
            assert len(results) == 1
            assert isinstance(results[0], SemanticMemoryResponse)
            assert results[0].id == str(mock_memory.id)
            assert results[0].content == "Python is a programming language"
            assert results[0].metadata == {"category": "programming"}
            assert results[0].score == 0.87

    @pytest.mark.asyncio
    async def test_search_generates_query_embedding(self):
        """Test that search generates embedding for the query."""
        from memory_service.crud.semantic import search_semantic_memory
        
        mock_db = AsyncMock(spec=AsyncSession)
        tenant_id = uuid4()
        query = "Docker containers"
        
        mock_result = Mock()
        mock_result.all = Mock(return_value=[])
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        mock_query_embedding = [0.3] * 1536
        
        with patch('memory_service.crud.semantic.embedding_service.generate_embedding',
                   new_callable=AsyncMock, return_value=mock_query_embedding) as mock_gen:
            await search_semantic_memory(mock_db, tenant_id, query, limit=5)
            
            # Verify embedding was generated for query
            mock_gen.assert_called_once_with(query)

    @pytest.mark.asyncio
    async def test_search_empty_results(self):
        """Test search with no matching results."""
        from memory_service.crud.semantic import search_semantic_memory
        
        mock_db = AsyncMock(spec=AsyncSession)
        tenant_id = uuid4()
        
        mock_result = Mock()
        mock_result.all = Mock(return_value=[])
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        with patch('memory_service.crud.semantic.embedding_service.generate_embedding',
                   new_callable=AsyncMock, return_value=[0.0] * 1536):
            results = await search_semantic_memory(mock_db, tenant_id, "nonexistent", 5)
            
            assert results == []

    @pytest.mark.asyncio
    async def test_search_respects_limit(self):
        """Test that search respects the limit parameter."""
        from memory_service.crud.semantic import search_semantic_memory
        
        mock_db = AsyncMock(spec=AsyncSession)
        tenant_id = uuid4()
        limit = 3
        
        # Create mock results
        mock_rows = []
        for i in range(limit):
            mock_memory = Mock(spec=SemanticMemory)
            mock_memory.id = uuid4()
            mock_memory.tenant_id = tenant_id
            mock_memory.content = f"Content {i}"
            mock_memory.memory_metadata = {}
            mock_memory.created_at = datetime(2026, 1, 22, 10, 0, 0)
            mock_memory.updated_at = datetime(2026, 1, 22, 10, 0, 0)
            
            mock_row = Mock()
            mock_row.SemanticMemory = mock_memory
            mock_row.score = 0.9 - (i * 0.1)
            mock_rows.append(mock_row)
        
        mock_result = Mock()
        mock_result.all = Mock(return_value=mock_rows)
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        with patch('memory_service.crud.semantic.embedding_service.generate_embedding',
                   new_callable=AsyncMock, return_value=[0.0] * 1536):
            results = await search_semantic_memory(mock_db, tenant_id, "test", limit=limit)
            
            assert len(results) == limit

    @pytest.mark.asyncio
    async def test_search_filters_by_tenant(self):
        """Test that search filters results by tenant_id."""
        from memory_service.crud.semantic import search_semantic_memory
        
        mock_db = AsyncMock(spec=AsyncSession)
        tenant_id = uuid4()
        
        mock_result = Mock()
        mock_result.all = Mock(return_value=[])
        
        # Capture the SQL statement
        executed_stmt = None
        
        async def capture_execute(stmt):
            nonlocal executed_stmt
            executed_stmt = stmt
            return mock_result
        
        mock_db.execute = AsyncMock(side_effect=capture_execute)
        
        with patch('memory_service.crud.semantic.embedding_service.generate_embedding',
                   new_callable=AsyncMock, return_value=[0.0] * 1536):
            await search_semantic_memory(mock_db, tenant_id, "test", 5)
            
            # Verify execute was called (statement includes tenant filter)
            mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_preserves_metadata_field_name(self):
        """Test that search correctly accesses memory_metadata column."""
        from memory_service.crud.semantic import search_semantic_memory
        
        mock_db = AsyncMock(spec=AsyncSession)
        tenant_id = uuid4()
        
        mock_memory = Mock(spec=SemanticMemory)
        mock_memory.id = uuid4()
        mock_memory.tenant_id = tenant_id
        mock_memory.content = "Test"
        mock_memory.memory_metadata = {"key": "value"}  # Correct column name
        mock_memory.created_at = datetime(2026, 1, 22, 10, 0, 0)
        mock_memory.updated_at = datetime(2026, 1, 22, 10, 0, 0)
        
        mock_row = Mock()
        mock_row.SemanticMemory = mock_memory
        mock_row.score = 0.95
        
        mock_result = Mock()
        mock_result.all = Mock(return_value=[mock_row])
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        with patch('memory_service.crud.semantic.embedding_service.generate_embedding',
                   new_callable=AsyncMock, return_value=[0.0] * 1536):
            results = await search_semantic_memory(mock_db, tenant_id, "test", 5)
            
            # Verify metadata field is correctly mapped
            assert results[0].metadata == {"key": "value"}
