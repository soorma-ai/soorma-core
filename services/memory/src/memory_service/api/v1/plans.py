"""Plans API endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query

from memory_service.core.dependencies import TenantContext, get_tenant_context
from soorma_common.models import (
    PlanCreate,
    PlanUpdate,
    PlanSummary,
)
from memory_service.services.plan_service import plan_service

router = APIRouter(prefix="/plans", tags=["Plans"])


@router.post("", response_model=PlanSummary, status_code=status.HTTP_201_CREATED)
async def create_plan_endpoint(
    data: PlanCreate,
    context: TenantContext = Depends(get_tenant_context),
):
    """Create a new plan."""
    return await plan_service.create(context.db, context.tenant_id, context.user_id, data)


@router.get("", response_model=list[PlanSummary])
async def list_plans_endpoint(
    status_filter: Optional[str] = Query(None, alias="status"),
    session_id: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    context: TenantContext = Depends(get_tenant_context),
):
    """List plans for the authenticated user."""
    return await plan_service.list(
        context.db, 
        context.tenant_id, 
        context.user_id, 
        status_filter, 
        session_id, 
        limit
    )


@router.get("/{plan_id}", response_model=PlanSummary)
async def get_plan_endpoint(
    plan_id: str,
    context: TenantContext = Depends(get_tenant_context),
):
    """Get a specific plan by ID."""
    result = await plan_service.get(context.db, context.tenant_id, plan_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan not found: {plan_id}",
        )
    return result


@router.put("/{plan_id}", response_model=PlanSummary)
async def update_plan_endpoint(
    plan_id: str,
    data: PlanUpdate,
    context: TenantContext = Depends(get_tenant_context),
):
    """Update plan status."""
    result = await plan_service.update(context.db, context.tenant_id, plan_id, data)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan not found: {plan_id}",
        )
    return result


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plan_endpoint(
    plan_id: str,
    context: TenantContext = Depends(get_tenant_context),
):
    """Delete plan."""
    deleted = await plan_service.delete(context.db, context.tenant_id, plan_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan not found: {plan_id}",
        )
