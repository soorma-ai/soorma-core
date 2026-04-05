"""Onboarding API endpoints."""

from fastapi import APIRouter, Depends
from soorma_common.models import OnboardingRequest, OnboardingResponse

from identity_service.core.dependencies import TenantContext, require_user_tenant_context
from identity_service.services.onboarding_service import onboarding_service

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])


@router.post("", response_model=OnboardingResponse)
async def onboard_tenant(
    request: OnboardingRequest,
    context: TenantContext = Depends(require_user_tenant_context),
):
    """Onboard tenant identity domain."""
    return await onboarding_service.onboard_tenant(context.db, request)
