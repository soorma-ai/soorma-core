"""Working memory API endpoints."""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status

from memory_service.core.dependencies import TenantContext, get_tenant_context
from soorma_common.models import (
    WorkingMemorySet,
    WorkingMemoryResponse,
    WorkingMemoryDeleteKeyResponse,
    WorkingMemoryDeletePlanResponse,
)
from memory_service.services.working_memory_service import working_memory_service

router = APIRouter(prefix="/working", tags=["Working Memory"])


@router.put("/{plan_id}/{key}", response_model=WorkingMemoryResponse)
async def set_plan_state(
    plan_id: UUID,
    key: str,
    data: WorkingMemorySet,
    context: TenantContext = Depends(get_tenant_context),
):
    """Set or update working memory value for a plan."""
    return await working_memory_service.set(
        context.db,
        context.tenant_id,
        context.user_id,
        plan_id,
        key,
        data,
    )


@router.get("/{plan_id}/{key}", response_model=WorkingMemoryResponse)
async def get_plan_state(
    plan_id: UUID,
    key: str,
    context: TenantContext = Depends(get_tenant_context),
):
    """Get working memory value for a plan."""
    result = await working_memory_service.get(
        context.db,
        context.tenant_id,
        context.user_id,
        plan_id,
        key,
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Working memory not found: {plan_id}/{key}",
        )
    return result


@router.delete("/{plan_id}/{key}", response_model=WorkingMemoryDeleteKeyResponse)
async def delete_plan_state_key(
    plan_id: UUID,
    key: str,
    context: TenantContext = Depends(get_tenant_context),
):
    """Delete a single working memory key for a plan."""
    result = await working_memory_service.delete_key(
        context.db,
        context.tenant_id,
        context.user_id,
        plan_id,
        key,
    )
    if not result.deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Working memory not found: {plan_id}/{key}",
        )
    return result


@router.delete("/{plan_id}", response_model=WorkingMemoryDeletePlanResponse)
async def delete_plan_state(
    plan_id: UUID,
    context: TenantContext = Depends(get_tenant_context),
):
    """Delete all working memory for a plan."""
    return await working_memory_service.delete_plan(
        context.db,
        context.tenant_id,
        context.user_id,
        plan_id,
    )
