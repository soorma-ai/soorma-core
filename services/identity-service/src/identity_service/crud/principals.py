"""Principal repository."""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from identity_service.models.domain import Principal


class PrincipalRepository:
    """Principal lifecycle persistence repository."""

    async def create_principal(self, db: AsyncSession, payload: dict[str, object]) -> dict[str, object]:
        """Persist principal with idempotent semantics."""
        principal_id = str(payload["principal_id"])
        existing = await db.get(Principal, principal_id)
        if existing is not None:
            return {
                "principal_id": existing.principal_id,
                "tenant_domain_id": existing.tenant_domain_id,
                "lifecycle_state": existing.lifecycle_state,
                "created": False,
            }

        model = Principal(
            principal_id=principal_id,
            tenant_domain_id=str(payload["tenant_domain_id"]),
            principal_type=str(payload["principal_type"]),
            lifecycle_state=str(payload.get("lifecycle_state", "active")),
            external_ref=str(payload["external_ref"]) if payload.get("external_ref") is not None else None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db.add(model)
        await db.commit()
        await db.refresh(model)
        return {
            "principal_id": model.principal_id,
            "tenant_domain_id": model.tenant_domain_id,
            "lifecycle_state": model.lifecycle_state,
            "created": True,
        }

    async def update_principal(self, db: AsyncSession, principal_id: str, payload: dict[str, object]) -> dict[str, object]:
        """Update principal lifecycle state and optional metadata."""
        model = await db.get(Principal, principal_id)
        if model is None:
            raise ValueError(f"principal not found: {principal_id}")

        model.tenant_domain_id = str(payload["tenant_domain_id"])
        model.principal_type = str(payload["principal_type"])
        model.lifecycle_state = str(payload.get("lifecycle_state", model.lifecycle_state))
        model.external_ref = str(payload["external_ref"]) if payload.get("external_ref") is not None else model.external_ref
        model.updated_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(model)
        return {
            "principal_id": model.principal_id,
            "tenant_domain_id": model.tenant_domain_id,
            "lifecycle_state": model.lifecycle_state,
        }

    async def get_principal(self, db: AsyncSession, principal_id: str) -> dict[str, object] | None:
        """Get principal by ID."""
        model = await db.get(Principal, principal_id)
        if model is None:
            return None
        return {
            "principal_id": model.principal_id,
            "tenant_domain_id": model.tenant_domain_id,
            "lifecycle_state": model.lifecycle_state,
            "principal_type": model.principal_type,
        }

    async def revoke_principal(self, db: AsyncSession, principal_id: str) -> dict[str, object]:
        """Set principal lifecycle state to revoked."""
        model = await db.get(Principal, principal_id)
        if model is None:
            raise ValueError(f"principal not found: {principal_id}")
        model.lifecycle_state = "revoked"
        model.updated_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(model)
        return {
            "principal_id": model.principal_id,
            "tenant_domain_id": model.tenant_domain_id,
            "lifecycle_state": model.lifecycle_state,
        }

    async def list_principals_for_tenant(self, db: AsyncSession, tenant_domain_id: str) -> list[dict[str, object]]:
        """List principals for a tenant domain."""
        rows = await db.execute(
            select(Principal).where(Principal.tenant_domain_id == tenant_domain_id)
        )
        return [
            {
                "principal_id": p.principal_id,
                "tenant_domain_id": p.tenant_domain_id,
                "lifecycle_state": p.lifecycle_state,
                "principal_type": p.principal_type,
            }
            for p in rows.scalars().all()
        ]


principal_repository = PrincipalRepository()
