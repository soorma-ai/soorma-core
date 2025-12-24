"""Semantic memory API endpoints."""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession

from memory_service.core.database import get_db, set_session_context
from memory_service.core.middleware import get_tenant_id
from soorma_common.models import SemanticMemoryCreate, SemanticMemoryResponse
from memory_service.crud.semantic import create_semantic_memory, search_semantic_memory

router = APIRouter(prefix="/semantic", tags=["Semantic Memory"])


@router.post("", response_model=SemanticMemoryResponse, status_code=201)
async def ingest_semantic_memory(
    request: Request,
    data: SemanticMemoryCreate,
    db: AsyncSession = Depends(get_db),
):
    """Ingest knowledge into semantic memory.

    The service automatically generates embeddings for the content.
    """
    tenant_id = UUID(get_tenant_id(request))
    await set_session_context(db, str(tenant_id), str(tenant_id))

    memory = await create_semantic_memory(db, tenant_id, data)
    return SemanticMemoryResponse(
        id=str(memory.id),
        tenant_id=str(memory.tenant_id),
        content=memory.content,
        metadata=memory.memory_metadata,
        created_at=memory.created_at.isoformat(),
        updated_at=memory.updated_at.isoformat(),
    )


@router.get("/search", response_model=List[SemanticMemoryResponse])
async def search_semantic(
    request: Request,
    q: str = Query(..., description="Search query"),
    limit: int = Query(5, ge=1, le=50, description="Maximum number of results"),
    db: AsyncSession = Depends(get_db),
):
    """Search semantic memory using vector similarity."""
    tenant_id = UUID(get_tenant_id(request))
    await set_session_context(db, str(tenant_id), str(tenant_id))

    results = await search_semantic_memory(db, tenant_id, q, limit)
    return results
