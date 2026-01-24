"""Service layer for Task Context operations.

This layer provides business logic and transaction management,
sitting between the API layer and CRUD layer.
"""

from uuid import UUID
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession

from soorma_common.models import (
    TaskContextCreate,
    TaskContextUpdate,
    TaskContextResponse,
)
from memory_service.crud.task_context import (
    create_task_context as crud_create,
    get_task_context as crud_get,
    update_task_context as crud_update,
    delete_task_context as crud_delete,
    get_task_by_subtask as crud_get_by_subtask,
)
from memory_service.models.memory import TaskContext


class TaskContextService:
    """Service for managing task contexts with proper transaction boundaries."""
    
    @staticmethod
    def _to_response(task_context: TaskContext) -> TaskContextResponse:
        """Convert database model to response DTO."""
        return TaskContextResponse(
            id=str(task_context.id),
            tenant_id=str(task_context.tenant_id),
            task_id=task_context.task_id,
            plan_id=task_context.plan_id,
            event_type=task_context.event_type,
            response_event=task_context.response_event,
            response_topic=task_context.response_topic,
            data=task_context.data,
            sub_tasks=task_context.sub_tasks,
            state=task_context.state,
            created_at=task_context.created_at.isoformat(),
            updated_at=task_context.updated_at.isoformat(),
        )
    
    async def create(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        data: TaskContextCreate,
    ) -> TaskContextResponse:
        """
        Create a new task context.
        
        Transaction boundary: Commits after successful creation.
        """
        task_context = await crud_create(
            db,
            tenant_id,
            data.task_id,
            data.plan_id,
            data.event_type,
            data.response_event,
            data.response_topic,
            data.data,
            data.sub_tasks,
            data.state,
        )
        await db.commit()
        
        return self._to_response(task_context)
    
    async def get(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        task_id: str,
    ) -> Optional[TaskContextResponse]:
        """Get task context by task ID."""
        task_context = await crud_get(db, tenant_id, task_id)
        if not task_context:
            return None
        
        return self._to_response(task_context)
    
    async def update(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        task_id: str,
        data: TaskContextUpdate,
    ) -> Optional[TaskContextResponse]:
        """
        Update task context.
        
        Transaction boundary: Commits after successful update.
        """
        task_context = await crud_update(
            db,
            tenant_id,
            task_id,
            data.sub_tasks,
            data.state,
        )
        if not task_context:
            return None
        
        await db.commit()
        
        return self._to_response(task_context)
    
    async def delete(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        task_id: str,
    ) -> bool:
        """
        Delete task context.
        
        Transaction boundary: Commits after successful deletion.
        Returns True if deleted, False if not found.
        """
        deleted = await crud_delete(db, tenant_id, task_id)
        if deleted:
            await db.commit()
        
        return deleted
    
    async def get_by_subtask(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        sub_task_id: str,
    ) -> Optional[TaskContextResponse]:
        """Find parent task by sub-task ID."""
        task_context = await crud_get_by_subtask(db, tenant_id, sub_task_id)
        if not task_context:
            return None
        
        return self._to_response(task_context)


# Singleton instance for dependency injection
task_context_service = TaskContextService()
