"""Memory service data deletion (BR-U4-06).

Covers 6 tables: semantic, episodic, procedural, working, task_context, plan_context.
Does NOT cover: Plan, Session (these are user-controlled lifecycle objects).
"""
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from soorma_service_common import PlatformTenantDataDeletion

from memory_service.models.memory import (
    SemanticMemory,
    EpisodicMemory,
    ProceduralMemory,
    WorkingMemory,
    TaskContext,
    PlanContext,
)


class MemoryDataDeletion(PlatformTenantDataDeletion):
    """Deletes memory data across the 6 tenant-scoped tables."""

    model_classes = [
        SemanticMemory,
        EpisodicMemory,
        ProceduralMemory,
        WorkingMemory,
        TaskContext,
        PlanContext,
    ]

    async def delete_by_platform_tenant(
        self,
        db: AsyncSession,
        platform_tenant_id: str,
    ) -> int:
        """Delete all memory data for a platform tenant across all 6 tables."""
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
        """Delete all memory data for a service tenant within a platform tenant."""
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
        """Delete all memory data for a specific user (GDPR right to erasure)."""
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
