"""FastAPI dependencies for identity service request context."""

from soorma_service_common import (
    RouteAuthPolicy,
    TenantContext,
    create_get_tenant_context,
    create_get_tenanted_db,
    create_require_admin_authorization,
    create_require_user_context_dependency,
    create_trust_guard_dependency,
)

from identity_service.core.config import settings
from identity_service.core.db import get_db

get_tenanted_db = create_get_tenanted_db(get_db)
get_tenant_context = create_get_tenant_context(get_tenanted_db)

require_user_tenant_context = create_require_user_context_dependency(
    get_tenant_context,
    correlation_header_name="X-Correlation-ID",
    request_header_name="X-Request-ID",
)

identity_default_route_policy = RouteAuthPolicy(
    route_id="identity.default",
    auth_required=True,
    allow_delegated_context=False,
)

require_trusted_tenant_context = create_trust_guard_dependency(
    get_tenant_context,
    identity_default_route_policy,
)

require_admin_authorization = create_require_admin_authorization(
    settings.identity_admin_api_key,
    header_name="X-Identity-Admin-Key",
)

__all__ = [
    "TenantContext",
    "get_tenant_context",
    "get_tenanted_db",
    "require_user_tenant_context",
    "identity_default_route_policy",
    "require_trusted_tenant_context",
    "require_admin_authorization",
]
