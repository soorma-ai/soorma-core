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


async def ensure_tenant_exists(session: AsyncSession, tenant_id: str) -> None:
    """
    Ensure tenant exists in the database (lazy population).
    
    Creates the tenant on-demand if it doesn't exist, following the
    "Lazy Population" strategy from the architecture document.
    
    Args:
        session: Database session
        tenant_id: Tenant UUID
    """
    # Use INSERT ... ON CONFLICT DO NOTHING for atomic upsert
    await session.execute(
        text(f"""
            INSERT INTO tenants (id, name)
            VALUES ('{tenant_id}'::UUID, 'tenant-{tenant_id}')
            ON CONFLICT (id) DO NOTHING
        """)
    )
    await session.commit()


async def ensure_user_exists(session: AsyncSession, tenant_id: str, user_id: str) -> None:
    """
    Ensure user exists in the database (lazy population).
    
    Creates the user on-demand if it doesn't exist, following the
    "Lazy Population" strategy from the architecture document.
    Also ensures the parent tenant exists first.
    
    Args:
        session: Database session
        tenant_id: Tenant UUID
        user_id: User UUID
    """
    # First ensure tenant exists (required for foreign key)
    await ensure_tenant_exists(session, tenant_id)
    
    # Then upsert the user
    await session.execute(
        text(f"""
            INSERT INTO users (id, tenant_id, username)
            VALUES ('{user_id}'::UUID, '{tenant_id}'::UUID, 'user-{user_id}')
            ON CONFLICT (id) DO NOTHING
        """)
    )
    await session.commit()


async def set_session_context(session: AsyncSession, tenant_id: str, user_id: str) -> None:
    """
    Set PostgreSQL session variables for RLS.
    
    Also ensures the user exists via lazy population before setting session context.
    """
    # Ensure user exists (lazy population)
    await ensure_user_exists(session, tenant_id, user_id)
    
    # Set session variables for RLS
    await session.execute(
        text(f"SET \"app.current_tenant\" = '{tenant_id}'")
    )
    await session.execute(
        text(f"SET \"app.current_user\" = '{user_id}'")
    )
