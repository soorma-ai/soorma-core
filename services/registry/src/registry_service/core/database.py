"""
Database configuration and session management.
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.engine import URL
from sqlalchemy.pool import NullPool

from .config import settings, check_required_settings
from ..models import Base


def create_db_url(driver: str) -> str:
    """
    Dynamically creates a database URL based on the environment and driver.
    - For local testing, uses SQLite or the configured DATABASE_URL.
    - For production, uses Cloud SQL Unix socket with PostgreSQL.
    
    Args:
        driver: Database driver (e.g., "postgresql+asyncpg", "postgresql+psycopg2", "sqlite+aiosqlite")
    
    Returns:
        Database connection URL string
    """
    if settings.IS_LOCAL_TESTING:
        # For local testing, return the appropriate pre-configured URL
        if "sqlite" in driver:
            return settings.SYNC_DATABASE_URL if "sqlite:" == driver[:7] else settings.DATABASE_URL
        else:
            # If using PostgreSQL locally, use the configured URL
            return settings.SYNC_DATABASE_URL if "psycopg2" in driver else settings.DATABASE_URL
    else:
        # Ensure all necessary environment variables are set for Cloud SQL
        check_required_settings(["DB_INSTANCE_CONNECTION_NAME", "DB_USER", "DB_NAME"])

        # For production, build the URL from components
        def get_db_password():
            try:
                with open(settings.DB_PASS_PATH, 'r') as f:
                    return f.read().strip()
            except IOError:
                raise ValueError(f"Secret at {settings.DB_PASS_PATH} not found.")

        # The parameter name for the socket depends on the driver
        socket_dir = f"/cloudsql/{settings.DB_INSTANCE_CONNECTION_NAME}"
        query_params = {"host": socket_dir}
        
        # The returned URL object can be rendered as a string
        return URL.create(
            drivername=driver,
            username=settings.DB_USER,
            password=get_db_password(),
            database=settings.DB_NAME,
            query=query_params,
        ).render_as_string(hide_password=False)


def create_db_engine():
    """
    Creates a SQLAlchemy async engine based on the environment.
    Uses SQLite for local testing and PostgreSQL for production.
    """
    # Use SQLite for local testing, PostgreSQL for production
    if settings.IS_LOCAL_TESTING:
        driver = "sqlite+aiosqlite"
    else:
        driver = "postgresql+asyncpg"
    
    return create_async_engine(
        create_db_url(driver=driver),
        poolclass=NullPool if not settings.IS_LOCAL_TESTING else None,
        future=True,
        echo=False  # Set to True for SQL query logging
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
