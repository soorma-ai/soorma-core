"""Delegated issuer API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from soorma_common.models import DelegatedIssuerRequest, DelegatedIssuerResponse

from identity_service.core.dependencies import (
    TenantContext,
    get_tenant_context,
    require_tenant_admin_authorization,
)
from identity_service.crud.delegated_issuers import delegated_issuer_repository
from identity_service.crud.tenant_domains import tenant_domain_repository
from identity_service.services.delegated_trust_service import delegated_trust_service

router = APIRouter(prefix="/delegated-issuers", tags=["Delegated Issuers"])


async def _ensure_tenant_domain_platform_match(
    context: TenantContext,
    tenant_domain_id: str,
) -> None:
    """Fail closed when tenant domain is outside current platform tenant context."""
    tenant_domain = await tenant_domain_repository.get_domain(context.db, tenant_domain_id)
    if tenant_domain is None:
        raise HTTPException(status_code=404, detail="Tenant domain was not found.")

    if str(tenant_domain["platform_tenant_id"]) != context.platform_tenant_id:
        raise HTTPException(
            status_code=403,
            detail="Tenant domain does not belong to current platform tenant context.",
        )


async def _get_delegated_issuer_tenant_domain_id(
    context: TenantContext,
    delegated_issuer_id: str,
) -> str:
    """Return delegated issuer tenant domain after ownership guard checks."""
    issuer = await delegated_issuer_repository.get_issuer(context.db, delegated_issuer_id)
    if issuer is None:
        raise HTTPException(status_code=404, detail="Delegated issuer was not found.")

    tenant_domain_id = str(issuer["tenant_domain_id"])
    await _ensure_tenant_domain_platform_match(context, tenant_domain_id)
    return tenant_domain_id


@router.post("", response_model=DelegatedIssuerResponse)
async def register_issuer(
    request: DelegatedIssuerRequest,
    _tenant_admin: str = Depends(require_tenant_admin_authorization),
    context: TenantContext = Depends(get_tenant_context),
):
    """Register delegated issuer."""
    await _ensure_tenant_domain_platform_match(context, request.tenant_domain_id)
    actor_id = context.principal_id or context.service_user_id or "identity-tenant-admin-api-key"
    return await delegated_trust_service.register_issuer(context.db, request, actor_id=actor_id)


@router.put("/{delegated_issuer_id}", response_model=DelegatedIssuerResponse)
async def update_issuer(
    delegated_issuer_id: str,
    request: DelegatedIssuerRequest,
    _tenant_admin: str = Depends(require_tenant_admin_authorization),
    context: TenantContext = Depends(get_tenant_context),
):
    """Update delegated issuer."""
    existing_tenant_domain_id = await _get_delegated_issuer_tenant_domain_id(context, delegated_issuer_id)
    if request.tenant_domain_id != existing_tenant_domain_id:
        raise HTTPException(
            status_code=400,
            detail="Delegated issuer tenant_domain_id is immutable.",
        )

    return await delegated_trust_service.update_issuer(context.db, delegated_issuer_id, request)
