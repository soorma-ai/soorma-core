from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os
import sys

# Try to import Base from installed package first (Docker/production)
# Fall back to source file import (local development)
try:
    from registry_service.models.base import Base
except Exception:
    # Add the project src to the path for local development
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "src"))
    
    # Import directly from file to avoid triggering __init__.py imports
    import importlib.util
    models_base_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
        "src", "registry_service", "models", "base.py"
    )
    spec = importlib.util.spec_from_file_location("models_base", models_base_path)
    models_base = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(models_base)
    Base = models_base.Base

# Get database URL directly from environment (avoid importing settings which triggers database.py)
def get_database_url() -> str:
    """Get database URL for Alembic migrations from environment."""
    # Try SYNC_DATABASE_URL first (preferred for Alembic)
    url = os.environ.get("SYNC_DATABASE_URL") or os.environ.get("DATABASE_URL", "sqlite:///./registry.db")
    
    # Replace async drivers with sync drivers for Alembic
    if "sqlite+aiosqlite" in url:
        url = url.replace("sqlite+aiosqlite", "sqlite")
    elif "postgresql+asyncpg" in url:
        url = url.replace("postgresql+asyncpg", "postgresql+psycopg2")
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg2://")
    
    return url

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Set the sqlalchemy.url in the config object
config.set_main_option('sqlalchemy.url', get_database_url().replace('%', '%%'))

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


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
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
