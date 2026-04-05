"""Token issuance repository."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from identity_service.models.domain import TokenIssuanceRecord


class TokenRecordRepository:
    """Token issuance record persistence repository."""

    async def create_record(self, db: AsyncSession, payload: dict[str, object]) -> dict[str, object]:
        """Persist issuance decision record."""
        record = TokenIssuanceRecord(
            issuance_id=str(payload.get("issuance_id") or uuid4()),
            tenant_domain_id=str(payload["tenant_domain_id"]),
            principal_id=str(payload["principal_id"]),
            issuance_type=str(payload.get("issuance_type", "platform")),
            decision=str(payload.get("decision", "issued")),
            decision_reason_code=str(payload.get("decision_reason_code", "ok")),
            issued_at=payload.get("issued_at") or datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return {
            "issuance_id": record.issuance_id,
            "tenant_domain_id": record.tenant_domain_id,
            "principal_id": record.principal_id,
            "issuance_type": record.issuance_type,
            "decision": record.decision,
            "decision_reason_code": record.decision_reason_code,
        }


token_record_repository = TokenRecordRepository()
