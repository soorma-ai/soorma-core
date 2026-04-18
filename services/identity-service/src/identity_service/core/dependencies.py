"""FastAPI dependencies for identity service request context."""

from fastapi import Depends, Header, HTTPException, Request, status

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
from identity_service.services.admin_api_keys import tenant_admin_api_key_service

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

require_superuser_admin_authorization = create_require_admin_authorization(
    settings.identity_superuser_api_key,
    header_name="X-Identity-Admin-Key",
    error_detail="Superuser authorization required",
)


async def require_tenant_admin_authorization(
    request: Request,
    context: TenantContext = Depends(get_tenant_context),
) -> str:
    """Validate tenant-bound admin authorization and require explicit tenant scope."""
    resolved_platform_tenant_id = str(request.headers.get("X-Tenant-ID") or "").strip()
    if not resolved_platform_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Tenant-ID header is required for tenant admin authorization.",
        )

    if not await tenant_admin_api_key_service.validate_api_key(
        context.db,
        resolved_platform_tenant_id,
        request.headers.get("X-Identity-Admin-Key"),
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
