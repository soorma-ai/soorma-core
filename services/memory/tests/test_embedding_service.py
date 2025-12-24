"""Tests for embedding service."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from memory_service.services.embedding import EmbeddingService


@pytest.fixture
def mock_openai_response():
    """Create mock OpenAI response."""
    mock_response = Mock()
    mock_response.data = [Mock(embedding=[0.1] * 1536)]
    return mock_response


@pytest.fixture
def mock_openai_batch_response():
    """Create mock OpenAI batch response."""
    mock_response = Mock()
    mock_response.data = [
        Mock(embedding=[0.1] * 1536),
        Mock(embedding=[0.2] * 1536),
        Mock(embedding=[0.3] * 1536),
    ]
    return mock_response


class TestEmbeddingService:
    """Test suite for EmbeddingService."""

    @pytest.mark.asyncio
    async def test_generate_embedding_success(self, mock_openai_response):
        """Test successful embedding generation."""
        with patch('memory_service.services.embedding.AsyncOpenAI') as mock_openai:
            mock_client = AsyncMock()
            mock_client.embeddings.create.return_value = mock_openai_response
            mock_openai.return_value = mock_client
            
            service = EmbeddingService()
            result = await service.generate_embedding("test text")
            
            assert isinstance(result, list)
            assert len(result) == 1536
            assert all(isinstance(x, float) for x in result)
            mock_client.embeddings.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_embedding_empty_text(self):
        """Test embedding generation with empty text returns zero vector."""
        service = EmbeddingService()
        
        # Test empty string
        result = await service.generate_embedding("")
        assert result == [0.0] * service.dimensions
        
        # Test whitespace only
        result = await service.generate_embedding("   ")
        assert result == [0.0] * service.dimensions
        
        # Test None-like empty
        result = await service.generate_embedding("  \n  \t  ")
        assert result == [0.0] * service.dimensions

    @pytest.mark.asyncio
    async def test_generate_embeddings_batch(self, mock_openai_batch_response):
        """Test batch embedding generation."""
        with patch('memory_service.services.embedding.AsyncOpenAI') as mock_openai:
            mock_client = AsyncMock()
            mock_client.embeddings.create.return_value = mock_openai_batch_response
            mock_openai.return_value = mock_client
            
            service = EmbeddingService()
            texts = ["text 1", "text 2", "text 3"]
            result = await service.generate_embeddings(texts)
            
            assert isinstance(result, list)
            assert len(result) == 3
            assert all(len(emb) == 1536 for emb in result)
            mock_client.embeddings.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_embeddings_empty_list(self):
        """Test batch embedding with empty list."""
        service = EmbeddingService()
        result = await service.generate_embeddings([])
        assert result == []

    @pytest.mark.asyncio
    async def test_generate_embeddings_mixed_empty(self, mock_openai_batch_response):
        """Test batch embedding with some empty texts."""
        with patch('memory_service.services.embedding.AsyncOpenAI') as mock_openai:
            mock_client = AsyncMock()
            mock_client.embeddings.create.return_value = mock_openai_batch_response
            mock_openai.return_value = mock_client
            
            service = EmbeddingService()
            texts = ["text 1", "", "text 2", "   ", "text 3"]
            result = await service.generate_embeddings(texts)
            
            assert len(result) == 5
            # Empty texts should have zero vectors
            assert result[1] == [0.0] * service.dimensions
            assert result[3] == [0.0] * service.dimensions

    @pytest.mark.asyncio
    async def test_generate_embeddings_all_empty(self):
        """Test batch embedding when all texts are empty."""
        service = EmbeddingService()
        texts = ["", "  ", "\n\t"]
        result = await service.generate_embeddings(texts)
        
        assert len(result) == 3
        assert all(emb == [0.0] * service.dimensions for emb in result)

    @pytest.mark.asyncio
    async def test_generate_embedding_api_error(self):
        """Test handling of API errors."""
        with patch('memory_service.services.embedding.AsyncOpenAI') as mock_openai:
            mock_client = AsyncMock()
            mock_client.embeddings.create.side_effect = Exception("API Error")
            mock_openai.return_value = mock_client
            
            service = EmbeddingService()
            
            with pytest.raises(Exception, match="API Error"):
                await service.generate_embedding("test text")

    def test_embedding_service_initialization(self):
        """Test service initializes with correct configuration."""
        service = EmbeddingService()
        
        assert service.client is not None
        assert service.model is not None
        assert service.dimensions == 1536  # Default dimension
