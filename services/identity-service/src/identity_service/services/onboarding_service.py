"""Onboarding domain service."""

from sqlalchemy.ext.asyncio import AsyncSession
from soorma_common.models import OnboardingRequest, OnboardingResponse

from identity_service.crud.principals import principal_repository
from identity_service.crud.tenant_domains import tenant_domain_repository
from identity_service.services.audit_service import audit_service


class OnboardingService:
    """Tenant onboarding business service."""

    async def onboard_tenant(
        self,
        db: AsyncSession,
        request: OnboardingRequest,
    ) -> OnboardingResponse:
        """Create tenant domain and bootstrap principal atomically."""
        domain_result = await tenant_domain_repository.create_domain(
            db,
            {
                "tenant_domain_id": request.tenant_domain_id,
                "platform_tenant_id": request.platform_tenant_id,
                "created_by": request.created_by,
                "status": "active",
            },
        )
        await principal_repository.create_principal(
            db,
            {
                "principal_id": request.bootstrap_admin_principal_id,
                "tenant_domain_id": request.tenant_domain_id,
                "principal_type": "admin",
                "lifecycle_state": "active",
            },
        )
        await audit_service.write_best_effort_event(
            db,
            event_type="identity.onboarding.completed",
            payload=f"tenant_domain_id={request.tenant_domain_id}",
        )
        return OnboardingResponse(
            tenant_domain_id=request.tenant_domain_id,
            bootstrap_admin_principal_id=request.bootstrap_admin_principal_id,
            status="created" if domain_result.get("created") else "existing",
        )


onboarding_service = OnboardingService()
