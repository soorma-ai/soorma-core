"""
Database configuration and session management.
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from .config import settings
from ..models import Base


def create_db_engine():
    """
    Creates a SQLAlchemy async engine using DATABASE_URL from settings.
    Uses NullPool so every request gets a fresh connection — safe for both
    PostgreSQL and the SQLite test override.
    """
    return create_async_engine(
        settings.DATABASE_URL,
        poolclass=NullPool,
        future=True,
        echo=False,
    )


# Create the engine when the module is loaded
engine = create_db_engine()

# Create a configured "Session" class
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=True,
    autocommit=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency to provide a database session per request.
    Yields a session and ensures it's closed after the request is finished.
    
    Usage:
        @app.get("/items/{item_id}")
        async def read_item(item_id: int, db: AsyncSession = Depends(get_db)):
            return await crud.get_item(db, item_id)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """
    Initialize the database by creating all tables.
    Only use this for local development/testing.
    In production, use Alembic migrations.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_db():
    """
    Drop all database tables.
    Only use this for testing.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
