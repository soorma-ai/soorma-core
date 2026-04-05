"""Audit service persistence tests."""

import pytest
from sqlalchemy import select

from identity_service.models.domain import IdentityAuditEvent
from identity_service.services.audit_service import audit_service


@pytest.mark.asyncio
async def test_write_critical_event_persists_record(db_session):
    """Critical audit event should be persisted."""
    await audit_service.write_critical_event(
        db_session,
        event_type="identity.test.critical",
        payload="critical-payload",
    )

    event = (
        await db_session.execute(
            select(IdentityAuditEvent).where(
                IdentityAuditEvent.event_type == "identity.test.critical"
            )
        )
    ).scalars().first()
    assert event is not None
    assert event.critical is True


@pytest.mark.asyncio
async def test_write_best_effort_event_persists_record(db_session):
    """Best-effort audit event should persist when DB is available."""
    await audit_service.write_best_effort_event(
        db_session,
        event_type="identity.test.best_effort",
        payload="best-effort-payload",
    )

    event = (
        await db_session.execute(
            select(IdentityAuditEvent).where(
                IdentityAuditEvent.event_type == "identity.test.best_effort"
            )
        )
    ).scalars().first()
    assert event is not None
    assert event.critical is False
