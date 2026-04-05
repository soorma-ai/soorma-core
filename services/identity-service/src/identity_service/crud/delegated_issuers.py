"""Delegated issuer repository."""

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from identity_service.models.domain import DelegatedIssuer


class DelegatedIssuerRepository:
    """Delegated issuer persistence repository."""

    async def register_issuer(self, db: AsyncSession, payload: dict[str, object]) -> dict[str, object]:
        """Persist delegated issuer trust metadata with idempotent semantics."""
        delegated_issuer_id = str(payload["delegated_issuer_id"])
        existing = await db.get(DelegatedIssuer, delegated_issuer_id)
        if existing is not None:
            return {
                "delegated_issuer_id": existing.delegated_issuer_id,
                "issuer_id": existing.issuer_id,
                "status": existing.status,
                "created": False,
            }

        model = DelegatedIssuer(
            delegated_issuer_id=delegated_issuer_id,
            tenant_domain_id=str(payload["tenant_domain_id"]),
            issuer_id=str(payload["issuer_id"]),
            status=str(payload.get("status", "active")),
            jwk_set_ref_or_material=str(payload["jwk_set_ref_or_material"]),
            audience_policy_ref=str(payload["audience_policy_ref"]),
            claim_mapping_policy_ref=str(payload["claim_mapping_policy_ref"]),
            created_by=str(payload["created_by"]),
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db.add(model)
        await db.commit()
        await db.refresh(model)
        return {
            "delegated_issuer_id": model.delegated_issuer_id,
            "issuer_id": model.issuer_id,
            "status": model.status,
            "created": True,
        }

    async def update_issuer(
        self,
        db: AsyncSession,
        delegated_issuer_id: str,
        payload: dict[str, object],
    ) -> dict[str, object]:
        """Update delegated issuer trust metadata."""
        model = await db.get(DelegatedIssuer, delegated_issuer_id)
        if model is None:
            raise ValueError(f"delegated issuer not found: {delegated_issuer_id}")

        model.tenant_domain_id = str(payload["tenant_domain_id"])
        model.issuer_id = str(payload["issuer_id"])
        model.status = str(payload.get("status", "active"))
        model.jwk_set_ref_or_material = str(payload["jwk_set_ref_or_material"])
        model.audience_policy_ref = str(payload["audience_policy_ref"])
        model.claim_mapping_policy_ref = str(payload["claim_mapping_policy_ref"])
        await db.commit()
        await db.refresh(model)
        return {
            "delegated_issuer_id": model.delegated_issuer_id,
            "issuer_id": model.issuer_id,
            "status": model.status,
        }

    async def get_issuer(self, db: AsyncSession, delegated_issuer_id: str) -> dict[str, object] | None:
        """Get delegated issuer by identifier."""
        model = await db.get(DelegatedIssuer, delegated_issuer_id)
        if model is None:
            return None
        return {
            "delegated_issuer_id": model.delegated_issuer_id,
            "tenant_domain_id": model.tenant_domain_id,
            "issuer_id": model.issuer_id,
            "status": model.status,
        }

    async def list_active_issuers(self, db: AsyncSession, tenant_domain_id: str) -> list[dict[str, object]]:
        """List active delegated issuers for tenant domain."""
        rows = await db.execute(
            select(DelegatedIssuer).where(
                DelegatedIssuer.tenant_domain_id == tenant_domain_id,
                DelegatedIssuer.status == "active",
            )
        )
        return [
            {
                "delegated_issuer_id": issuer.delegated_issuer_id,
                "tenant_domain_id": issuer.tenant_domain_id,
                "issuer_id": issuer.issuer_id,
                "status": issuer.status,
            }
            for issuer in rows.scalars().all()
        ]


delegated_issuer_repository = DelegatedIssuerRepository()
