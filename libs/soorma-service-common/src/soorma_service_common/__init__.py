"""
soorma-service-common — Shared FastAPI/Starlette infrastructure for Soorma backend services.
"""

from .middleware import TenancyMiddleware
from .dependencies import (
    get_platform_tenant_id,
    get_service_tenant_id,
    get_service_user_id,
    require_user_context,
    validate_delegated_context_structure,
    default_trust_policy_hook,
    evaluate_trust_policy,
    create_trust_guard_dependency,
    create_require_user_context_dependency,
    create_require_admin_authorization,
    create_get_tenanted_db,
    set_config_for_session,
)
from .tenant_context import (
    TenantContext,
    CanonicalAuthContext,
    RouteAuthPolicy,
    TrustDecision,
    to_canonical_auth_context,
    create_get_tenant_context,
)
from .deletion import PlatformTenantDataDeletion

__all__ = [
    # Middleware
    "TenancyMiddleware",
    # Dependency functions
    "get_platform_tenant_id",
    "get_service_tenant_id",
    "get_service_user_id",
    "require_user_context",
    "validate_delegated_context_structure",
    "default_trust_policy_hook",
    "evaluate_trust_policy",
    "create_trust_guard_dependency",
    "create_require_user_context_dependency",
    "create_require_admin_authorization",
    "create_get_tenanted_db",
    "set_config_for_session",
    # Identity bundle
    "TenantContext",
    "CanonicalAuthContext",
    "RouteAuthPolicy",
    "TrustDecision",
    "to_canonical_auth_context",
    "create_get_tenant_context",
    # GDPR interface
    "PlatformTenantDataDeletion",
]
