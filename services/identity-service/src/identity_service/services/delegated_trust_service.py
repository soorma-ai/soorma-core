"""Delegated issuer trust service."""

from sqlalchemy.ext.asyncio import AsyncSession
from soorma_common.models import DelegatedIssuerRequest, DelegatedIssuerResponse

from identity_service.crud.delegated_issuers import delegated_issuer_repository
from identity_service.services.audit_service import audit_service


class DelegatedTrustService:
    """Delegated trust registration and validation service."""

    async def register_issuer(self, db: AsyncSession, request: DelegatedIssuerRequest) -> DelegatedIssuerResponse:
        """Register delegated issuer."""
        result = await delegated_issuer_repository.register_issuer(
            db,
            {
                "delegated_issuer_id": request.delegated_issuer_id,
                "tenant_domain_id": request.tenant_domain_id,
                "issuer_id": request.issuer_id,
                "jwk_set_ref_or_material": request.jwk_set_ref_or_material,
                "audience_policy_ref": request.audience_policy_ref,
                "claim_mapping_policy_ref": request.claim_mapping_policy_ref,
                "created_by": request.created_by,
                "status": "active",
            },
        )
        await audit_service.write_best_effort_event(
            db,
            event_type="identity.delegated_issuer.registered",
            payload=f"delegated_issuer_id={request.delegated_issuer_id}",
        )
        return DelegatedIssuerResponse(
            delegated_issuer_id=str(result["delegated_issuer_id"]),
            issuer_id=str(result["issuer_id"]),
            status=str(result["status"]),
        )

    async def update_issuer(
        self,
        db: AsyncSession,
        delegated_issuer_id: str,
        request: DelegatedIssuerRequest,
    ) -> DelegatedIssuerResponse:
        """Update delegated issuer."""
        result = await delegated_issuer_repository.update_issuer(
            db,
            delegated_issuer_id,
            {
                "tenant_domain_id": request.tenant_domain_id,
                "issuer_id": request.issuer_id,
                "jwk_set_ref_or_material": request.jwk_set_ref_or_material,
                "audience_policy_ref": request.audience_policy_ref,
                "claim_mapping_policy_ref": request.claim_mapping_policy_ref,
                "status": "active",
            },
        )
        await audit_service.write_best_effort_event(
            db,
            event_type="identity.delegated_issuer.updated",
            payload=f"delegated_issuer_id={delegated_issuer_id}",
        )
        return DelegatedIssuerResponse(
            delegated_issuer_id=str(result["delegated_issuer_id"]),
            issuer_id=str(result["issuer_id"]),
            status=str(result["status"]),
        )

    async def is_trusted(self, db: AsyncSession, delegated_issuer_id: str | None) -> bool:
        """Check whether delegated issuer is trusted."""
        if not delegated_issuer_id:
            return False
        issuer = await delegated_issuer_repository.get_issuer(db, delegated_issuer_id)
        if issuer is None:
            return False
        return str(issuer["status"]) == "active"


delegated_trust_service = DelegatedTrustService()
