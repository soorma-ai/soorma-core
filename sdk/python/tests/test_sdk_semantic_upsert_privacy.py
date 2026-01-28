"""SDK tests for Semantic Memory Upsert and Privacy (Stage 2.1 - RF-ARCH-012 + RF-ARCH-014).

Tests validate SDK behavior for:
- RF-ARCH-012: Upsert by external_id or content_hash
- RF-ARCH-014: User-scoped privacy (default private, optional public)

Focus: SDK contract and integration with Memory Service API
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from soorma.memory.client import MemoryClient
from soorma_common.models import SemanticMemoryResponse


@pytest.fixture
def memory_client():
    """Create a MemoryClient instance for testing."""
    return MemoryClient(base_url="http://localhost:8083")


class TestSemanticUpsertSDK:
    """Test SDK upsert behavior with external_id and content_hash."""

    @pytest.mark.asyncio
    async def test_store_knowledge_with_external_id(self, memory_client):
        """Should store knowledge with external_id for versioning."""
        # Setup mock
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "mem-1",
            "tenantId": "tenant-1",
            "userId": "user-alice",
            "content": "Docker v2",
            "externalId": "doc-docker",
            "isPublic": False,
            "metadata": {"version": "2.0"},
            "createdAt": "2026-01-27T10:00:00Z",
            "updatedAt": "2026-01-27T10:00:00Z",
        }
        mock_response.raise_for_status = MagicMock()
        
        memory_client._client = AsyncMock()
        memory_client._client.post = AsyncMock(return_value=mock_response)
        
        # Call store_knowledge with external_id
        result = await memory_client.store_knowledge(
            content="Docker v2",
            user_id="user-alice",
            external_id="doc-docker",
            metadata={"version": "2.0"}
        )
        
        # Verify result
        assert result.content == "Docker v2"
        assert result.external_id == "doc-docker"
        assert result.user_id == "user-alice"
        assert result.is_public == False
        
        # Verify API call includes user_id as query parameter
        call_kwargs = memory_client._client.post.call_args.kwargs
        assert call_kwargs["params"]["user_id"] == "user-alice"
        
        # Verify DTO doesn't include user_id in body
        dto_payload = call_kwargs["json"]
        assert "user_id" not in dto_payload
        assert dto_payload["externalId"] == "doc-docker"  # camelCase
        assert dto_payload["content"] == "Docker v2"

    @pytest.mark.asyncio
    async def test_store_knowledge_auto_dedupe_without_external_id(self, memory_client):
        """Should deduplicate by content_hash when no external_id provided."""
        # Setup mock
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "mem-2",
            "tenantId": "tenant-1",
            "userId": "user-bob",
            "content": "Python is a programming language",
            "externalId": None,
            "isPublic": False,
            "metadata": {},
            "createdAt": "2026-01-27T10:00:00Z",
            "updatedAt": "2026-01-27T10:00:00Z",
        }
        mock_response.raise_for_status = MagicMock()
        
        memory_client._client = AsyncMock()
        memory_client._client.post = AsyncMock(return_value=mock_response)
        
        # Call without external_id (relies on content_hash)
        result = await memory_client.store_knowledge(
            content="Python is a programming language",
            user_id="user-bob"
        )
        
        # Verify result
        assert result.content == "Python is a programming language"
        assert result.external_id is None
        
        # Verify DTO doesn't include external_id (None defaults to omit)
        dto_payload = memory_client._client.post.call_args.kwargs["json"]
        assert dto_payload["externalId"] is None  # camelCase

    @pytest.mark.asyncio
    async def test_store_knowledge_with_is_public_flag(self, memory_client):
        """Should respect is_public flag for knowledge visibility."""
        # Setup mock for public knowledge
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "mem-3",
            "tenantId": "tenant-1",
            "userId": "user-alice",
            "content": "Team's API best practices",
            "externalId": "best-practices",
            "isPublic": True,
            "metadata": {},
            "createdAt": "2026-01-27T10:00:00Z",
            "updatedAt": "2026-01-27T10:00:00Z",
        }
        mock_response.raise_for_status = MagicMock()
        
        memory_client._client = AsyncMock()
        memory_client._client.post = AsyncMock(return_value=mock_response)
        
        # Store as public
        result = await memory_client.store_knowledge(
            content="Team's API best practices",
            user_id="user-alice",
            external_id="best-practices",
            is_public=True  # Mark as public
        )
        
        # Verify result is public
        assert result.is_public == True
        
        # Verify DTO includes is_public=True
        dto_payload = memory_client._client.post.call_args.kwargs["json"]
        assert dto_payload["isPublic"] == True  # camelCase

    @pytest.mark.asyncio
    async def test_store_knowledge_private_by_default(self, memory_client):
        """Should default to private (is_public=False) when not specified."""
        # Setup mock
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "mem-4",
            "tenantId": "tenant-1",
            "userId": "user-charlie",
            "content": "My private notes",
            "externalId": None,
            "isPublic": False,
            "metadata": {},
            "createdAt": "2026-01-27T10:00:00Z",
            "updatedAt": "2026-01-27T10:00:00Z",
        }
        mock_response.raise_for_status = MagicMock()
        
        memory_client._client = AsyncMock()
        memory_client._client.post = AsyncMock(return_value=mock_response)
        
        # Store without specifying is_public (should default to False)
        result = await memory_client.store_knowledge(
            content="My private notes",
            user_id="user-charlie"
        )
        
        # Verify defaults to private
        assert result.is_public == False
        
        # Verify DTO includes is_public=False
        dto_payload = memory_client._client.post.call_args.kwargs["json"]
        assert dto_payload["isPublic"] == False  # camelCase


class TestSemanticQuerySDK:
    """Test SDK query behavior with privacy support."""

    @pytest.mark.asyncio
    async def test_query_knowledge_passes_user_id(self, memory_client):
        """Should pass user_id as query parameter in query requests."""
        # Setup mock
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "id": "mem-5",
                "tenantId": "tenant-1",
                "userId": "user-alice",
                "content": "Search result",
                "externalId": None,
                "isPublic": False,
                "metadata": {},
                "createdAt": "2026-01-27T10:00:00Z",
                "updatedAt": "2026-01-27T10:00:00Z",
                "score": 0.95,
            }
        ]
        mock_response.raise_for_status = MagicMock()
        
        memory_client._client = AsyncMock()
        memory_client._client.post = AsyncMock(return_value=mock_response)
        
        # Call query_knowledge
        results = await memory_client.query_knowledge(
            query="search term",
            user_id="user-alice",
            limit=5,
            include_public=True
        )
        
        # Verify results
        assert len(results) == 1
        assert results[0].content == "Search result"
        assert results[0].user_id == "user-alice"
        
        # Verify user_id passed as query parameter
        call_kwargs = memory_client._client.post.call_args.kwargs
        assert call_kwargs["params"]["user_id"] == "user-alice"
        
        # Verify query params in JSON body (not user_id)
        json_payload = call_kwargs["json"]
        assert "user_id" not in json_payload
        assert json_payload["query"] == "search term"
        assert json_payload["limit"] == 5
        assert json_payload["include_public"] == True  # Plain dict, not DTO

    @pytest.mark.asyncio
    async def test_query_knowledge_exclude_public(self, memory_client):
        """Should exclude public knowledge when include_public=False."""
        # Setup mock
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "id": "mem-6",
                "tenantId": "tenant-1",
                "userId": "user-bob",
                "content": "Private knowledge",
                "externalId": None,
                "isPublic": False,
                "metadata": {},
                "createdAt": "2026-01-27T10:00:00Z",
                "updatedAt": "2026-01-27T10:00:00Z",
                "score": 0.88,
            }
        ]
        mock_response.raise_for_status = MagicMock()
        
        memory_client._client = AsyncMock()
        memory_client._client.post = AsyncMock(return_value=mock_response)
        
        # Query without public knowledge
        results = await memory_client.query_knowledge(
            query="search",
            user_id="user-bob",
            include_public=False
        )
        
        # Verify include_public passed correctly
        json_payload = memory_client._client.post.call_args.kwargs["json"]
        assert json_payload["include_public"] == False  # Plain dict, not DTO


class TestSemanticMetadataSDK:
    """Test SDK metadata, tags, and source handling."""

    @pytest.mark.asyncio
    async def test_store_knowledge_with_tags(self, memory_client):
        """Should include tags in metadata when provided."""
        # Setup mock
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "mem-7",
            "tenantId": "tenant-1",
            "userId": "user-dave",
            "content": "Docker content",
            "externalId": None,
            "isPublic": False,
            "metadata": {"tags": ["docker", "containers"]},
            "createdAt": "2026-01-27T10:00:00Z",
            "updatedAt": "2026-01-27T10:00:00Z",
        }
        mock_response.raise_for_status = MagicMock()
        
        memory_client._client = AsyncMock()
        memory_client._client.post = AsyncMock(return_value=mock_response)
        
        # Store with tags
        result = await memory_client.store_knowledge(
            content="Docker content",
            user_id="user-dave",
            tags=["docker", "containers"]
        )
        
        # Verify tags in response metadata
        assert result.metadata.get("tags") == ["docker", "containers"]
        
        # Verify tags passed in DTO
        dto_payload = memory_client._client.post.call_args.kwargs["json"]
        assert dto_payload["tags"] == ["docker", "containers"]

    @pytest.mark.asyncio
    async def test_store_knowledge_with_source(self, memory_client):
        """Should include source when provided."""
        # Setup mock
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "mem-8",
            "tenantId": "tenant-1",
            "userId": "user-eve",
            "content": "Python content",
            "externalId": None,
            "isPublic": False,
            "metadata": {"source": "documentation"},
            "createdAt": "2026-01-27T10:00:00Z",
            "updatedAt": "2026-01-27T10:00:00Z",
        }
        mock_response.raise_for_status = MagicMock()
        
        memory_client._client = AsyncMock()
        memory_client._client.post = AsyncMock(return_value=mock_response)
        
        # Store with source
        result = await memory_client.store_knowledge(
            content="Python content",
            user_id="user-eve",
            source="documentation"
        )
        
        # Verify source in response metadata
        assert result.metadata.get("source") == "documentation"
        
        # Verify source passed in DTO
        dto_payload = memory_client._client.post.call_args.kwargs["json"]
        assert dto_payload["source"] == "documentation"
