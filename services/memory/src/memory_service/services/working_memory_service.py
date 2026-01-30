"""Service layer for Working Memory operations."""

from uuid import UUID
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from soorma_common.models import (
    WorkingMemorySet,
    WorkingMemoryResponse,
    WorkingMemoryDeleteKeyResponse,
    WorkingMemoryDeletePlanResponse,
)
from memory_service.crud.working import (
    set_working_memory as crud_set,
    get_working_memory as crud_get,
    delete_working_memory_key as crud_delete_key,
    delete_working_memory_plan as crud_delete_plan,
)
from memory_service.models.memory import WorkingMemory


class WorkingMemoryService:
    """Service for managing working memory with proper transaction boundaries."""
    
    @staticmethod
    def _to_response(memory: WorkingMemory) -> WorkingMemoryResponse:
        """Convert database model to response DTO."""
        return WorkingMemoryResponse(
            id=str(memory.id),
            tenant_id=str(memory.tenant_id),
            plan_id=str(memory.plan_id),
            key=memory.key,
            value=memory.value,
            updated_at=memory.updated_at.isoformat(),
        )
    
    async def set(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        plan_id: UUID,
        key: str,
        data: WorkingMemorySet,
    ) -> WorkingMemoryResponse:
        """
        Set or update working memory value.
        
        Transaction boundary: No commit needed - upsert is atomic.
        """
        memory = await crud_set(db, tenant_id, user_id, plan_id, key, data)
        return self._to_response(memory)
    
    async def get(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        plan_id: UUID,
        key: str,
    ) -> Optional[WorkingMemoryResponse]:
        """Get working memory value."""
        memory = await crud_get(db, tenant_id, user_id, plan_id, key)
        if not memory:
            return None
        
        return self._to_response(memory)

    async def delete_key(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        plan_id: UUID,
        key: str,
    ) -> WorkingMemoryDeleteKeyResponse:
        """Delete a single working memory key."""
        deleted = await crud_delete_key(db, tenant_id, user_id, plan_id, key)
        return WorkingMemoryDeleteKeyResponse(
            success=True,
            deleted=deleted,
            message=f"Working memory key deleted" if deleted else f"Working memory key not found",
        )

    async def delete_plan(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        plan_id: UUID,
    ) -> WorkingMemoryDeletePlanResponse:
        """Delete all working memory for a plan."""
        count = await crud_delete_plan(db, tenant_id, user_id, plan_id)
        return WorkingMemoryDeletePlanResponse(
            success=True,
            count_deleted=count,
            message=f"Deleted {count} working memory keys",
        )


# Singleton instance for dependency injection
working_memory_service = WorkingMemoryService()
