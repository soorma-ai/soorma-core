"""
FastAPI dependency functions for tenancy identity extraction and RLS activation.

These functions read identity dimensions from request.state (populated by
TenancyMiddleware) and activate PostgreSQL RLS via set_config.
"""
import logging
from typing import AsyncGenerator, Callable, Optional

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .tenant_context import (
    CanonicalAuthContext,
    RouteAuthPolicy,
    TenantContext,
    TrustDecision,
    to_canonical_auth_context,
)


LOGGER = logging.getLogger(__name__)

TENANT_IDENTITY_REQUIRED_MESSAGE = "Missing required tenant identity context"
USER_IDENTITY_REQUIRED_MESSAGE = "Missing required user identity context"
BOTH_IDENTITIES_REQUIRED_MESSAGE = (
    "Missing required tenant and user identity context"
)
INVALID_DELEGATED_CONTEXT_MESSAGE = "Invalid delegated identity context"


def _is_blank(value: Optional[str]) -> bool:
    """Return True when value is absent or whitespace-only."""
    return value is None or value.strip() == ""


def _log_identity_validation_failure(
    platform_tenant_id: str,
    failure_reason: str,
    correlation_id: Optional[str] = None,
    request_id: Optional[str] = None,
) -> None:
    """Emit safe structured warning logs without service-identity dimensions."""
    extra = {
        "event_name": "identity_validation_failed",
        "severity": "warning",
        "platform_tenant_id": platform_tenant_id,
        "failure_reason": failure_reason,
    }
    if correlation_id:
        extra["correlation_id"] = correlation_id
    if request_id:
        extra["request_id"] = request_id

    LOGGER.warning(
        "identity_validation_failed",
        extra=extra,
    )


def require_user_context(
    context: TenantContext,
    *,
    correlation_id: Optional[str] = None,
    request_id: Optional[str] = None,
) -> TenantContext:
    """Validate service-tenant and service-user context for user-scoped operations.

    Args:
        context: Resolved tenant context containing platform, service-tenant,
            and service-user identity dimensions.

    Returns:
        The same ``TenantContext`` object unchanged when validation passes.

    Raises:
        HTTPException: Raised with status ``400`` when identity context is
            missing or blank.
    """
    missing_service_tenant = _is_blank(context.service_tenant_id)
    missing_service_user = _is_blank(context.service_user_id)

    if not missing_service_tenant and not missing_service_user:
        return context

    if missing_service_tenant and missing_service_user:
        failure_reason = "missing_service_tenant_id,missing_service_user_id"
        detail = BOTH_IDENTITIES_REQUIRED_MESSAGE
    elif missing_service_tenant:
        failure_reason = "missing_service_tenant_id"
        detail = TENANT_IDENTITY_REQUIRED_MESSAGE
    else:
        failure_reason = "missing_service_user_id"
        detail = USER_IDENTITY_REQUIRED_MESSAGE

    _log_identity_validation_failure(
        platform_tenant_id=context.platform_tenant_id,
        failure_reason=failure_reason,
        correlation_id=correlation_id,
        request_id=request_id,
    )
    raise HTTPException(status_code=400, detail=detail)


def create_require_admin_authorization(
    expected_api_key: str,
    *,
    header_name: str = "X-Admin-Key",
    error_detail: str = "Admin authorization required",
) -> Callable[[], None]:
    """Create a reusable FastAPI dependency for admin authorization checks.

    Args:
        expected_api_key: API key value required for admin access.
        header_name: Header alias used to read the provided API key.
        error_detail: Error message returned when authorization fails.

    Returns:
        A FastAPI dependency function that raises HTTP 403 on mismatch.
    """

    def require_admin_authorization(
        provided_api_key: Optional[str] = Header(default=None, alias=header_name),
    ) -> None:
        """Validate admin API key from request header."""
        if provided_api_key != expected_api_key:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=error_detail,
            )

    return require_admin_authorization


