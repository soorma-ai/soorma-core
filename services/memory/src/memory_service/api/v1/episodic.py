"""Episodic memory API endpoints."""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession

from memory_service.core.database import get_db, set_session_context
from memory_service.core.middleware import get_tenant_id
from soorma_common.models import EpisodicMemoryCreate, EpisodicMemoryResponse
from memory_service.crud.episodic import (
    create_episodic_memory,
    get_recent_episodic_memory,
    search_episodic_memory,
)

router = APIRouter(prefix="/episodic", tags=["Episodic Memory"])


@router.post("", response_model=EpisodicMemoryResponse, status_code=201)
async def log_episodic_memory(
    request: Request,
    data: EpisodicMemoryCreate,
    user_id: str = Query(..., description="User identifier"),
    db: AsyncSession = Depends(get_db),
):
    """Log an interaction to episodic memory.

    The service automatically generates embeddings for the content.
    
    Args:
        user_id: User identifier (required in single-tenant mode)
    """
    tenant_id = UUID(get_tenant_id(request))
    user_id_uuid = UUID(user_id)
    
    await set_session_context(db, str(tenant_id), str(user_id_uuid))

    memory = await create_episodic_memory(db, tenant_id, user_id_uuid, data)
    return EpisodicMemoryResponse(
        id=str(memory.id),
        tenant_id=str(memory.tenant_id),
        user_id=str(memory.user_id),
        agent_id=memory.agent_id,
        role=memory.role,
        content=memory.content,
        metadata=memory.memory_metadata,
        created_at=memory.created_at.isoformat(),
    )


@router.get("/recent", response_model=List[EpisodicMemoryResponse])
async def get_recent_history(
    request: Request,
    agent_id: str = Query(..., description="Agent identifier"),
    user_id: str = Query(..., description="User identifier"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of results"),
    db: AsyncSession = Depends(get_db),
):
    """Get recent interaction history (context window).
    
    Args:
        user_id: User identifier (required in single-tenant mode)
    """
    tenant_id = UUID(get_tenant_id(request))
    user_id_uuid = UUID(user_id)
    
    await set_session_context(db, str(tenant_id), str(user_id_uuid))

    results = await get_recent_episodic_memory(db, tenant_id, user_id_uuid, agent_id, limit)
    return results


@router.get("/search", response_model=List[EpisodicMemoryResponse])
async def search_episodic(
    request: Request,
    agent_id: str = Query(..., description="Agent identifier"),
    q: str = Query(..., description="Search query"),
    user_id: str = Query(..., description="User identifier"),
    limit: int = Query(5, ge=1, le=50, description="Maximum number of results"),
    db: AsyncSession = Depends(get_db),
):
    """Search episodic memory using vector similarity (long-term recall).
    
    Args:
        user_id: User identifier (required in single-tenant mode)
    """
    tenant_id = UUID(get_tenant_id(request))
    user_id_uuid = UUID(user_id)
    
    await set_session_context(db, str(tenant_id), str(user_id_uuid))

    results = await search_episodic_memory(db, tenant_id, user_id_uuid, agent_id, q, limit)
    return results
