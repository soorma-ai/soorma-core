"""
API dependencies for authentication and request context.

Registry Service Authentication Model (v0.7.x):
  platform_tenant_id is extracted from the X-Tenant-ID header by TenancyMiddleware
  and stored on request.state. get_platform_tenant_id reads it as a plain str.

  get_tenanted_db wraps the service's own get_db session factory:
    - Reads identity from request.state
    - Calls PostgreSQL set_config x3 to activate RLS for the session
    - Yields the AsyncSession

  v0.8.0+: will be replaced with API Key / machine token validation.
"""
from soorma_service_common import create_get_tenanted_db, get_platform_tenant_id  # noqa: F401
from ..core.database import get_db

# Bind the registry's get_db to the tenancy wrapper.
# This instance is used as a FastAPI dependency in all v1 route handlers.
get_tenanted_db = create_get_tenanted_db(get_db)

__all__ = ["get_platform_tenant_id", "get_tenanted_db"]

