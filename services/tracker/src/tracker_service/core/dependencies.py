"""FastAPI dependencies for tracker tenancy and request context."""

from soorma_service_common import (
    RouteAuthPolicy,
    TenantContext,
    create_get_tenant_context,
    create_get_tenanted_db,
    create_trust_guard_dependency,
)
from tracker_service.core.db import get_db

# Bind tracker get_db to tenancy-aware DB dependency.
get_tenanted_db = create_get_tenanted_db(get_db)

# Provide bundled identity + tenanted db context for route handlers.
get_tenant_context = create_get_tenant_context(get_tenanted_db)

default_tracker_route_policy = RouteAuthPolicy(
    route_id="tracker.default",
    auth_required=True,
    allow_delegated_context=False,
)

require_trusted_tenant_context = create_trust_guard_dependency(
    get_tenant_context,
    default_tracker_route_policy,
)

__all__ = [
    "TenantContext",
    "get_tenant_context",
    "get_tenanted_db",
    "default_tracker_route_policy",
    "require_trusted_tenant_context",
]
