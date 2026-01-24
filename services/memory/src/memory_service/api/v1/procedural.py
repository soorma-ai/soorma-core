"""Procedural memory API endpoints."""

from fastapi import APIRouter, Depends, Query

from memory_service.core.dependencies import TenantContext, get_tenant_context
from soorma_common.models import ProceduralMemoryResponse
from memory_service.services.procedural_memory_service import procedural_memory_service

router = APIRouter(prefix="/procedural", tags=["Procedural Memory"])


@router.get("/context", response_model=list[ProceduralMemoryResponse])
async def get_procedural_context(
    agent_id: str = Query(..., description="Agent identifier"),
    q: str = Query(..., description="Task/query context"),
    limit: int = Query(3, ge=1, le=20, description="Maximum number of results"),
    context: TenantContext = Depends(get_tenant_context),
):
    """Fetch relevant procedural knowledge (skills, prompts, rules).

    Returns system prompts and few-shot examples matching the task context.
    """
    return await procedural_memory_service.get_relevant_skills(
        context.db, context.tenant_id, context.user_id, q, limit
    )
