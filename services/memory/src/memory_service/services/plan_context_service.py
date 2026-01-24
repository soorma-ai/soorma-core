"""Service layer for Plan Context operations.

This layer provides business logic and transaction management,
sitting between the API layer and CRUD layer.
"""

from uuid import UUID
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession

from soorma_common.models import (
    PlanContextCreate,
    PlanContextUpdate,
    PlanContextResponse,
)
from memory_service.crud.plan_context import (
    create_plan_context as crud_create,
    get_plan_context as crud_get,
    update_plan_context as crud_update,
    delete_plan_context as crud_delete,
    get_plan_by_correlation as crud_get_by_correlation,
)
from memory_service.models.memory import PlanContext


class PlanContextService:
    """Service for managing plan contexts with proper transaction boundaries."""
    
    @staticmethod
    def _to_response(plan_context: PlanContext) -> PlanContextResponse:
        """Convert database model to response DTO."""
        return PlanContextResponse(
            id=str(plan_context.id),
            tenant_id=str(plan_context.tenant_id),
            plan_id=plan_context.plan_id,
            session_id=plan_context.session_id,
            goal_event=plan_context.goal_event,
            goal_data=plan_context.goal_data,
            response_event=plan_context.response_event,
            state=plan_context.state,
            current_state=plan_context.current_state,
            correlation_ids=plan_context.correlation_ids,
            created_at=plan_context.created_at.isoformat(),
            updated_at=plan_context.updated_at.isoformat(),
        )
    
    async def create(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        data: PlanContextCreate,
    ) -> PlanContextResponse:
        """
        Create a new plan context.
        
        Transaction boundary: Commits after successful creation.
        """
        plan_context = await crud_create(
            db,
            tenant_id,
            data.plan_id,
            data.session_id,
            data.goal_event,
            data.goal_data,
            data.response_event,
            data.state,
            data.current_state,
            data.correlation_ids,
        )
        await db.commit()
        
        return self._to_response(plan_context)
    
    async def get(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        plan_id: str,
    ) -> Optional[PlanContextResponse]:
        """Get plan context by plan ID."""
        plan_context = await crud_get(db, tenant_id, plan_id)
        if not plan_context:
            return None
        
        return self._to_response(plan_context)
    
    async def update(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        plan_id: str,
        data: PlanContextUpdate,
    ) -> Optional[PlanContextResponse]:
        """
        Update plan context.
        
        Transaction boundary: Commits after successful update.
        """
        plan_context = await crud_update(
            db,
            tenant_id,
            plan_id,
            data.state,
            data.current_state,
            data.correlation_ids,
        )
        if not plan_context:
            return None
        
        await db.commit()
        
        return self._to_response(plan_context)
    
    async def delete(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        plan_id: str,
    ) -> bool:
        """
        Delete plan context.
        
        Transaction boundary: Commits after successful deletion.
        Returns True if deleted, False if not found.
        """
        deleted = await crud_delete(db, tenant_id, plan_id)
        if deleted:
            await db.commit()
        
        return deleted
    
    async def get_by_correlation(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        correlation_id: str,
    ) -> Optional[PlanContextResponse]:
        """Find plan by correlation ID."""
        plan_context = await crud_get_by_correlation(db, tenant_id, correlation_id)
        if not plan_context:
            return None
        
        return self._to_response(plan_context)


# Singleton instance for dependency injection
plan_context_service = PlanContextService()
