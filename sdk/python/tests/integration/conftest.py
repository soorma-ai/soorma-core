"""Shared fixtures for in-process integration tests.

Environment variables MUST be set at module level, before any import of
registry_service, so that SQLAlchemy picks up the test DATABASE_URL when
the module-level ``engine`` is created inside registry_service.core.database.

All tests in this package use:
  - An isolated SQLite database written to /tmp/
  - httpx.ASGITransport to drive the Registry ASGI app in-process
  - No NATS, no docker, no external services
"""

import asyncio
import os
from typing import Generator

import httpx
import pytest
from sqlalchemy import create_engine as _sync_create_engine, text

# ---------------------------------------------------------------------------
# 1. Bootstrap env vars BEFORE any service module is imported
# ---------------------------------------------------------------------------

_TEST_DB = "/tmp/soorma_integration_test.db"

os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{_TEST_DB}")
os.environ.setdefault("SYNC_DATABASE_URL", f"sqlite:///{_TEST_DB}")
os.environ.setdefault("IS_LOCAL_TESTING", "true")
os.environ.setdefault("SOORMA_DEVELOPER_TENANT_ID", "00000000-0000-0000-0000-000000000001")

# ---------------------------------------------------------------------------
# 2. Service imports — safe now that env vars are in place
# ---------------------------------------------------------------------------

from registry_service.core.cache import (  # noqa: E402
    invalidate_agent_cache,
    invalidate_event_cache,
)
from registry_service.core.database import engine as _async_engine  # noqa: E402
from registry_service.main import app as _registry_app  # noqa: E402
from registry_service.models import Base  # noqa: E402
from soorma.registry.client import RegistryClient  # noqa: E402

# ---------------------------------------------------------------------------
# 3. Well-known tenant IDs for isolation tests
# ---------------------------------------------------------------------------

TENANT_A = "00000000-0000-0000-0000-000000000001"
TENANT_B = "00000000-0000-0000-0000-000000000002"

# ---------------------------------------------------------------------------
# 4. Session-scoped fixture: create the SQLite DB once per session
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session", autouse=True)
def _create_integration_db() -> Generator[None, None, None]:
    """Create the SQLite database tables once per test session.

    Removes any stale DB file from a previous run first so each session
    starts from a known-clean state.  Disposes the async engine and removes
    the file again on teardown.
    """
    if os.path.exists(_TEST_DB):
        os.remove(_TEST_DB)

    sync_engine = _sync_create_engine(f"sqlite:///{_TEST_DB}")
    Base.metadata.create_all(sync_engine)
    sync_engine.dispose()

    yield

    # Teardown: close async connections, then delete the file
    asyncio.run(_async_engine.dispose())
    if os.path.exists(_TEST_DB):
        os.remove(_TEST_DB)


# ---------------------------------------------------------------------------
# 5. Function-scoped fixture: truncate all tables between tests
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clean_tables() -> Generator[None, None, None]:
    """Truncate all registry tables and invalidate caches before each test.

    Using DELETE rather than DROP/CREATE keeps the fixture fast (no DDL
    round-trip).  Caches are also invalidated so stale in-memory state from
    a previous test cannot leak into the next one.
    """
    sync_engine = _sync_create_engine(f"sqlite:///{_TEST_DB}")
    with sync_engine.connect() as conn:
        # Delete in dependency order so FK constraints don't fire
        conn.execute(text("DELETE FROM agent_capabilities"))
        conn.execute(text("DELETE FROM agents"))
        conn.execute(text("DELETE FROM payload_schemas"))
        conn.execute(text("DELETE FROM events"))
        conn.commit()
    sync_engine.dispose()

    invalidate_agent_cache()
    invalidate_event_cache()


# ---------------------------------------------------------------------------
# 6. Factory: create a RegistryClient backed by the in-process registry app
# ---------------------------------------------------------------------------


def make_registry_client(tenant_id: str = TENANT_A) -> RegistryClient:
    """Return a RegistryClient that drives the in-process Registry via ASGITransport.

    The underlying httpx.AsyncClient is replaced with one that routes all
    requests directly through the ASGI app (no TCP socket needed).  The
    auth headers are also overridden so each test can choose its tenant.

    Args:
        tenant_id: X-Tenant-ID header value to use for all requests.

    Returns:
        Configured RegistryClient ready for async use.
    """
    client = RegistryClient(base_url="http://test-registry")
    # Swap the default HTTP transport for an in-process ASGI transport
    client._client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=_registry_app),
        base_url="http://test-registry",
    )
    # Ensure the correct tenant header is sent on every request
    client._auth_headers = {"X-Tenant-ID": tenant_id}
    return client
