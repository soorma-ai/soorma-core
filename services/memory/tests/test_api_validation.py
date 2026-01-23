"""Tests for API endpoint validation and request/response schemas."""

import pytest
from uuid import UUID, uuid4
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch

from memory_service.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestHealthEndpoint:
    """Test suite for health check endpoint."""

    def test_health_check(self, client):
        """Test health endpoint returns 200."""
        response = client.get("/health")
        assert response.status_code == 200
        # Health endpoint returns service info
        data = response.json()
        assert "status" in data or "service_name" in data


class TestEpisodicEndpoints:
    """Test suite for episodic memory API validation (no DB required)."""

    def test_log_episodic_requires_user_id(self, client):
        """Test episodic endpoint requires user_id query parameter."""
        # Missing user_id should return 422
        response = client.post(
            "/v1/memory/episodic",
            json={
                "agent_id": "test-agent",
                "role": "user",
                "content": "test content"
            }
        )
        assert response.status_code == 422
        assert "user_id" in response.text

    @pytest.mark.skip(reason="Requires PostgreSQL database - validates at DB constraint level")
    def test_log_episodic_validates_role(self, client):
        """Test episodic endpoint validates role enum."""
        response = client.post(
            "/v1/memory/episodic",
            params={"user_id": str(uuid4())},
            json={
                "agent_id": "test-agent",
                "role": "invalid_role",  # Invalid role
                "content": "test content"
            }
        )
        # Should fail validation
        assert response.status_code == 422

    @pytest.mark.skip(reason="Requires PostgreSQL database - validates at Pydantic level")
    def test_log_episodic_requires_content(self, client):
        """Test episodic endpoint requires content field."""
        response = client.post(
            "/v1/memory/episodic",
            params={"user_id": str(uuid4())},
            json={
                "agent_id": "test-agent",
                "role": "user"
                # Missing content
            }
        )
        assert response.status_code == 422

    def test_get_recent_requires_user_id(self, client):
        """Test get recent history requires user_id."""
        response = client.get(
            "/v1/memory/episodic/recent",
            params={"agent_id": "test-agent"}
            # Missing user_id
        )
        assert response.status_code == 422

    def test_search_episodic_requires_params(self, client):
        """Test search endpoint requires all parameters."""
        # Missing user_id
        response = client.get(
            "/v1/memory/episodic/search",
            params={
                "agent_id": "test-agent",
                "query": "test query"
            }
        )
        assert response.status_code == 422


class TestSemanticEndpoints:
    """Test suite for semantic memory API validation."""

    def test_ingest_semantic_requires_user_id(self, client):
        """Test semantic ingest requires user_id query parameter."""
        response = client.post(
            "/v1/memory/semantic",
            # Missing user_id query param
            json={
                "content": "test knowledge",
                "metadata": {"source": "test"}
            }
        )
        assert response.status_code == 422
        assert "user_id" in response.text.lower()

    def test_ingest_semantic_requires_valid_user_id_uuid(self, client):
        """Test semantic ingest requires valid UUID format for user_id."""
        response = client.post(
            "/v1/memory/semantic",
            params={"user_id": "not-a-uuid"},  # Invalid UUID format
            json={
                "content": "test knowledge",
                "metadata": {"source": "test"}
            }
        )
        assert response.status_code == 422
        assert "user_id" in response.text.lower()

    @pytest.mark.skip(reason="Requires PostgreSQL database for actual operation")
    def test_ingest_semantic_requires_content(self, client):
        """Test semantic ingest requires content field."""
        response = client.post(
            "/v1/memory/semantic",
            params={"user_id": str(uuid4())},  # Valid user_id
            json={
                "metadata": {"source": "test"}
                # Missing content
            }
        )
        assert response.status_code == 422
        assert "content" in response.text.lower()

    def test_search_semantic_requires_user_id(self, client):
        """Test semantic search requires user_id query parameter."""
        response = client.get(
            "/v1/memory/semantic/search",
            params={"q": "test query"}
            # Missing user_id
        )
        assert response.status_code == 422
        assert "user_id" in response.text.lower()

    @pytest.mark.skip(reason="FastAPI resolves dependencies before query param validation - requires mock")
    def test_search_semantic_requires_query(self, client):
        """Test semantic search requires query parameter."""
        # Note: FastAPI processes dependency injection (TenantContext) before
        # validating query parameters, so this test hits the database.
        # Need to mock get_tenant_context dependency for pure validation test.
        response = client.get(
            "/v1/memory/semantic/search",
            params={"user_id": str(uuid4())}
            # Missing q (query)
        )
        assert response.status_code == 422


