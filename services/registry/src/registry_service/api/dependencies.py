"""
API dependencies for authentication and request context.

Registry Service Authentication Model (v0.8.x):
  platform_tenant_id is extracted from validated bearer-token identity by
  TenancyMiddleware and stored on request.state. get_platform_tenant_id reads it
  as a plain str.

  get_tenanted_db wraps the service's own get_db session factory:
    - Reads identity from request.state
    - Calls PostgreSQL set_config x3 to activate RLS for the session
    - Yields the AsyncSession

  Future hardening may add selected API-key control-plane flows, but bearer-
  authenticated machine and developer principals are the current runtime model.
"""
from soorma_service_common import (  # noqa: F401
  RouteAuthPolicy,
  create_get_tenanted_db,
  get_platform_tenant_id,
)
from ..core.database import get_db

# Bind the registry's get_db to the tenancy wrapper.
# This instance is used as a FastAPI dependency in all v1 route handlers.
get_tenanted_db = create_get_tenanted_db(get_db)

default_registry_route_policy = RouteAuthPolicy(
  route_id="registry.default",
  auth_required=True,
  allow_delegated_context=False,
)

__all__ = [
  "get_platform_tenant_id",
  "get_tenanted_db",
  "default_registry_route_policy",
]

