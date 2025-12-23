"""Working memory API endpoints."""

from uuid import UUID
from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from memory_service.core.database import get_db, set_session_context
from memory_service.core.middleware import get_tenant_id
from soorma_common.models import WorkingMemorySet, WorkingMemoryResponse
from memory_service.crud.working import set_working_memory, get_working_memory

router = APIRouter(prefix="/working", tags=["Working Memory"])


@router.put("/{plan_id}/{key}", response_model=WorkingMemoryResponse)
async def set_plan_state(
    request: Request,
    plan_id: UUID,
    key: str,
    data: WorkingMemorySet,
    db: AsyncSession = Depends(get_db),
):
    """Set or update working memory value for a plan."""
    tenant_id = UUID(get_tenant_id(request))
    await set_session_context(db, str(tenant_id), str(tenant_id))

    memory = await set_working_memory(db, tenant_id, plan_id, key, data)
    return WorkingMemoryResponse(
        id=str(memory.id),
        tenant_id=str(memory.tenant_id),
        plan_id=str(memory.plan_id),
        key=memory.key,
        value=memory.value,
        updated_at=memory.updated_at.isoformat(),
    )


@router.get("/{plan_id}/{key}", response_model=WorkingMemoryResponse)
async def get_plan_state(
    request: Request,
    plan_id: UUID,
    key: str,
    db: AsyncSession = Depends(get_db),
):
    """Get working memory value for a plan."""
    tenant_id = UUID(get_tenant_id(request))
    await set_session_context(db, str(tenant_id), str(tenant_id))

    memory = await get_working_memory(db, tenant_id, plan_id, key)
    if not memory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Working memory not found: {plan_id}/{key}",
        )

    return WorkingMemoryResponse(
        id=str(memory.id),
        tenant_id=str(memory.tenant_id),
        plan_id=str(memory.plan_id),
        key=memory.key,
        value=memory.value,
        updated_at=memory.updated_at.isoformat(),
    )
