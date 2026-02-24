"""Database connection and session management."""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)

from tracker_service.core.config import settings


# Database engine and session factory
engine: AsyncEngine | None = None
AsyncSessionLocal: async_sessionmaker[AsyncSession] | None = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session dependency for FastAPI endpoints.
    
    Yields:
        AsyncSession: Database session
        
    Raises:
        RuntimeError: If database not initialized
    """
    if AsyncSessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database connection and session factory.
    
    Creates async engine and session factory using settings.database_url.
    Should be called during application startup.
    """
    global engine, AsyncSessionLocal
    
    if engine is not None:
        # Already initialized
        return
    
    # Create async engine
    engine = create_async_engine(
        settings.database_url,
        echo=not settings.is_prod,  # Log SQL in non-prod
        pool_pre_ping=True,  # Verify connections before using
        pool_size=5,
        max_overflow=10,
    )
    
    # Create session factory
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    
    print(f"✓ Database initialized: {settings.database_url}")


async def close_db() -> None:
    """Close database connection and cleanup resources.
    
    Should be called during application shutdown.
    """
    global engine, AsyncSessionLocal
    
    if engine is not None:
        await engine.dispose()
        engine = None
        AsyncSessionLocal = None
        print("✓ Database connection closed")
