"""Principal lifecycle service."""

from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from soorma_common.models import PrincipalRequest, PrincipalResponse

from identity_service.crud.principals import principal_repository
from identity_service.crud.tenant_domains import tenant_domain_repository
from identity_service.services.errors import IdentityServiceError
from identity_service.services.audit_service import audit_service


class PrincipalService:
    """Principal lifecycle business service."""

    async def create_principal(self, db: AsyncSession, request: PrincipalRequest) -> PrincipalResponse:
        """Create principal."""
        domain = await tenant_domain_repository.get_domain(db, request.tenant_domain_id)
        if domain is None:
            raise IdentityServiceError(
                code="tenant_domain_not_found",
                message="Tenant domain was not found for principal creation.",
                status_code=404,
            )

        principal_id = f"pr_{uuid4().hex}"
        result = await principal_repository.create_principal(
            db,
            {
                "principal_id": principal_id,
                "tenant_domain_id": request.tenant_domain_id,
                "principal_type": request.principal_type,
                "lifecycle_state": request.lifecycle_state,
                "external_ref": request.external_ref,
            },
        )
        await audit_service.write_best_effort_event(
            db,
            event_type="identity.principal.created",
            payload=f"principal_id={principal_id}",
        )
        return PrincipalResponse(
            principal_id=str(result["principal_id"]),
            tenant_domain_id=str(result["tenant_domain_id"]),
            lifecycle_state=str(result["lifecycle_state"]),
        )

    async def update_principal(self, db: AsyncSession, principal_id: str, request: PrincipalRequest) -> PrincipalResponse:
        """Update principal."""
        current = await principal_repository.get_principal(db, principal_id)
        if current is None:
            raise IdentityServiceError(
                code="principal_not_found",
                message="Principal was not found.",
                status_code=404,
            )

        result = await principal_repository.update_principal(
            db,
            principal_id,
            {
                "tenant_domain_id": str(current["tenant_domain_id"]),
                "principal_type": request.principal_type,
                "lifecycle_state": request.lifecycle_state,
                "external_ref": request.external_ref,
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
