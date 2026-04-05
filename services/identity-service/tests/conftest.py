"""Pytest fixtures for identity-service tests."""

from fastapi.testclient import TestClient
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from identity_service.core.db import Base
from identity_service.main import app
from identity_service import models  # noqa: F401  # Ensures ORM models are imported.


@pytest.fixture
def client() -> TestClient:
    """Create test client for FastAPI app."""
    return TestClient(app)


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    """Create isolated in-memory SQLite session for persistence tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session

    await engine.dispose()
