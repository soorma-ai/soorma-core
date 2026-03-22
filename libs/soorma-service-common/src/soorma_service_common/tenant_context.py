"""
TenantContext dataclass and dependency factory for bundle injection.

Combining all three identity dimensions with an RLS-activated DB session
into a single Depends() reduces boilerplate across Memory and Tracker routes.
"""
from dataclasses import dataclass
from typing import Callable, Optional

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class TenantContext:
    """
    Convenience bundle: all three identity dimensions plus an RLS-activated DB session.

    Invariant: db is always an RLS-activated AsyncSession (set_config already called
    by the underlying get_tenanted_db dependency).  Route handlers receive a fully
    ready context with a single Depends(get_tenant_context) instead of four.

    Attributes:
        platform_tenant_id: The Soorma platform tenant (always present, never blank).
        service_tenant_id: Optional per-service tenant scope (None if not provided).
        service_user_id: Optional per-service user scope (None if not provided).
        db: AsyncSession with PostgreSQL RLS session variables already set.
    """

    platform_tenant_id: str
    service_tenant_id: Optional[str]
    service_user_id: Optional[str]
    db: AsyncSession


def create_get_tenant_context(get_tenanted_db: Callable) -> Callable:
    """
    Factory: returns a FastAPI dependency that yields a TenantContext.

    Each consuming service calls this once, binding it to its own get_tenanted_db:

        from soorma_service_common import create_get_tenant_context
        from my_service.core.dependencies import get_tenanted_db

        get_tenant_context = create_get_tenant_context(get_tenanted_db)

    The returned dependency reads identity from request.state and combines it
    with the RLS-activated session from get_tenanted_db.

    Args:
        get_tenanted_db: The consuming service's bound get_tenanted_db dependency
                         (itself produced by create_get_tenanted_db).

    Returns:
        A FastAPI dependency: get_tenant_context(request, db) -> TenantContext
    """
    async def get_tenant_context(
        request: Request,
        db: AsyncSession = Depends(get_tenanted_db),
    ) -> TenantContext:
        """
        FastAPI dependency: combines request.state identity values with an
        RLS-activated DB session into a single TenantContext bundle.

        Returns:
            TenantContext with all three identity dimensions and db already
            configured with set_config (via get_tenanted_db).
        """
        return TenantContext(
            platform_tenant_id=request.state.platform_tenant_id,
            service_tenant_id=request.state.service_tenant_id,
            service_user_id=request.state.service_user_id,
            db=db,
        )

    return get_tenant_context
