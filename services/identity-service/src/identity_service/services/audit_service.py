"""Identity audit service."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from identity_service.models.domain import IdentityAuditEvent


class AuditService:
    """Audit writer service split for critical and best-effort paths."""

    async def _write_event(
        self,
        db: AsyncSession,
        event_type: str,
        payload: str,
        critical: bool,
    ) -> None:
        """Persist an identity audit event."""
        event = IdentityAuditEvent(
            event_id=str(uuid4()),
            tenant_domain_id="unknown",
            event_type=event_type,
            actor="identity-service",
            correlation_id=str(uuid4()),
            payload_summary=payload,
            critical=critical,
            emitted_at=datetime.now(UTC),
        )
        db.add(event)
        await db.commit()

    async def write_critical_event(self, db: AsyncSession, event_type: str, payload: str) -> None:
        """Write critical audit event and propagate failures."""
        await self._write_event(db, event_type=event_type, payload=payload, critical=True)

    async def write_best_effort_event(self, db: AsyncSession, event_type: str, payload: str) -> None:
        """Write best-effort audit event and swallow transient failures."""
        try:
            await self._write_event(db, event_type=event_type, payload=payload, critical=False)
        except Exception:
            await db.rollback()


audit_service = AuditService()
