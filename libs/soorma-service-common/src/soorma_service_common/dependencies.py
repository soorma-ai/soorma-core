"""
FastAPI dependency functions for tenancy identity extraction and RLS activation.

These functions read identity dimensions from request.state (populated by
TenancyMiddleware) and activate PostgreSQL RLS via set_config.
"""
from typing import AsyncGenerator, Callable, Optional

from fastapi import Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def _set_config_dim(db: AsyncSession, key: str, value: str) -> None:
    """Execute a single transaction-scoped set_config call. Private helper."""
    await db.execute(
        text("SELECT set_config(:key, :value, true)"),
        {"key": key, "value": value},
    )


def get_platform_tenant_id(request: Request) -> str:
    """Read platform_tenant_id from request.state (set by TenancyMiddleware). Returns str."""
    return request.state.platform_tenant_id


def get_service_tenant_id(request: Request) -> Optional[str]:
    """Read service_tenant_id from request.state. Returns None if not set."""
    return request.state.service_tenant_id


def get_service_user_id(request: Request) -> Optional[str]:
    """Read service_user_id from request.state. Returns None if not set."""
    return request.state.service_user_id


def create_get_tenanted_db(get_db: Callable) -> Callable:
    """
    Factory: returns a FastAPI dependency function bound to the given get_db callable.

    Each consuming service calls this once at module level, binding it to its own get_db:

        from soorma_service_common import create_get_tenanted_db
        from my_service.core.database import get_db

        get_tenanted_db = create_get_tenanted_db(get_db)

    The returned function is an async generator dependency that:
      1. Reads identity from request.state
      2. Calls PostgreSQL set_config x3 (transaction-scoped) to activate RLS
      3. Yields the AsyncSession for the route handler

    Args:
        get_db: The consuming service's async generator DB session dependency.

    Returns:
        An async generator FastAPI dependency: get_tenanted_db(request, db) -> AsyncSession
    """
    async def get_tenanted_db(
        request: Request,
        db: AsyncSession = Depends(get_db),
    ) -> AsyncGenerator[AsyncSession, None]:
        """
        FastAPI dependency: activates RLS via set_config x3 before yielding the DB session.

        Reads request.state.{platform_tenant_id,service_tenant_id,service_user_id}
        (set by TenancyMiddleware) and calls:
            set_config('app.platform_tenant_id', ..., true)
            set_config('app.service_tenant_id',  ..., true)
            set_config('app.service_user_id',    ..., true)

        None values are converted to '' (empty string) — PostgreSQL set_config
        requires a string value; RLS policies treat '' as no-filter for optional dims.
        """
        platform_tenant_id: str = request.state.platform_tenant_id
        service_tenant_id: Optional[str] = request.state.service_tenant_id
        service_user_id: Optional[str] = request.state.service_user_id

        await _set_config_dim(db, "app.platform_tenant_id", platform_tenant_id)
        await _set_config_dim(db, "app.service_tenant_id", service_tenant_id or "")
        await _set_config_dim(db, "app.service_user_id", service_user_id or "")

        yield db

    return get_tenanted_db


async def set_config_for_session(
    db: AsyncSession,
    platform_tenant_id: str,
    service_tenant_id: Optional[str],
    service_user_id: Optional[str],
) -> None:
    """
    NATS-path RLS activation: same set_config logic as get_tenanted_db but
    called directly on an AsyncSession (no HTTP request object available).

    Used by NATS event subscribers where TenancyMiddleware never runs.
    Must be called before any RLS-protected query in the same DB session.

    Args:
        db: Open AsyncSession to execute set_config on.
        platform_tenant_id: Platform tenant ID (from event.platform_tenant_id).
        service_tenant_id: Service tenant ID (from event.tenant_id); None becomes ''.
        service_user_id: Service user ID (from event.user_id); None becomes ''.
    """
    await _set_config_dim(db, "app.platform_tenant_id", platform_tenant_id)
    await _set_config_dim(db, "app.service_tenant_id", service_tenant_id or "")
    await _set_config_dim(db, "app.service_user_id", service_user_id or "")