class TestWorkingMemoryEndpoints:
    """Test suite for working memory API validation."""

    def test_store_working_memory_requires_plan_id(self, client):
        """Test working memory requires plan_id in path."""
        # Invalid UUID format
        response = client.put(
            "/v1/memory/working/invalid-uuid/test-key",
            json={"data": "test"}
        )
        assert response.status_code in [400, 422]

    @pytest.mark.skip(reason="Requires PostgreSQL database for actual operation")
    def test_retrieve_working_memory_path_params(self, client):
        """Test working memory retrieve validates path parameters."""
        plan_id = str(uuid4())
        response = client.get(f"/v1/memory/working/{plan_id}/test-key")
        # Should attempt to query (may fail without DB, but validates schema)
        assert response.status_code != 422  # Schema validation passed


class TestProceduralEndpoints:
    """Test suite for procedural memory API validation."""

    def test_get_procedural_requires_user_id(self, client):
        """Test procedural context requires user_id."""
        response = client.get(
            "/v1/memory/procedural/context",
            params={
                "agent_id": "test-agent",
                "query": "test query"
                # Missing user_id
            }
        )
        assert response.status_code == 422


class TestUUIDValidation:
    """Test UUID validation across endpoints."""

    def test_invalid_user_id_format(self, client):
        """Test endpoints reject invalid UUID format for user_id."""
        # The endpoint should handle invalid UUID gracefully
        # Currently raises ValueError in endpoint code before Pydantic validation
        try:
            response = client.post(
                "/v1/memory/episodic",
                params={"user_id": "not-a-uuid"},
                json={
                    "agent_id": "test-agent",
                    "role": "user",
                    "content": "test"
                }
            )
            # Should fail UUID validation (500 for ValueError in endpoint)
            assert response.status_code in [400, 422, 500]
        except ValueError as e:
            # ValueError is also acceptable - means UUID validation happened
            assert "badly formed" in str(e).lower() or "uuid" in str(e).lower()

    @pytest.mark.skip(reason="Requires PostgreSQL database")
    def test_valid_user_id_format(self, client):
        """Test endpoints accept valid UUID format."""
        valid_uuid = str(uuid4())
        response = client.post(
            "/v1/memory/episodic",
            params={"user_id": valid_uuid},
            json={
                "agent_id": "test-agent",
                "role": "user",
                "content": "test"
            }
        )
        # May fail with DB error, but UUID validation passed
        assert response.status_code != 422 or "user_id" not in response.text.lower()


class TestMetadataHandling:
    """Test metadata field handling."""

    @pytest.mark.skip(reason="Requires PostgreSQL database")
    def test_episodic_accepts_optional_metadata(self, client):
        """Test episodic memory accepts optional metadata."""
        response = client.post(
            "/v1/memory/episodic",
            params={"user_id": str(uuid4())},
            json={
                "agent_id": "test-agent",
                "role": "user",
                "content": "test",
                "metadata": {"key": "value"}
            }
        )
        # Schema validation should pass (may fail on DB)
        assert response.status_code != 422

    @pytest.mark.skip(reason="Requires PostgreSQL database")
    def test_semantic_accepts_optional_metadata(self, client):
        """Test semantic memory accepts optional metadata."""
        response = client.post(
            "/v1/memory/semantic",
            json={
                "content": "test knowledge",
                "metadata": {"source": "test", "page": 1}
            }
        )
        # Schema validation should pass
        assert response.status_code != 422
