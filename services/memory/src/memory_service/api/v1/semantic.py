"""Semantic memory API endpoints."""

from fastapi import APIRouter, Depends, Query

from memory_service.core.dependencies import TenantContext, get_tenant_context
from soorma_common.models import SemanticMemoryCreate, SemanticMemoryResponse
from memory_service.services.semantic_memory_service import semantic_memory_service

router = APIRouter(prefix="/semantic", tags=["Semantic Memory"])


@router.post("", response_model=SemanticMemoryResponse, status_code=201)
async def ingest_semantic_memory(
    data: SemanticMemoryCreate,
    context: TenantContext = Depends(get_tenant_context),
):
    """Ingest knowledge into semantic memory.

    The service automatically generates embeddings for the content.
    """
    return await semantic_memory_service.ingest(context.db, context.tenant_id, data)


@router.get("/search", response_model=list[SemanticMemoryResponse])
async def search_semantic(
    q: str = Query(..., description="Search query"),
    limit: int = Query(5, ge=1, le=50, description="Maximum number of results"),
    context: TenantContext = Depends(get_tenant_context),
):
    """Search semantic memory using vector similarity."""
    return await semantic_memory_service.search(context.db, context.tenant_id, q, limit)
