"""Onboarding API endpoints."""

from fastapi import APIRouter, Depends
from soorma_common.models import OnboardingRequest, OnboardingResponse

from identity_service.core.dependencies import (
    TenantContext,
    get_tenant_context,
    require_admin_authorization,
)
from identity_service.services.onboarding_service import onboarding_service

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])


@router.post("", response_model=OnboardingResponse)
async def onboard_tenant(
    request: OnboardingRequest,
    _admin: None = Depends(require_admin_authorization),
    context: TenantContext = Depends(get_tenant_context),
):
    """Onboard tenant identity domain."""
    # Bootstrap onboarding is an admin-only flow and may execute before
    # service-tenant/service-user identity exists.
    actor_id = context.principal_id or context.service_user_id or "identity-admin-api-key"
    return await onboarding_service.onboard_tenant(context.db, request, actor_id=actor_id)
