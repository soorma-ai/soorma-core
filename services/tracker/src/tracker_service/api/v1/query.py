"""Query API endpoints for Tracker Service.

This module provides read-only query endpoints for:
- Plan execution progress
- Action execution history
- Event timelines
- Agent metrics
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Header, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from soorma_common import (
    PlanProgress as PlanProgressDTO,
    TaskExecution,
    EventTimeline,
    AgentMetrics,
    PlanExecution,
    DelegationGroup,
)
from tracker_service.core.db import get_db
from tracker_service.models import db as db_models


router = APIRouter(prefix="/v1/tracker", tags=["tracker"])


@router.get("/plans/{plan_id}", response_model=PlanProgressDTO)
async def get_plan_progress(
    plan_id: str,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    x_user_id: str = Header(..., alias="X-User-ID"),
    db: AsyncSession = Depends(get_db),
) -> PlanProgressDTO:
    """
    Get plan execution progress.
    
    Args:
        plan_id: Plan identifier
        x_tenant_id: Tenant ID from header (multi-tenancy)
        x_user_id: User ID from header (multi-tenancy)
        db: Database session
    
    Returns:
        PlanProgress with execution status and metrics
    
    Raises:
        HTTPException: 404 if plan not found
    """
    # Query plan_progress with tenant filtering
    stmt = select(db_models.PlanProgress).where(
        db_models.PlanProgress.plan_id == plan_id,
        db_models.PlanProgress.tenant_id == x_tenant_id,
    )
    result = await db.execute(stmt)
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
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    x_user_id: str = Header(..., alias="X-User-ID"),
    db: AsyncSession = Depends(get_db),
) -> List[TaskExecution]:
    """
    Get all action executions for a plan.
    
    Args:
        plan_id: Plan identifier
        x_tenant_id: Tenant ID from header
        x_user_id: User ID from header
        db: Database session
    
    Returns:
        List of TaskExecution records (may be empty)
    """
    # Query action_progress with tenant + plan filtering
    stmt = select(db_models.ActionProgress).where(
        db_models.ActionProgress.plan_id == plan_id,
        db_models.ActionProgress.tenant_id == x_tenant_id,
    ).order_by(db_models.ActionProgress.started_at)
    
    result = await db.execute(stmt)
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
