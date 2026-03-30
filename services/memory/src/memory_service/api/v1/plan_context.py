"""Plan context API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from memory_service.core.dependencies import TenantContext, require_user_tenant_context
from soorma_common.models import (
    PlanContextCreate,
    PlanContextUpdate,
    PlanContextResponse,
)
from memory_service.services.plan_context_service import plan_context_service

router = APIRouter(prefix="/plan-context", tags=["Plan Context"])


@router.post("", response_model=PlanContextResponse, status_code=status.HTTP_200_OK)
async def store_plan_context_endpoint(
    data: PlanContextCreate,
    context: TenantContext = Depends(require_user_tenant_context),
):
    """Store plan context (insert or update if exists)."""
    return await plan_context_service.upsert(
        context.db,
        context.platform_tenant_id,
        context.service_tenant_id,
        context.service_user_id,
        data,
    )


@router.get("/{plan_id}", response_model=PlanContextResponse)
async def get_plan_context_endpoint(
    plan_id: str,
    context: TenantContext = Depends(require_user_tenant_context),
):
    """Get plan context by plan ID."""
    result = await plan_context_service.get(
        context.db,
        context.platform_tenant_id,
        context.service_tenant_id,
        context.service_user_id,
        plan_id,
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan context not found: {plan_id}",
        )
    return result


@router.put("/{plan_id}", response_model=PlanContextResponse)
async def update_plan_context_endpoint(
    plan_id: str,
    data: PlanContextUpdate,
    context: TenantContext = Depends(require_user_tenant_context),
):
    """Update plan context."""
    result = await plan_context_service.update(
        context.db,
        context.platform_tenant_id,
        context.service_tenant_id,
        context.service_user_id,
        plan_id,
        data,
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan context not found: {plan_id}",
        )
    return result


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plan_context_endpoint(
    plan_id: str,
    context: TenantContext = Depends(require_user_tenant_context),
):
    """Delete plan context."""
    deleted = await plan_context_service.delete(
        context.db,
        context.platform_tenant_id,
        context.service_tenant_id,
        context.service_user_id,
        plan_id,
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan context not found: {plan_id}",
        )


@router.get("/by-correlation/{correlation_id}", response_model=PlanContextResponse)
async def get_plan_by_correlation_endpoint(
    correlation_id: str,
    context: TenantContext = Depends(require_user_tenant_context),
):
    """Find plan by correlation ID."""
    result = await plan_context_service.get_by_correlation(
        context.db,
        context.platform_tenant_id,
        context.service_tenant_id,
        context.service_user_id,
        correlation_id,
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan not found for correlation ID: {correlation_id}",
        )
    return result
