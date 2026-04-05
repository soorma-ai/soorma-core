"""Alembic environment for identity-service migrations."""

from logging.config import fileConfig
import os
import sys
import importlib.util

from alembic import context
from sqlalchemy import engine_from_config, pool

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
SRC_ROOT = os.path.join(PROJECT_ROOT, "src")
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)


def _load_module(module_name: str, path: str):
    """Load module from file path for Alembic runtime imports."""
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


db_module = _load_module(
    "identity_service_db",
    os.path.join(PROJECT_ROOT, "src", "identity_service", "core", "db.py"),
)
Base = db_module.Base

# Import models so metadata is fully registered before autogenerate/use.
_load_module(
    "identity_service_domain",
    os.path.join(PROJECT_ROOT, "src", "identity_service", "models", "domain.py"),
)


def get_database_url() -> str:
    """Resolve sync database URL for Alembic."""
    url = os.environ.get("SYNC_DATABASE_URL") or os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg2://soorma:soorma@localhost:5432/identity",
    )
    if "postgresql+asyncpg" in url:
        url = url.replace("postgresql+asyncpg", "postgresql+psycopg2")
    elif url.startswith("postgresql://") and "psycopg2" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg2://")
    return url


config = context.config
config.set_main_option("sqlalchemy.url", get_database_url().replace("%", "%%"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in offline mode."""
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
    """Run migrations in online mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
