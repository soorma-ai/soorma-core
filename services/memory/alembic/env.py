
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os
import sys
import importlib

# Try to import Base from installed package first (Docker/production)
# Fall back to source file import (local development)
try:
    from memory_service.core.database import Base
except Exception:
    # Add the project src to the path for local development
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "src"))
    
    # Import directly from file to avoid triggering __init__.py imports
    import importlib.util
    database_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
        "src", "memory_service", "core", "database.py"
    )
    spec = importlib.util.spec_from_file_location("database", database_path)
    database = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(database)
    Base = database.Base

# Import models to ensure they're registered with Base
try:
    from memory_service.models import memory  # noqa
except Exception:
    # Local development - import directly
    models_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
        "src", "memory_service", "models", "memory.py"
    )
    spec = importlib.util.spec_from_file_location("memory", models_path)
    memory = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(memory)

# Get database URL directly from environment
def get_database_url() -> str:
    """Get database URL for Alembic migrations from environment."""
    # Try SYNC_DATABASE_URL first (preferred for Alembic)
    url = os.environ.get("SYNC_DATABASE_URL") or os.environ.get("DATABASE_URL", "postgresql+psycopg2://soorma:soorma@localhost:5432/memory")
    
    # Replace async drivers with sync drivers for Alembic
    if "postgresql+asyncpg" in url:
        url = url.replace("postgresql+asyncpg", "postgresql+psycopg2")
    elif url.startswith("postgresql://") and "psycopg2" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg2://")
    
    return url

# this is the Alembic Config object
config = context.config

# Set the sqlalchemy.url in the config object
config.set_main_option('sqlalchemy.url', get_database_url().replace('%', '%%'))

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
