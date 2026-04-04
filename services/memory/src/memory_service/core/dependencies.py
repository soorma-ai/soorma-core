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
from fastapi import Depends

from soorma_service_common import (  # noqa: F401
  RouteAuthPolicy,
    TenantContext,
    create_get_tenant_context,
    create_get_tenanted_db,
  create_trust_guard_dependency,
    create_require_user_context_dependency,
    create_require_admin_authorization,
)
from memory_service.core.config import settings
from memory_service.core.database import get_db

# Bind memory service's get_db to the tenancy wrapper.
# This instance is used as a FastAPI dependency in all v1 route handlers.
get_tenanted_db = create_get_tenanted_db(get_db)

# Combine identity + RLS-activated session into a single bundle dependency.
get_tenant_context = create_get_tenant_context(get_tenanted_db)


require_user_tenant_context = create_require_user_context_dependency(
  get_tenant_context,
  correlation_header_name="X-Correlation-ID",
  request_header_name="X-Request-ID",
)

default_memory_route_policy = RouteAuthPolicy(
  route_id="memory.default",
  auth_required=True,
  allow_delegated_context=False,
)

require_trusted_tenant_context = create_trust_guard_dependency(
  get_tenant_context,
  default_memory_route_policy,
)


require_admin_authorization = create_require_admin_authorization(
  settings.memory_admin_api_key,
  header_name="X-Memory-Admin-Key",
)

__all__ = [
  "TenantContext",
  "get_tenant_context",
  "get_tenanted_db",
  "require_user_tenant_context",
  "default_memory_route_policy",
  "require_trusted_tenant_context",
  "require_admin_authorization",
]