def create_require_user_context_dependency(
    get_tenant_context: Callable,
    *,
    correlation_header_name: str = "X-Correlation-ID",
    request_header_name: str = "X-Request-ID",
) -> Callable:
    """Create a reusable FastAPI dependency for user-context validation.

    This adapter centralizes request-header extraction for correlation/request IDs
    and delegates the core validation logic to ``require_user_context``.

    Args:
        get_tenant_context: Bound tenant-context dependency for the service.
        correlation_header_name: Request header carrying correlation identifier.
        request_header_name: Request header carrying request identifier.

    Returns:
        A FastAPI dependency function that returns validated ``TenantContext``.
    """

    def require_user_tenant_context(
        request: Request,
        context: TenantContext = Depends(get_tenant_context),
    ) -> TenantContext:
        """Validate user context and include optional request identifiers in logs."""
        return require_user_context(
            context,
            correlation_id=request.headers.get(correlation_header_name),
            request_id=request.headers.get(request_header_name),
        )

    return require_user_tenant_context


TrustPolicyHook = Callable[[CanonicalAuthContext, RouteAuthPolicy], TrustDecision]


def validate_delegated_context_structure(context: CanonicalAuthContext) -> None:
    """Validate delegated tuple structure for canonical context.

    Delegated context is valid when both service_tenant_id and service_user_id are
    present and non-blank, or when both are absent.
    """
    tenant_present = not _is_blank(context.service_tenant_id)
    user_present = not _is_blank(context.service_user_id)
    if tenant_present == user_present:
        return
    raise HTTPException(status_code=401, detail=INVALID_DELEGATED_CONTEXT_MESSAGE)


def default_trust_policy_hook(
    context: CanonicalAuthContext,
    policy: RouteAuthPolicy,
) -> TrustDecision:
    """Default trust-policy decision for coexistence phase.

    - Header-based/internal flows are trusted by default.
    - JWT delegated flows require route policy to allow delegated context.
    - Optional issuer allowlist is enforced when configured.
    """
    delegated = bool(context.delegated_claims_present) and (
        (context.auth_source or "").strip().lower() == "jwt"
    )
    source = (context.auth_source or "legacy-header").strip().lower()

    if delegated and not policy.allow_delegated_context:
        return TrustDecision(
            allowed=False,
            provenance="denied",
            reason="delegated_context_not_allowed",
            policy_id=policy.route_id,
        )

    if delegated and policy.allowed_issuers:
        issuer = (context.issuer or "").strip()
        if issuer not in policy.allowed_issuers:
            return TrustDecision(
                allowed=False,
                provenance="denied",
                reason="issuer_not_allowed",
                policy_id=policy.route_id,
            )

    flow = "delegated_issuer" if source == "jwt" and delegated else "internal_agent"
    if policy.allowed_flows and flow not in policy.allowed_flows:
        return TrustDecision(
            allowed=False,
            provenance="denied",
            reason="flow_not_allowed",
            policy_id=policy.route_id,
        )

    provenance = "trusted_delegated" if flow == "delegated_issuer" else "trusted_internal"
    return TrustDecision(
        allowed=True,
        provenance=provenance,
        reason="allowed",
        policy_id=policy.route_id,
    )


def evaluate_trust_policy(
    context: CanonicalAuthContext,
    policy: RouteAuthPolicy,
    trust_policy_hook: Optional[TrustPolicyHook] = None,
) -> TrustDecision:
    """Evaluate trust policy and enforce fail-closed behavior."""
    validate_delegated_context_structure(context)
    decision = (trust_policy_hook or default_trust_policy_hook)(context, policy)
    if not decision.allowed:
        raise HTTPException(status_code=403, detail="Trust policy denied")
    return decision


def create_trust_guard_dependency(
    get_tenant_context: Callable,
    route_policy: RouteAuthPolicy,
    *,
    trust_policy_hook: Optional[TrustPolicyHook] = None,
) -> Callable:
    """Create a dependency that enforces trust policy for a route."""

    def require_trusted_context(
        request: Request,
        context: TenantContext = Depends(get_tenant_context),
    ) -> TenantContext:
        canonical = to_canonical_auth_context(context)
        decision = evaluate_trust_policy(canonical, route_policy, trust_policy_hook)
        request.state.auth_provenance = decision.provenance
        request.state.trust_decision_reason = decision.reason
        return context

    return require_trusted_context


