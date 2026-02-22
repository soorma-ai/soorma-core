"""Alembic environment configuration for Tracker Service."""

from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os
import sys

# Import Base and models from tracker service
from tracker_service.models.db import Base

# Import all models to ensure they're registered with Base.metadata
from tracker_service.models.db import PlanProgress, ActionProgress


def get_database_url() -> str:
    """Get database URL for Alembic migrations from environment."""
    # Try SYNC_DATABASE_URL first (preferred for Alembic)
    url = os.environ.get(
        "SYNC_DATABASE_URL"
    ) or os.environ.get(
        "DATABASE_URL", "postgresql+psycopg2://soorma:soorma@localhost:5432/tracker"
    )
    
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
    """Run migrations in 'offline' mode."""
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
    """Run migrations in 'online' mode."""
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
