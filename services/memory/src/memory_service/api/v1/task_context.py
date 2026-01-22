"""Task context API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from memory_service.core.dependencies import TenantContext, get_tenant_context
from soorma_common.models import (
    TaskContextCreate,
    TaskContextUpdate,
    TaskContextResponse,
)
from memory_service.services.task_context_service import task_context_service

router = APIRouter(prefix="/task-context", tags=["Task Context"])


@router.post("", response_model=TaskContextResponse, status_code=status.HTTP_201_CREATED)
async def create_task_context_endpoint(
    data: TaskContextCreate,
    context: TenantContext = Depends(get_tenant_context),
):
    """Create a new task context."""
    return await task_context_service.create(context.db, context.tenant_id, data)


@router.get("/{task_id}", response_model=TaskContextResponse)
async def get_task_context_endpoint(
    task_id: str,
    context: TenantContext = Depends(get_tenant_context),
):
    """Get task context by task ID."""
    result = await task_context_service.get(context.db, context.tenant_id, task_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task context not found: {task_id}",
        )
    return result


@router.put("/{task_id}", response_model=TaskContextResponse)
async def update_task_context_endpoint(
    task_id: str,
    data: TaskContextUpdate,
    context: TenantContext = Depends(get_tenant_context),
):
    """Update task context."""
    result = await task_context_service.update(context.db, context.tenant_id, task_id, data)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task context not found: {task_id}",
        )
    return result


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task_context_endpoint(
    task_id: str,
    context: TenantContext = Depends(get_tenant_context),
):
    """Delete task context."""
    deleted = await task_context_service.delete(context.db, context.tenant_id, task_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task context not found: {task_id}",
        )


@router.get("/by-subtask/{sub_task_id}", response_model=TaskContextResponse)
async def get_task_by_subtask_endpoint(
    sub_task_id: str,
    context: TenantContext = Depends(get_tenant_context),
):
    """Find parent task by sub-task ID."""
    result = await task_context_service.get_by_subtask(context.db, context.tenant_id, sub_task_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parent task not found for sub-task: {sub_task_id}",
        )
    return result

