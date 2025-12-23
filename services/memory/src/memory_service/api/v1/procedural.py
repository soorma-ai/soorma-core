"""Procedural memory API endpoints."""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession

from memory_service.core.database import get_db, set_session_context
from memory_service.core.middleware import get_tenant_id, get_user_id
from soorma_common.models import ProceduralMemoryResponse
from memory_service.crud.procedural import search_procedural_memory

router = APIRouter(prefix="/procedural", tags=["Procedural Memory"])


@router.get("/context", response_model=List[ProceduralMemoryResponse])
async def get_procedural_context(
    request: Request,
    agent_id: str = Query(..., description="Agent identifier"),
    q: str = Query(..., description="Task/query context"),
    limit: int = Query(3, ge=1, le=20, description="Maximum number of results"),
    db: AsyncSession = Depends(get_db),
):
    """Fetch relevant procedural knowledge (skills, prompts, rules).

    Returns system prompts and few-shot examples matching the task context.
    """
    tenant_id = UUID(get_tenant_id(request))
    user_id = UUID(get_user_id(request))
    await set_session_context(db, str(tenant_id), str(user_id))

    results = await search_procedural_memory(db, tenant_id, user_id, agent_id, q, limit)
    return results
