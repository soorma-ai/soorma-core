"""Query API endpoints for Tracker Service.

This module provides read-only query endpoints for:
- Plan execution progress
- Action execution history
- Event timelines
- Agent metrics
"""

from typing import List
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from starlette import status

from soorma_common import (
    PlanProgress as PlanProgressDTO,
    TaskExecution,
)
from tracker_service.core.dependencies import TenantContext, get_tenant_context
from tracker_service.models import db as db_models


router = APIRouter(prefix="/tracker", tags=["tracker"])


def _validate_identity_dimensions(context: TenantContext) -> None:
    """Enforce minimal local validation for identity dimensions."""
    if not context.service_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="X-Service-Tenant-ID header is required",
        )
    if not context.service_user_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="X-User-ID header is required",
        )

    if len(context.platform_tenant_id) > 64:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="X-Tenant-ID exceeds 64 characters",
        )
    if len(context.service_tenant_id) > 64:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="X-Service-Tenant-ID exceeds 64 characters",
        )
    if len(context.service_user_id) > 64:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="X-User-ID exceeds 64 characters",
        )


@router.get("/plans/{plan_id}", response_model=PlanProgressDTO)
async def get_plan_progress(
    plan_id: str,
    context: TenantContext = Depends(get_tenant_context),
) -> PlanProgressDTO:
    """
    Get plan execution progress.
    
    Args:
        plan_id: Plan identifier
        context: Tenant identity bundle with RLS-activated database session
    
    Returns:
        PlanProgress with execution status and metrics
    
    Raises:
        HTTPException: 404 if plan not found
    """
    _validate_identity_dimensions(context)

    # Query plan_progress with tenant filtering
    stmt = select(db_models.PlanProgress).where(
        db_models.PlanProgress.plan_id == plan_id,
        db_models.PlanProgress.platform_tenant_id == context.platform_tenant_id,
        db_models.PlanProgress.service_tenant_id == context.service_tenant_id,
        db_models.PlanProgress.service_user_id == context.service_user_id,
    )
    result = await context.db.execute(stmt)
    plan_progress = result.scalar_one_or_none()
    
    if plan_progress is None:
        raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")
    
    # Convert DB model to DTO
    return PlanProgressDTO(
        plan_id=plan_progress.plan_id,
        status=plan_progress.status,
        task_count=plan_progress.total_actions,
        completed_tasks=plan_progress.completed_actions,
        failed_tasks=plan_progress.failed_actions,
        started_at=plan_progress.started_at,
        completed_at=plan_progress.completed_at,
        current_state=plan_progress.error_message,  # Map error_message to current_state
    )


@router.get("/plans/{plan_id}/actions", response_model=List[TaskExecution])
async def get_plan_actions(
    plan_id: str,
    context: TenantContext = Depends(get_tenant_context),
) -> List[TaskExecution]:
    """
    Get all action executions for a plan.
    
    Args:
        plan_id: Plan identifier
        context: Tenant identity bundle with RLS-activated database session
    
    Returns:
        List of TaskExecution records (may be empty)
    """
    _validate_identity_dimensions(context)

    # Query action_progress with tenant + plan filtering
    stmt = select(db_models.ActionProgress).where(
        db_models.ActionProgress.plan_id == plan_id,
        db_models.ActionProgress.platform_tenant_id == context.platform_tenant_id,
        db_models.ActionProgress.service_tenant_id == context.service_tenant_id,
        db_models.ActionProgress.service_user_id == context.service_user_id,
    ).order_by(db_models.ActionProgress.started_at)
    
    result = await context.db.execute(stmt)
    actions = result.scalars().all()
    
    # Convert DB models to DTOs
    task_executions = []
    for action in actions:
        # Calculate duration if completed
        duration = None
        if action.started_at and action.completed_at:
            duration = (action.completed_at - action.started_at).total_seconds()
        
        task_executions.append(
            TaskExecution(
                task_id=action.action_id,
                event_type=action.action_type or "unknown",  # Use action_type from DB
                state=action.status,  # ActionStatus and TaskState have compatible values
                started_at=action.started_at,
                completed_at=action.completed_at,
                duration_seconds=duration,
                progress=None,  # Not tracked in DB yet
            )
        )
    
    return task_executions
