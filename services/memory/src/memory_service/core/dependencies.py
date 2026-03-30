"""FastAPI dependencies for authentication and request context.

Memory Service Authentication Model (v0.7.x):
  platform_tenant_id is extracted from the X-Tenant-ID header by TenancyMiddleware
  (from soorma_service_common) and stored on request.state. get_tenant_context bundles
  platform_tenant_id, service_tenant_id, service_user_id with a tenanted DB session.

  get_tenanted_db wraps the service's own get_db session factory:
    - Reads identity from request.state (set by TenancyMiddleware)
    - Calls PostgreSQL set_config x3 to activate RLS for the transaction
    - Yields the AsyncSession

  v0.8.0+: will be replaced with API Key / machine token validation.
"""
from fastapi import Depends, Header, HTTPException, status

from soorma_service_common import (  # noqa: F401
    TenantContext,
    create_get_tenant_context,
    create_get_tenanted_db,
  require_user_context,
)
from memory_service.core.config import settings
from memory_service.core.database import get_db

# Bind memory service's get_db to the tenancy wrapper.
# This instance is used as a FastAPI dependency in all v1 route handlers.
get_tenanted_db = create_get_tenanted_db(get_db)

# Combine identity + RLS-activated session into a single bundle dependency.
get_tenant_context = create_get_tenant_context(get_tenanted_db)


def require_user_tenant_context(
  context: TenantContext = Depends(get_tenant_context),
) -> TenantContext:
  """Enforce user-scoped identity dimensions and return validated context."""
  return require_user_context(context)


def require_admin_authorization(
  admin_key: str | None = Header(default=None, alias="X-Memory-Admin-Key"),
) -> None:
  """Require explicit admin key for privileged admin endpoints."""
  if admin_key != settings.memory_admin_api_key:
    raise HTTPException(
      status_code=status.HTTP_403_FORBIDDEN,
      detail="Admin authorization required",
    )

__all__ = [
  "TenantContext",
  "get_tenant_context",
  "get_tenanted_db",
  "require_user_tenant_context",
  "require_admin_authorization",
]