async def _set_config_dim(db: AsyncSession, key: str, value: str) -> None:
    """Execute a single transaction-scoped set_config call. Private helper."""
    await db.execute(
        text("SELECT set_config(:key, :value, true)"),
        {"key": key, "value": value},
    )


def get_platform_tenant_id(request: Request) -> str:
    """Read platform_tenant_id from request.state (set by TenancyMiddleware). Returns str."""
    return request.state.platform_tenant_id


def get_service_tenant_id(request: Request) -> Optional[str]:
    """Read service_tenant_id from request.state. Returns None if not set."""
    return request.state.service_tenant_id


def get_service_user_id(request: Request) -> Optional[str]:
    """Read service_user_id from request.state. Returns None if not set."""
    return request.state.service_user_id


def create_get_tenanted_db(get_db: Callable) -> Callable:
    """
    Factory: returns a FastAPI dependency function bound to the given get_db callable.

    Each consuming service calls this once at module level, binding it to its own get_db:

        from soorma_service_common import create_get_tenanted_db
        from my_service.core.database import get_db

        get_tenanted_db = create_get_tenanted_db(get_db)

    The returned function is an async generator dependency that:
      1. Reads identity from request.state
      2. Calls PostgreSQL set_config x3 (transaction-scoped) to activate RLS
      3. Yields the AsyncSession for the route handler

    Args:
        get_db: The consuming service's async generator DB session dependency.

    Returns:
        An async generator FastAPI dependency: get_tenanted_db(request, db) -> AsyncSession
    """
    async def get_tenanted_db(
        request: Request,
        db: AsyncSession = Depends(get_db),
    ) -> AsyncGenerator[AsyncSession, None]:
        """
        FastAPI dependency: activates RLS via set_config x3 before yielding the DB session.

        Reads request.state.{platform_tenant_id,service_tenant_id,service_user_id}
        (set by TenancyMiddleware) and calls:
            set_config('app.platform_tenant_id', ..., true)
            set_config('app.service_tenant_id',  ..., true)
            set_config('app.service_user_id',    ..., true)

        None values are converted to '' (empty string) — PostgreSQL set_config
        requires a string value; RLS policies treat '' as no-filter for optional dims.
        """
        platform_tenant_id: str = request.state.platform_tenant_id
        service_tenant_id: Optional[str] = request.state.service_tenant_id
        service_user_id: Optional[str] = request.state.service_user_id

        await _set_config_dim(db, "app.platform_tenant_id", platform_tenant_id)
        await _set_config_dim(db, "app.service_tenant_id", service_tenant_id or "")
        await _set_config_dim(db, "app.service_user_id", service_user_id or "")

        yield db

    return get_tenanted_db


async def set_config_for_session(
    db: AsyncSession,
    platform_tenant_id: str,
    service_tenant_id: Optional[str],
    service_user_id: Optional[str],
) -> None:
    """
    NATS-path RLS activation: same set_config logic as get_tenanted_db but
    called directly on an AsyncSession (no HTTP request object available).

    Used by NATS event subscribers where TenancyMiddleware never runs.
    Must be called before any RLS-protected query in the same DB session.

    Args:
        db: Open AsyncSession to execute set_config on.
        platform_tenant_id: Platform tenant ID (from event.platform_tenant_id).
        service_tenant_id: Service tenant ID (from event.tenant_id); None becomes ''.
        service_user_id: Service user ID (from event.user_id); None becomes ''.
    """
    await _set_config_dim(db, "app.platform_tenant_id", platform_tenant_id)
    await _set_config_dim(db, "app.service_tenant_id", service_tenant_id or "")
    await _set_config_dim(db, "app.service_user_id", service_user_id or "")
