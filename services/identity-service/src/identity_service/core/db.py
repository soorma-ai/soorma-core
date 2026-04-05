"""Database connection and session management."""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from identity_service.core.config import settings


engine: AsyncEngine | None = None
AsyncSessionLocal: async_sessionmaker[AsyncSession] | None = None

Base = declarative_base()


async def init_db() -> None:
    """Initialize database engine and session factory."""
    global engine, AsyncSessionLocal
    if engine is not None:
        return

    # SQLite engines used by tests do not support pool_size/max_overflow.
    if settings.database_url.startswith("sqlite"):
        engine = create_async_engine(
            settings.database_url,
            echo=not settings.is_prod,
            pool_pre_ping=True,
        )
    else:
        engine = create_async_engine(
            settings.database_url,
            echo=not settings.is_prod,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


async def close_db() -> None:
    """Dispose database resources."""
    global engine, AsyncSessionLocal
    if engine is None:
        return
    await engine.dispose()
    engine = None
    AsyncSessionLocal = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session dependency."""
    if AsyncSessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
