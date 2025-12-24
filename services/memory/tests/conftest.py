"""Test configuration and fixtures."""

import pytest
import asyncio
import os
from typing import AsyncGenerator
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
    """Create a test database engine."""
    # Use in-memory SQLite for testing
    # Note: pgvector is not available in SQLite, so vector tests won't work
    # For full testing, use a test PostgreSQL database
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
    """Create a test database session."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Mock environment variables for testing."""
    # Set test environment variables
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    
    # Prevent actual OpenAI API calls
    monkeypatch.setenv("TESTING", "true")
