"""Tenant admin credential repository."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from identity_service.models.domain import TenantAdminCredential


class TenantAdminCredentialRepository:
    """Persistence helpers for tenant admin credentials."""

    async def create_credential(
        self,
        db: AsyncSession,
        payload: dict[str, object],
        *,
        commit: bool = True,
    ) -> dict[str, object]:
        """Persist a tenant admin credential record."""
        model = TenantAdminCredential(
            credential_id=str(payload["credential_id"]),
            platform_tenant_id=str(payload["platform_tenant_id"]),
            secret_hash=str(payload["secret_hash"]),
            status=str(payload.get("status", "active")),
            created_by=str(payload["created_by"]),
            rotated_from_credential_id=(
                str(payload["rotated_from_credential_id"])
                if payload.get("rotated_from_credential_id") is not None
                else None
            ),
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db.add(model)
        if commit:
            await db.commit()
            await db.refresh(model)
        else:
            await db.flush()
        return {
            "credential_id": model.credential_id,
            "platform_tenant_id": model.platform_tenant_id,
            "status": model.status,
        }

    async def get_active_credential(
        self,
        db: AsyncSession,
        credential_id: str,
        platform_tenant_id: str,
    ) -> dict[str, object] | None:
        """Fetch an active tenant admin credential by id and tenant."""
        rows = await db.execute(
            select(TenantAdminCredential).where(
                TenantAdminCredential.credential_id == credential_id,
                TenantAdminCredential.platform_tenant_id == platform_tenant_id,
                TenantAdminCredential.status == "active",
            )
        )
        model = rows.scalars().first()
        if model is None:
            return None
        return {
            "credential_id": model.credential_id,
            "platform_tenant_id": model.platform_tenant_id,
            "secret_hash": model.secret_hash,
            "status": model.status,
        }

    async def revoke_active_credentials(
        self,
        db: AsyncSession,
        platform_tenant_id: str,
        *,
        commit: bool = True,
    ) -> int:
        """Revoke all currently active credentials for the tenant."""
        rows = await db.execute(
            select(TenantAdminCredential).where(
                TenantAdminCredential.platform_tenant_id == platform_tenant_id,
                TenantAdminCredential.status == "active",
            )
        )
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        revoked_count = 0
        for model in rows.scalars().all():
            model.status = "revoked"
            model.revoked_at = now
            revoked_count += 1
        if commit:
            await db.commit()
        else:
            await db.flush()
        return revoked_count


tenant_admin_credential_repository = TenantAdminCredentialRepository()
