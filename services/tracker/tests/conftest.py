"""Pytest configuration and fixtures for tracker service tests."""

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from tracker_service.models.db import Base
from tracker_service.core.db import get_db
from tracker_service.main import app


# Test database URL (in-memory SQLite for fast tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="function")
async def db_engine():
    """Create async database engine for testing."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(db_engine):
    """Create async database session for testing."""
    async_session_maker = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session_maker() as session:
        yield session


@pytest.fixture(scope="function")
def override_get_db(db_session):
    """Override the get_db dependency in FastAPI app."""
    async def _get_test_db():
        yield db_session
    
    app.dependency_overrides[get_db] = _get_test_db
    yield
    app.dependency_overrides.clear()
