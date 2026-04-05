"""Delegated issuer API endpoints."""

from fastapi import APIRouter, Depends
from soorma_common.models import DelegatedIssuerRequest, DelegatedIssuerResponse

from identity_service.core.dependencies import (
    TenantContext,
    require_admin_authorization,
    require_user_tenant_context,
)
from identity_service.services.delegated_trust_service import delegated_trust_service

router = APIRouter(prefix="/delegated-issuers", tags=["Delegated Issuers"])


@router.post("", response_model=DelegatedIssuerResponse)
async def register_issuer(
    request: DelegatedIssuerRequest,
    _admin: None = Depends(require_admin_authorization),
    context: TenantContext = Depends(require_user_tenant_context),
):
    """Register delegated issuer."""
    actor_id = context.principal_id or context.service_user_id
    return await delegated_trust_service.register_issuer(context.db, request, actor_id=actor_id)


@router.put("/{delegated_issuer_id}", response_model=DelegatedIssuerResponse)
async def update_issuer(
    delegated_issuer_id: str,
    request: DelegatedIssuerRequest,
    _admin: None = Depends(require_admin_authorization),
    context: TenantContext = Depends(require_user_tenant_context),
):
    """Update delegated issuer."""
    return await delegated_trust_service.update_issuer(context.db, delegated_issuer_id, request)
