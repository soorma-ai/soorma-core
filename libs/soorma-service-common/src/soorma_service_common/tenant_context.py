"""
TenantContext dataclass and dependency factory for bundle injection.

Combining all three identity dimensions with an RLS-activated DB session
into a single Depends() reduces boilerplate across Memory and Tracker routes.
"""
from dataclasses import dataclass, field
from typing import Callable, Optional

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class TenantContext:
    """
    Convenience bundle: all three identity dimensions plus an RLS-activated DB session.

    Invariant: db is always an RLS-activated AsyncSession (set_config already called
    by the underlying get_tenanted_db dependency).  Route handlers receive a fully
    ready context with a single Depends(get_tenant_context) instead of four.

    Attributes:
        platform_tenant_id: The Soorma platform tenant (always present, never blank).
        service_tenant_id: Optional per-service tenant scope (None if not provided).
        service_user_id: Optional per-service user scope (None if not provided).
        db: AsyncSession with PostgreSQL RLS session variables already set.
    """

    platform_tenant_id: str
    service_tenant_id: Optional[str]
    service_user_id: Optional[str]
    db: AsyncSession
    principal_id: Optional[str] = None
    principal_type: Optional[str] = None
    roles: list[str] = field(default_factory=list)
    issuer: Optional[str] = None
    audience: Optional[str] = None
    auth_source: Optional[str] = None
    correlation_id: Optional[str] = None


@dataclass
class CanonicalAuthContext:
    """Canonical auth context used for trust-policy evaluation."""

    platform_tenant_id: str
    service_tenant_id: Optional[str]
    service_user_id: Optional[str]
    principal_id: Optional[str] = None
    principal_type: Optional[str] = None
    roles: list[str] = field(default_factory=list)
    issuer: Optional[str] = None
    audience: Optional[str] = None
    auth_source: Optional[str] = None
    correlation_id: Optional[str] = None
    delegated_claims_present: bool = False


@dataclass
class RouteAuthPolicy:
    """Route-level trust policy owned by each consuming service."""

    route_id: str
    auth_required: bool = True
    allow_delegated_context: bool = False
    allowed_flows: list[str] = field(default_factory=lambda: ["internal_agent"])
    allowed_issuers: list[str] = field(default_factory=list)
    required_roles: list[str] = field(default_factory=list)


@dataclass
class TrustDecision:
    """Trust-policy evaluation outcome."""

    allowed: bool
    provenance: str
    reason: str
    policy_id: Optional[str] = None


def to_canonical_auth_context(context: TenantContext) -> CanonicalAuthContext:
    """Convert a TenantContext into a CanonicalAuthContext."""
    auth_source = (context.auth_source or "").strip().lower() or None
    delegated_present = bool(
        auth_source == "jwt"
        and context.service_tenant_id
        and context.service_user_id
    )

    return CanonicalAuthContext(
        platform_tenant_id=context.platform_tenant_id,
        service_tenant_id=context.service_tenant_id,
        service_user_id=context.service_user_id,
        principal_id=context.principal_id,
        principal_type=context.principal_type,
        roles=list(context.roles or []),
        issuer=context.issuer,
        audience=context.audience,
        auth_source=auth_source,
        correlation_id=context.correlation_id,
        delegated_claims_present=delegated_present,
    )


def create_get_tenant_context(get_tenanted_db: Callable) -> Callable:
    """
    Factory: returns a FastAPI dependency that yields a TenantContext.

    Each consuming service calls this once, binding it to its own get_tenanted_db:

        from soorma_service_common import create_get_tenant_context
        from my_service.core.dependencies import get_tenanted_db

        get_tenant_context = create_get_tenant_context(get_tenanted_db)

    The returned dependency reads identity from request.state and combines it
    with the RLS-activated session from get_tenanted_db.

    Args:
        get_tenanted_db: The consuming service's bound get_tenanted_db dependency
                         (itself produced by create_get_tenanted_db).

    Returns:
        A FastAPI dependency: get_tenant_context(request, db) -> TenantContext
    """
    async def get_tenant_context(
        request: Request,
        db: AsyncSession = Depends(get_tenanted_db),
    ) -> TenantContext:
        """
        FastAPI dependency: combines request.state identity values with an
        RLS-activated DB session into a single TenantContext bundle.

        Returns:
            TenantContext with all three identity dimensions and db already
            configured with set_config (via get_tenanted_db).
        """
        return TenantContext(
            platform_tenant_id=request.state.platform_tenant_id,
            service_tenant_id=request.state.service_tenant_id,
            service_user_id=request.state.service_user_id,
            db=db,
            principal_id=getattr(request.state, "principal_id", None),
            principal_type=getattr(request.state, "principal_type", None),
            roles=list(getattr(request.state, "roles", []) or []),
            issuer=getattr(request.state, "auth_issuer", None),
            audience=getattr(request.state, "auth_audience", None),
            auth_source=getattr(request.state, "auth_source", None),
            correlation_id=request.headers.get("X-Correlation-ID"),
        )

    return get_tenant_context
