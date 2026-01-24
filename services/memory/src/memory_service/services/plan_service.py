"""Service layer for Plan operations.

This layer provides business logic and transaction management,
sitting between the API layer and CRUD layer.
"""

from uuid import UUID
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from soorma_common.models import (
    PlanCreate,
    PlanUpdate,
    PlanSummary,
)
from memory_service.crud.plans import (
    create_plan as crud_create,
    get_plan as crud_get,
    list_plans as crud_list,
    update_plan as crud_update,
    delete_plan as crud_delete,
)
from memory_service.models.memory import Plan


class PlanService:
    """Service for managing plans with proper transaction boundaries."""
    
    @staticmethod
    def _to_summary(plan: Plan) -> PlanSummary:
        """Convert database model to summary DTO."""
        return PlanSummary(
            id=str(plan.id),
            tenant_id=str(plan.tenant_id),
            user_id=str(plan.user_id),
            plan_id=plan.plan_id,
            session_id=plan.session_id,
            goal_event=plan.goal_event,
            goal_data=plan.goal_data,
            status=plan.status,
            parent_plan_id=plan.parent_plan_id,
            created_at=plan.created_at.isoformat(),
            updated_at=plan.updated_at.isoformat(),
        )
    
    async def create(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        data: PlanCreate,
    ) -> PlanSummary:
        """
        Create a new plan.
        
        Transaction boundary: Commits after successful creation.
        """
        plan = await crud_create(
            db,
            tenant_id,
            user_id,
            data.plan_id,
            data.session_id,
            data.goal_event,
            data.goal_data,
            data.parent_plan_id,
        )
        await db.commit()
        
        return self._to_summary(plan)
    
    async def get(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        plan_id: str,
    ) -> Optional[PlanSummary]:
        """Get plan by ID."""
        plan = await crud_get(db, tenant_id, plan_id)
        if not plan:
            return None
        
        return self._to_summary(plan)
    
    async def list(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        status: Optional[str] = None,
        session_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[PlanSummary]:
        """List plans for a user with optional filters."""
        plans = await crud_list(db, tenant_id, user_id, status, session_id, limit)
        return [self._to_summary(p) for p in plans]
    
    async def update(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        plan_id: str,
        data: PlanUpdate,
    ) -> Optional[PlanSummary]:
        """
        Update plan status.
        
        Transaction boundary: Commits after successful update.
        """
        plan = await crud_update(db, tenant_id, plan_id, data.status)
        if not plan:
            return None
        
        await db.commit()
        
        return self._to_summary(plan)
    
    async def delete(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        plan_id: str,
    ) -> bool:
        """
        Delete plan.
        
        Transaction boundary: Commits after successful deletion.
        Returns True if deleted, False if not found.
        """
        deleted = await crud_delete(db, tenant_id, plan_id)
        if deleted:
            await db.commit()
        
        return deleted


# Singleton instance for dependency injection
plan_service = PlanService()
