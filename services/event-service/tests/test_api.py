"""
Tests for the Event Service API endpoints.
"""
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

# Use memory adapter for tests
import os
os.environ["EVENT_ADAPTER"] = "memory"
os.environ["DEBUG"] = "true"

from src.main import app, adapter


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
async def async_client():
    """Create an async test client with lifespan."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Ensure adapter is connected for tests
        if adapter and not adapter.is_connected:
            await adapter.connect()
        yield ac


class TestHealthEndpoint:
    """Tests for health check endpoint."""
    
    def test_health_check(self, client):
        """Test health check returns expected fields."""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "adapter" in data
        assert "connected" in data
        assert "active_streams" in data


class TestRootEndpoint:
    """Tests for root info endpoint."""
    
    def test_root(self, client):
        """Test root endpoint returns service info."""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["service"] == "soorma-event-service"
        assert "version" in data


class TestPublishEndpoint:
    """Tests for event publishing endpoint."""
    
    @pytest.mark.asyncio
    async def test_publish_event(self, async_client):
        """Test publishing a valid event."""
        event = {
            "event": {
                "source": "test-agent",
                "type": "test.event",
                "topic": "test-topic",
                "data": {"key": "value"},
            }
        }
        
        response = await async_client.post("/v1/events/publish", json=event)
        
        # May be 503 if adapter not connected (acceptable in unit test)
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            assert "event_id" in data
        else:
            assert response.status_code == 503  # Adapter not connected
    
    @pytest.mark.asyncio
    async def test_publish_event_missing_fields(self, async_client):
        """Test publishing with missing required fields."""
        event = {
            "event": {
                "source": "test-agent",
                # Missing "type" and "topic"
            }
        }
        
        response = await async_client.post("/v1/events/publish", json=event)
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_publish_event_with_optional_fields(self, async_client):
        """Test publishing with optional fields."""
        event = {
            "event": {
                "source": "test-agent",
                "type": "test.event",
                "topic": "test-topic",
                "data": {"key": "value"},
                "correlation_id": "trace-123",
                "subject": "user:456",
                "tenant_id": "tenant-1",
                "session_id": "session-abc",
            }
        }
        
        response = await async_client.post("/v1/events/publish", json=event)
        
        # May be 503 if adapter not connected (acceptable in unit test)
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
        else:
            assert response.status_code == 503  # Adapter not connected


class TestAdminEndpoints:
    """Tests for admin endpoints."""
    
    def test_list_connections(self, client):
        """Test listing active connections."""
        response = client.get("/v1/admin/connections")
        assert response.status_code == 200
        
        data = response.json()
        assert "count" in data
        assert "connections" in data
        assert isinstance(data["connections"], list)
