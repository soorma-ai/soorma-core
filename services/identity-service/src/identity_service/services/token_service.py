"""Token issuance service."""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession
from soorma_common.models import TokenIssueRequest, TokenIssueResponse

from identity_service.crud.principals import principal_repository
from identity_service.crud.token_records import token_record_repository
from identity_service.services.audit_service import audit_service
from identity_service.services.delegated_trust_service import delegated_trust_service
from identity_service.services.provider_facade import provider_facade


class TokenService:
    """Token issuance business service."""

    async def issue_token(self, db: AsyncSession, request: TokenIssueRequest) -> TokenIssueResponse:
        """Issue platform or delegated token."""
        principal = await principal_repository.get_principal(db, request.principal_id)
        if principal is None:
            raise ValueError(f"principal not found: {request.principal_id}")
        if str(principal["lifecycle_state"]) != "active":
            raise PermissionError("principal is not active")

        if request.issuance_type == "delegated":
            is_trusted = await delegated_trust_service.is_trusted(db, request.delegated_issuer_id)
            if not is_trusted:
                await token_record_repository.create_record(
                    db,
                    {
                        "tenant_domain_id": request.tenant_domain_id,
                        "principal_id": request.principal_id,
                        "issuance_type": request.issuance_type,
                        "decision": "denied",
                        "decision_reason_code": "delegated_issuer_untrusted",
                    },
                )
                await audit_service.write_best_effort_event(
                    db,
                    event_type="identity.token.denied",
                    payload=(
                        f"tenant_domain_id={request.tenant_domain_id},"
                        f"principal_id={request.principal_id},reason=delegated_issuer_untrusted"
                    ),
                )
                raise PermissionError("delegated issuer is not trusted")

        issued_at = datetime.now(UTC)
        claims = {
            "tenant_domain_id": request.tenant_domain_id,
            "principal_id": request.principal_id,
            "issuance_type": request.issuance_type,
            "delegated_issuer_id": request.delegated_issuer_id,
            "iss": "soorma-identity-service",
            "iat": int(issued_at.timestamp()),
        }
        token = await provider_facade.issue_signed_token(claims)
        await token_record_repository.create_record(
            db,
            {
                "tenant_domain_id": request.tenant_domain_id,
                "principal_id": request.principal_id,
                "issuance_type": request.issuance_type,
                "decision": "issued",
                "decision_reason_code": "ok",
                "issued_at": issued_at,
            },
        )
        await audit_service.write_best_effort_event(
            db,
            event_type="identity.token.issued",
            payload=(
                f"tenant_domain_id={request.tenant_domain_id},"
                f"principal_id={request.principal_id},issuance_type={request.issuance_type}"
            ),
        )
        return TokenIssueResponse(token=token, token_type="Bearer")

    async def validate_delegated_assertion(
        self,
        db: AsyncSession,
        issuer_id: str,
        assertion: str,
    ) -> bool:
        """Validate delegated assertion and trust status."""
        issuer = await delegated_trust_service.is_trusted(db, issuer_id)
        if not issuer:
            raise PermissionError("delegated issuer is not trusted")
        return await provider_facade.validate_delegated_assertion(issuer_id, assertion)


token_service = TokenService()
