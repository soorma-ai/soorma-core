"""Tests for Tracker Service main application (GREEN phase).

These tests verify that the actual implementation works correctly.
"""

import pytest
from fastapi.testclient import TestClient


def test_imports_work():
    """Test that all modules can be imported without errors."""
    from tracker_service import __version__
    from tracker_service.main import app
    from tracker_service.core.config import settings
    from tracker_service.core.db import get_db, init_db, close_db
    
    assert __version__ == "0.8.2"
    assert app is not None
    assert settings is not None
    assert get_db is not None
    assert init_db is not None
    assert close_db is not None


def test_health_check_endpoint():
    """Test that health check endpoint works."""
    from tracker_service.main import app
    
    client = TestClient(app)
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "tracker-service"
    assert data["version"] == "0.8.2"


@pytest.mark.asyncio
async def test_init_db_creates_engine():
    """Test that init_db creates database engine and session factory."""
    from tracker_service.core.db import init_db, close_db, engine, AsyncSessionLocal
    
    # Initialize database
    await init_db()
    
    try:
        # Import after init to get the initialized globals
        from tracker_service.core import db
        
        # Verify engine and session factory were created
        assert db.engine is not None
        assert db.AsyncSessionLocal is not None
    finally:
        # Cleanup
        await close_db()


@pytest.mark.asyncio
async def test_close_db_disposes_engine():
    """Test that close_db properly disposes the engine."""
    from tracker_service.core.db import init_db, close_db
    
    # Initialize database
    await init_db()
    
    # Close database
    await close_db()
    
    # Import after close to verify cleanup
    from tracker_service.core import db
    assert db.engine is None
    assert db.AsyncSessionLocal is None


@pytest.mark.asyncio
async def test_get_db_raises_when_not_initialized():
    """Test that get_db raises RuntimeError when database not initialized."""
    from tracker_service.core.db import get_db, close_db
    
    # Ensure database is not initialized
    await close_db()
    
    with pytest.raises(RuntimeError, match="Database not initialized"):
        async for _ in get_db():
            pass


def test_settings_configuration():
    """Test that settings are configured correctly."""
    from tracker_service.core.config import settings

    assert settings.service_name == "tracker-service"
    assert "tracker" in settings.database_url
    assert "nats://" in settings.nats_url
    assert settings.default_platform_tenant_id is not None
    assert settings.default_service_user_id is not None
