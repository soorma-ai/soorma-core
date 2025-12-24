"""Database connection and session management."""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text

from memory_service.core.config import settings

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=not settings.is_prod,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for models
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session dependency."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def set_session_context(session: AsyncSession, tenant_id: str, user_id: str) -> None:
    """Set PostgreSQL session variables for RLS."""
    await session.execute(
        text(f"SET app.current_tenant = '{tenant_id}'")
    )
    await session.execute(
        text(f"SET app.current_user = '{user_id}'")
    )
