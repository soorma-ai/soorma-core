"""Delegated issuer API endpoints."""

from fastapi import APIRouter, Depends
from soorma_common.models import DelegatedIssuerRequest, DelegatedIssuerResponse

from identity_service.core.dependencies import TenantContext, require_user_tenant_context
from identity_service.services.delegated_trust_service import delegated_trust_service

router = APIRouter(prefix="/delegated-issuers", tags=["Delegated Issuers"])


@router.post("", response_model=DelegatedIssuerResponse)
async def register_issuer(
    request: DelegatedIssuerRequest,
    context: TenantContext = Depends(require_user_tenant_context),
):
    """Register delegated issuer."""
    return await delegated_trust_service.register_issuer(context.db, request)


@router.put("/{delegated_issuer_id}", response_model=DelegatedIssuerResponse)
async def update_issuer(
    delegated_issuer_id: str,
    request: DelegatedIssuerRequest,
    context: TenantContext = Depends(require_user_tenant_context),
):
    """Update delegated issuer."""
    return await delegated_trust_service.update_issuer(context.db, delegated_issuer_id, request)
