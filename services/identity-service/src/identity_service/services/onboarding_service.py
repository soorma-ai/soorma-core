"""Onboarding domain service."""

from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from soorma_common.models import OnboardingRequest, OnboardingResponse

from identity_service.crud.principals import principal_repository
from identity_service.crud.tenant_domains import tenant_domain_repository
from identity_service.services.admin_api_keys import tenant_admin_api_key_service
from identity_service.services.audit_service import audit_service


class OnboardingService:
    """Tenant onboarding business service."""

    @staticmethod
    def _new_identity_id(prefix: str) -> str:
        """Create service-owned identifier with stable readable prefix."""
        return f"{prefix}_{uuid4().hex}"

    async def onboard_tenant(
        self,
        db: AsyncSession,
        request: OnboardingRequest,
        *,
        actor_id: str,
    ) -> OnboardingResponse:
        """Create tenant domain and bootstrap principal atomically."""
        tenant_domain_id = self._new_identity_id("td")
        platform_tenant_id = self._new_identity_id("pt")
        bootstrap_admin_principal_id = self._new_identity_id("pr")
        tenant_admin_api_key = tenant_admin_api_key_service.issue_api_key(platform_tenant_id)

        try:
            domain_result = await tenant_domain_repository.create_domain(
                db,
                {
                    "tenant_domain_id": tenant_domain_id,
                    "platform_tenant_id": platform_tenant_id,
                    "created_by": actor_id,
                    "status": "active",
                },
                commit=False,
            )
            await principal_repository.create_principal(
                db,
                {
                    "principal_id": bootstrap_admin_principal_id,
                    "tenant_domain_id": tenant_domain_id,
                    "principal_type": "admin",
                    "lifecycle_state": "active",
                    "external_ref": request.bootstrap_admin_external_ref,
                },
                commit=False,
            )
            await db.commit()
        except Exception:
            await db.rollback()
            raise

        await audit_service.write_best_effort_event(
            db,
            event_type="identity.onboarding.completed",
            payload=f"tenant_domain_id={tenant_domain_id}",
        )
        return OnboardingResponse(
            tenant_domain_id=tenant_domain_id,
            platform_tenant_id=platform_tenant_id,
            bootstrap_admin_principal_id=bootstrap_admin_principal_id,
            tenant_admin_api_key=tenant_admin_api_key,
            status="created" if domain_result.get("created") else "existing",
        )


onboarding_service = OnboardingService()
