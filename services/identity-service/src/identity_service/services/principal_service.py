"""Principal lifecycle service."""

from sqlalchemy.ext.asyncio import AsyncSession
from soorma_common.models import PrincipalRequest, PrincipalResponse

from identity_service.crud.principals import principal_repository
from identity_service.services.audit_service import audit_service


class PrincipalService:
    """Principal lifecycle business service."""

    async def create_principal(self, db: AsyncSession, request: PrincipalRequest) -> PrincipalResponse:
        """Create principal."""
        result = await principal_repository.create_principal(
            db,
            {
                "principal_id": request.principal_id,
                "tenant_domain_id": request.tenant_domain_id,
                "principal_type": request.principal_type,
                "lifecycle_state": request.lifecycle_state,
            },
        )
        await audit_service.write_best_effort_event(
            db,
            event_type="identity.principal.created",
            payload=f"principal_id={request.principal_id}",
        )
        return PrincipalResponse(
            principal_id=str(result["principal_id"]),
            tenant_domain_id=str(result["tenant_domain_id"]),
            lifecycle_state=str(result["lifecycle_state"]),
        )

    async def update_principal(self, db: AsyncSession, principal_id: str, request: PrincipalRequest) -> PrincipalResponse:
        """Update principal."""
        result = await principal_repository.update_principal(
            db,
            principal_id,
            {
                "tenant_domain_id": request.tenant_domain_id,
                "principal_type": request.principal_type,
                "lifecycle_state": request.lifecycle_state,
            },
        )
        await audit_service.write_best_effort_event(
            db,
            event_type="identity.principal.updated",
            payload=f"principal_id={principal_id}",
        )
        return PrincipalResponse(
            principal_id=str(result["principal_id"]),
            tenant_domain_id=str(result["tenant_domain_id"]),
            lifecycle_state=str(result["lifecycle_state"]),
        )

    async def revoke_principal(self, db: AsyncSession, principal_id: str) -> PrincipalResponse:
        """Revoke principal."""
        result = await principal_repository.revoke_principal(db, principal_id)
        await audit_service.write_best_effort_event(
            db,
            event_type="identity.principal.revoked",
            payload=f"principal_id={principal_id}",
        )
        return PrincipalResponse(
            principal_id=str(result["principal_id"]),
            tenant_domain_id=str(result["tenant_domain_id"]),
            lifecycle_state=str(result["lifecycle_state"]),
        )


principal_service = PrincipalService()
