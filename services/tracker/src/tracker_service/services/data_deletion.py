"""Tracker service data deletion for GDPR and operational cleanup."""

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from soorma_service_common import PlatformTenantDataDeletion
from tracker_service.models.db import ActionProgress, PlanProgress


class TrackerDataDeletion(PlatformTenantDataDeletion):
    """Deletes tracker data across plan and action progress tables."""

    model_classes = [
        ActionProgress,
        PlanProgress,
    ]

    async def delete_by_platform_tenant(
        self,
        db: AsyncSession,
        platform_tenant_id: str,
    ) -> int:
        """Delete all tracker data for a platform tenant."""
        total = 0
        for model in self.model_classes:
            result = await db.execute(
                delete(model).where(model.platform_tenant_id == platform_tenant_id)
            )
            total += result.rowcount
        return total

    async def delete_by_service_tenant(
        self,
        db: AsyncSession,
        platform_tenant_id: str,
        service_tenant_id: str,
    ) -> int:
        """Delete tracker data for a service tenant within a platform tenant."""
        total = 0
        for model in self.model_classes:
            result = await db.execute(
                delete(model).where(
                    model.platform_tenant_id == platform_tenant_id,
                    model.service_tenant_id == service_tenant_id,
                )
            )
            total += result.rowcount
        return total

    async def delete_by_service_user(
        self,
        db: AsyncSession,
        platform_tenant_id: str,
        service_tenant_id: str,
        service_user_id: str,
    ) -> int:
        """Delete tracker data for a specific service user."""
        total = 0
        for model in self.model_classes:
            result = await db.execute(
                delete(model).where(
                    model.platform_tenant_id == platform_tenant_id,
                    model.service_tenant_id == service_tenant_id,
                    model.service_user_id == service_user_id,
                )
            )
            total += result.rowcount
        return total
