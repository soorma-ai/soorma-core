"""
Test configuration and fixtures.
"""
import pytest
import os
import asyncio
from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from fastapi.testclient import TestClient

# Sentinel platform tenant ID used by all tests (matches DEFAULT_PLATFORM_TENANT_ID)
TEST_TENANT_ID = "spt_00000000-0000-0000-0000-000000000000"

# Use a test-specific SQLite database file
TEST_DB_FILE = "test_registry.db"
TEST_DATABASE_URL = f"sqlite+aiosqlite:///./{TEST_DB_FILE}"

# Set the environment variable BEFORE importing the app
# This ensures the app uses the test database from the start
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault("SOORMA_AUTH_JWT_SECRET", "dev-identity-signing-key")

# Now import after setting environment variables
from registry_service.main import app
from registry_service.core.database import engine, AsyncSessionLocal
from registry_service.api.dependencies import get_tenanted_db


async def _test_get_tenanted_db():
    """SQLite-safe override: yields a plain session without calling set_config."""
    async with AsyncSessionLocal() as session:
        yield session


# Override get_tenanted_db globally — SQLite does not support PostgreSQL set_config.
app.dependency_overrides[get_tenanted_db] = _test_get_tenanted_db
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
    Create a test client with authenticated bearer headers.
    """
    with TestClient(app, headers=build_auth_headers(TEST_TENANT_ID)) as test_client:
        yield test_client


def build_auth_headers(
    platform_tenant_id: str = TEST_TENANT_ID,
    service_tenant_id: str = "st_test-tenant",
    service_user_id: str = "su_test-user",
    principal_id: str = "registry-test-user",
) -> dict[str, str]:
    """Build JWT bearer headers for registry-service tests."""
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": principal_id,
            "platform_tenant_id": platform_tenant_id,
            "service_tenant_id": service_tenant_id,
            "service_user_id": service_user_id,
            "principal_id": principal_id,
            "principal_type": "service",
            "roles": ["service"],
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=1)).timestamp()),
        },
        os.environ["SOORMA_AUTH_JWT_SECRET"],
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}

