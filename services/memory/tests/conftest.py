"""Test configuration and fixtures."""

import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator

import jwt
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from memory_service.core.database import Base
from memory_service.models import memory  # noqa - ensure models are loaded


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create a test database engine using in-memory SQLite.

    Note: pgvector operations (cosine_distance etc.) are not available in SQLite —
    semantic search tests mock the embedding service instead.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session backed by in-memory SQLite."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()


# Standard test identity constants (opaque strings, not UUIDs)
TEST_PLATFORM_TENANT_ID = "spt_00000000-0000-0000-0000-000000000000"
TEST_SERVICE_TENANT_ID = "st_test-tenant"
TEST_SERVICE_USER_ID = "su_test-user"


@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Mock environment variables for testing."""
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.setenv("SOORMA_AUTH_JWT_SECRET", "dev-identity-signing-key")


def build_auth_headers(
    platform_tenant_id: str = TEST_PLATFORM_TENANT_ID,
    service_tenant_id: str = TEST_SERVICE_TENANT_ID,
    service_user_id: str = TEST_SERVICE_USER_ID,
    principal_id: str = TEST_SERVICE_USER_ID,
) -> dict[str, str]:
    """Build JWT bearer headers for memory-service tests."""
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
        "dev-identity-signing-key",
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}

