"""Semantic memory API endpoints with upsert and privacy support.

RF-ARCH-012: Upsert via external_id or content_hash
RF-ARCH-014: User-scoped privacy (default private, optional public)
"""

from fastapi import APIRouter, Depends, Query

from memory_service.core.dependencies import TenantContext, get_tenant_context
from soorma_common.models import SemanticMemoryCreate, SemanticMemoryResponse
from memory_service.services.semantic_memory_service import semantic_memory_service

router = APIRouter(prefix="/semantic", tags=["Semantic Memory"])


@router.post("", response_model=SemanticMemoryResponse, status_code=201)
async def store_knowledge(
    data: SemanticMemoryCreate,
    context: TenantContext = Depends(get_tenant_context),
):
    """Store or update knowledge in semantic memory (upsert).
    
    RF-ARCH-012: Upserts by external_id (if provided) or content_hash (automatic).
    RF-ARCH-014: Defaults to private (user-scoped). Use is_public=true for shared knowledge.
    
    Behavior:
    - With external_id: Updates existing knowledge with same external_id
    - Without external_id: Prevents duplicate content via content_hash
    - Privacy: Knowledge is private by default (only visible to this user)
    
    The service automatically generates embeddings for the content.
    """
    return await semantic_memory_service.store_knowledge(
        context.db,
        context.tenant_id,
        str(context.user_id),  # Pass user_id from context
        data
    )


@router.post("/query", response_model=list[SemanticMemoryResponse])
async def query_knowledge(
    query: str = Query(..., description="Search query text"),
    limit: int = Query(5, ge=1, le=50, description="Maximum number of results"),
    include_public: bool = Query(True, description="Include public knowledge from all users"),
    context: TenantContext = Depends(get_tenant_context),
):
    """Query semantic memory using vector similarity with privacy support.
    
    RF-ARCH-014: Returns your private knowledge + optional public knowledge from tenant.
    
    Args:
        query: Text to search for semantically
        limit: Maximum results to return
        include_public: If true, also returns public knowledge from all users in tenant
    
    Returns:
        List of knowledge entries sorted by similarity score (highest first)
    """
    return await semantic_memory_service.query_knowledge(
        context.db,
        context.tenant_id,
        str(context.user_id),  # Pass user_id from context
        query,
        limit,
        include_public
    )


@router.get("/search", response_model=list[SemanticMemoryResponse])
async def search_semantic(
    q: str = Query(..., description="Search query"),
    limit: int = Query(5, ge=1, le=50, description="Maximum number of results"),
    context: TenantContext = Depends(get_tenant_context),
):
    """Search semantic memory using vector similarity (backward compatibility endpoint).
    
    Deprecated: Use POST /v1/memory/semantic/query instead for consistency.
    
    This endpoint maintains backward compatibility and includes public knowledge.
    """
    return await semantic_memory_service.search(
        context.db,
        context.tenant_id,
        str(context.user_id),
        q,
        limit
    )
