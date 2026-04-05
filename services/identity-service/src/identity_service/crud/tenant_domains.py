"""Tenant domain repository."""

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from identity_service.models.domain import PlatformTenantIdentityDomain


class TenantDomainRepository:
    """Tenant domain persistence repository."""

    async def create_domain(
        self,
        db: AsyncSession,
        payload: dict[str, object],
        *,
        commit: bool = True,
    ) -> dict[str, object]:
        """Persist tenant domain with idempotent semantics."""
        tenant_domain_id = str(payload["tenant_domain_id"])
        existing = await db.get(PlatformTenantIdentityDomain, tenant_domain_id)
        if existing is not None:
            return {
                "tenant_domain_id": existing.tenant_domain_id,
                "platform_tenant_id": existing.platform_tenant_id,
                "status": existing.status,
                "created": False,
            }

        model = PlatformTenantIdentityDomain(
            tenant_domain_id=tenant_domain_id,
            platform_tenant_id=str(payload["platform_tenant_id"]),
            status=str(payload.get("status", "active")),
            created_by=str(payload["created_by"]),
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db.add(model)
        if commit:
            await db.commit()
            await db.refresh(model)
        else:
            await db.flush()
        return {
            "tenant_domain_id": model.tenant_domain_id,
            "platform_tenant_id": model.platform_tenant_id,
            "status": model.status,
            "created": True,
        }

    async def get_domain(self, db: AsyncSession, tenant_domain_id: str) -> dict[str, object] | None:
        """Fetch tenant domain by identifier."""
        model = await db.get(PlatformTenantIdentityDomain, tenant_domain_id)
        if model is None:
            return None
        return {
            "tenant_domain_id": model.tenant_domain_id,
            "platform_tenant_id": model.platform_tenant_id,
            "status": model.status,
        }


tenant_domain_repository = TenantDomainRepository()
