"""FastAPI dependencies for identity service request context."""

from fastapi import Header, HTTPException, status

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
from identity_service.services.admin_api_keys import TenantAdminApiKeyService

get_tenanted_db = create_get_tenanted_db(get_db)
get_tenant_context = create_get_tenant_context(get_tenanted_db)

require_user_tenant_context = create_require_user_context_dependency(
    get_tenant_context,
    correlation_header_name="X-Correlation-ID",
    request_header_name="X-Request-ID",
)

tenant_admin_api_key_service = TenantAdminApiKeyService(
    settings.identity_tenant_admin_api_key_secret,
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

require_superuser_admin_authorization = create_require_admin_authorization(
    settings.identity_superuser_api_key,
    header_name="X-Identity-Admin-Key",
    error_detail="Superuser authorization required",
)


def require_tenant_admin_authorization(
    provided_api_key: str | None = Header(default=None, alias="X-Identity-Admin-Key"),
    platform_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
) -> str:
    """Validate tenant-bound admin authorization and require explicit tenant scope."""
    resolved_platform_tenant_id = str(platform_tenant_id or "").strip()
    if not resolved_platform_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Tenant-ID header is required for tenant admin authorization.",
        )

    if not tenant_admin_api_key_service.validate_api_key(
        resolved_platform_tenant_id,
        provided_api_key,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant admin authorization required",
        )

    return resolved_platform_tenant_id

__all__ = [
    "TenantContext",
    "get_tenant_context",
    "get_tenanted_db",
    "require_user_tenant_context",
    "identity_default_route_policy",
    "require_trusted_tenant_context",
    "require_superuser_admin_authorization",
    "require_tenant_admin_authorization",
    "tenant_admin_api_key_service",
]
