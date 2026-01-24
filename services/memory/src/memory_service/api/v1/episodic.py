"""Episodic memory API endpoints."""

from fastapi import APIRouter, Depends, Query

from memory_service.core.dependencies import TenantContext, get_tenant_context
from soorma_common.models import EpisodicMemoryCreate, EpisodicMemoryResponse
from memory_service.services.episodic_memory_service import episodic_memory_service

router = APIRouter(prefix="/episodic", tags=["Episodic Memory"])


@router.post("", response_model=EpisodicMemoryResponse, status_code=201)
async def log_episodic_memory(
    data: EpisodicMemoryCreate,
    context: TenantContext = Depends(get_tenant_context),
):
    """Log an interaction to episodic memory.

    The service automatically generates embeddings for the content.
    """
    return await episodic_memory_service.log(context.db, context.tenant_id, context.user_id, data)


@router.get("/recent", response_model=list[EpisodicMemoryResponse])
async def get_recent_history(
    agent_id: str = Query(..., description="Agent identifier"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of results"),
    context: TenantContext = Depends(get_tenant_context),
):
    """Get recent interaction history (context window)."""
    return await episodic_memory_service.get_recent(
        context.db, context.tenant_id, context.user_id, agent_id, limit
    )


@router.get("/search", response_model=list[EpisodicMemoryResponse])
async def search_episodic(
    agent_id: str = Query(..., description="Agent identifier"),
    q: str = Query(..., description="Search query"),
    limit: int = Query(5, ge=1, le=50, description="Maximum number of results"),
    context: TenantContext = Depends(get_tenant_context),
):
    """Search episodic memories using vector similarity."""
    return await episodic_memory_service.search(
        context.db, context.tenant_id, context.user_id, q, agent_id, limit
    )
