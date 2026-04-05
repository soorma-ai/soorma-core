"""Mapping and collision policy service."""

from sqlalchemy.ext.asyncio import AsyncSession
from soorma_common.models import MappingEvaluationRequest, MappingEvaluationResponse

from identity_service.crud.mappings import mapping_repository
from identity_service.crud.principals import principal_repository
from identity_service.services.audit_service import audit_service


class MappingService:
    """External identity mapping and collision policy service."""

    async def evaluate_mapping(
        self,
        db: AsyncSession,
        request: MappingEvaluationRequest,
    ) -> MappingEvaluationResponse:
        """Evaluate mapping collision policy."""
        if request.override_requested:
            principal = await principal_repository.get_principal(db, request.principal_id)
            if principal is None or str(principal["principal_type"]) != "admin":
                await audit_service.write_best_effort_event(
                    db,
                    event_type="identity.mapping.evaluated",
                    payload=(
                        f"tenant_domain_id={request.tenant_domain_id},"
                        "decision=deny,reason=override_admin_required"
                    ),
                )
                return MappingEvaluationResponse(
                    decision="deny",
                    reason_code="override_admin_required",
                )

        result = await mapping_repository.evaluate_collision(
            db,
            {
                "tenant_domain_id": request.tenant_domain_id,
                "source_issuer_id": request.source_issuer_id,
                "external_identity_key": request.external_identity_key,
                "canonical_identity_key": request.canonical_identity_key,
                "principal_id": request.principal_id,
                "override_requested": request.override_requested,
            },
        )
        await audit_service.write_best_effort_event(
            db,
            event_type="identity.mapping.evaluated",
            payload=(
                f"tenant_domain_id={request.tenant_domain_id},"
                f"decision={result['decision']},reason={result['reason_code']}"
            ),
        )
        return MappingEvaluationResponse(
            decision=str(result["decision"]),
            reason_code=str(result["reason_code"]),
        )


mapping_service = MappingService()
