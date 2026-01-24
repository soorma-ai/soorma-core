"""Service layer for Working Memory operations."""

from uuid import UUID
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from soorma_common.models import WorkingMemorySet, WorkingMemoryResponse
from memory_service.crud.working import (
    set_working_memory as crud_set,
    get_working_memory as crud_get,
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
        plan_id: UUID,
        key: str,
        data: WorkingMemorySet,
    ) -> WorkingMemoryResponse:
        """
        Set or update working memory value.
        
        Transaction boundary: No commit needed - upsert is atomic.
        """
        memory = await crud_set(db, tenant_id, plan_id, key, data)
        return self._to_response(memory)
    
    async def get(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        plan_id: UUID,
        key: str,
    ) -> Optional[WorkingMemoryResponse]:
        """Get working memory value."""
        memory = await crud_get(db, tenant_id, plan_id, key)
        if not memory:
            return None
        
        return self._to_response(memory)


# Singleton instance for dependency injection
working_memory_service = WorkingMemoryService()
