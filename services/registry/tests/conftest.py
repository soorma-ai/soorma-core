"""
Test configuration and fixtures.
"""
import pytest
import os
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from fastapi.testclient import TestClient

# Use a test-specific SQLite database file
TEST_DB_FILE = "test_registry.db"
TEST_DATABASE_URL = f"sqlite+aiosqlite:///./{TEST_DB_FILE}"

# Set the environment variable BEFORE importing the app
# This ensures the app uses the test database from the start
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["SYNC_DATABASE_URL"] = f"sqlite:///./{TEST_DB_FILE}"
os.environ["IS_LOCAL_TESTING"] = "true"

# Now import after setting environment variables
from registry_service.main import app
from registry_service.core.database import get_db, engine, AsyncSessionLocal
from registry_service.core.cache import invalidate_agent_cache, invalidate_event_cache
from registry_service.models import Base


@pytest.fixture(scope="function", autouse=True)
def setup_test_db():
    """Set up and tear down test database for each test."""
    # Clear caches before each test
    invalidate_agent_cache()
    invalidate_event_cache()
    
    # Remove existing test database
    if os.path.exists(TEST_DB_FILE):
        os.remove(TEST_DB_FILE)
    
    # Create tables using a sync approach to ensure file is writable
    async def create_tables():
        # Import here to ensure we use the test database URL
        from sqlalchemy import create_engine as sync_create_engine
        sync_engine = sync_create_engine(f"sqlite:///./{TEST_DB_FILE}")
        Base.metadata.create_all(sync_engine)
        sync_engine.dispose()
    
    asyncio.run(create_tables())
    
    yield
    
    # Dispose the async engine before cleaning up
    async def cleanup():
        await engine.dispose()
    
    asyncio.run(cleanup())
    
    # Clean up after test
    if os.path.exists(TEST_DB_FILE):
        os.remove(TEST_DB_FILE)


@pytest.fixture
def client():
    """
    Create a test client.
    The app already uses the test database via environment variables.
    """
    # Create test client
    with TestClient(app) as test_client:
        yield test_client
