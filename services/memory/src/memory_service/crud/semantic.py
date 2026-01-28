"""CRUD operations for semantic memory."""

import hashlib
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from pgvector.sqlalchemy import Vector

from memory_service.models.memory import SemanticMemory
from soorma_common.models import SemanticMemoryCreate, SemanticMemoryResponse
from memory_service.services.embedding import embedding_service


def generate_content_hash(content: str) -> str:
    """Generate SHA-256 hash of content for deduplication."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


async def upsert_semantic_memory(
    db: AsyncSession,
    tenant_id: UUID,
    user_id: str,
    content: str,
    external_id: Optional[str] = None,
    is_public: bool = False,
    metadata: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None,
    source: Optional[str] = None,
) -> SemanticMemory:
    """
    Upsert semantic memory entry with privacy support.
    
    RF-ARCH-012: Upsert by external_id OR content_hash
    RF-ARCH-014: User-scoped privacy (default private, optional public)
    
    Args:
        db: Database session
        tenant_id: Tenant identifier
        user_id: User who owns this knowledge (required)
        content: Text content
        external_id: Optional user-provided ID for versioning
        is_public: If True, visible to all users in tenant. Default False (private).
        metadata: Optional metadata dict
        tags: Optional tags list
        source: Optional source identifier
    
    Returns:
        SemanticMemory: Created or updated memory entry
    
    Behavior:
        - With external_id: Upserts on (tenant_id, user_id, external_id) if private,
                           or (tenant_id, external_id) if public
        - Without external_id: Upserts on (tenant_id, user_id, content_hash) if private,
                              or (tenant_id, content_hash) if public
        - Updates existing entry if constraint matches
        - Creates new entry if no match found
    """
    # Generate content hash
    content_hash = generate_content_hash(content)
    
    # TODO: Optimization opportunity - Reuse embeddings for duplicate content
    # Current: Generate embedding unconditionally (~200-500ms API call + cost)
    # Optimization: Check for existing embedding with same content_hash before generating
    # Decision: Not implementing yet (Stage 2.1) - premature optimization
    # Rationale:
    #   - MVP phase: ship first, measure later
    #   - Adds complexity: extra SELECT query, race conditions, embedding model versioning
    #   - Unknown savings: need production metrics to justify (target: >30% cache hit rate)
    #   - Consider when: >1000 upserts/day OR embedding costs become significant
    # Implementation: SELECT embedding FROM semantic_memories WHERE content_hash=? LIMIT 1
    embedding = await embedding_service.generate_embedding(content)
    
    # Build metadata
    memory_metadata = metadata or {}
    if tags:
        memory_metadata['tags'] = tags
    if source:
        memory_metadata['source'] = source
    
    # Prepare the insert statement with ON CONFLICT DO UPDATE
    # PostgreSQL's INSERT ... ON CONFLICT ... DO UPDATE (upsert)
    stmt = insert(SemanticMemory).values(
        tenant_id=tenant_id,
        user_id=user_id,
        content=content,
        embedding=embedding,
        external_id=external_id,
        content_hash=content_hash,
        is_public=is_public,
        memory_metadata=memory_metadata,
    )
    
    # Determine conflict target based on external_id presence and privacy
    if external_id is not None:
        # Upsert by external_id
        if is_public:
            # Public knowledge: unique per tenant
            conflict_target = ['tenant_id', 'external_id']
            conflict_where = text('external_id IS NOT NULL AND is_public = TRUE')
        else:
            # Private knowledge: unique per user
            conflict_target = ['tenant_id', 'user_id', 'external_id']
            conflict_where = text('external_id IS NOT NULL AND is_public = FALSE')
    else:
        # Upsert by content_hash
        if is_public:
            # Public knowledge: unique per tenant
            conflict_target = ['tenant_id', 'content_hash']
            conflict_where = text('is_public = TRUE')
        else:
            # Private knowledge: unique per user
            conflict_target = ['tenant_id', 'user_id', 'content_hash']
            conflict_where = text('is_public = FALSE')
    
    # Add the ON CONFLICT clause
    # Note: We update all fields including is_public to allow visibility changes
    stmt = stmt.on_conflict_do_update(
        index_elements=conflict_target,
        index_where=conflict_where,
        set_={
            'content': content,
            'embedding': embedding,
            'content_hash': content_hash,
            'is_public': is_public,  # Allow visibility changes on upsert
            'memory_metadata': memory_metadata,
            'updated_at': func.now(),
        }
    ).returning(SemanticMemory)
    
    # Execute the upsert
    result = await db.execute(stmt)
    memory = result.scalar_one()
    
    await db.flush()
    await db.refresh(memory)
    
    return memory


async def create_semantic_memory(
    db: AsyncSession,
    tenant_id: UUID,
    user_id: str,
    data: SemanticMemoryCreate,
) -> SemanticMemory:
    """
    Create a new semantic memory entry (delegates to upsert).
    
    RF-ARCH-014: Requires user_id for privacy support.
    RF-ARCH-012: Uses upsert to prevent duplicates.
    
    This function is kept for backward compatibility but now delegates to upsert_semantic_memory.
    """
    return await upsert_semantic_memory(
        db=db,
        tenant_id=tenant_id,
        user_id=user_id,
        content=data.content,
        external_id=getattr(data, 'external_id', None),
        is_public=getattr(data, 'is_public', False),
        metadata=data.metadata,
    )


async def search_semantic_memory(
    db: AsyncSession,
    tenant_id: UUID,
    user_id: str,
    query: str,
    limit: int = 5,
    include_public: bool = True,
) -> List[SemanticMemoryResponse]:
    """
    Search semantic memory using vector similarity with privacy support.
    
    RF-ARCH-014: Returns user's private knowledge + optional public knowledge.
    
    Args:
        db: Database session
        tenant_id: Tenant identifier
        user_id: User performing the query
        query: Query text
        limit: Maximum number of results
        include_public: If True, includes public knowledge from all users
    
    Returns:
        List of SemanticMemoryResponse sorted by relevance score
    """
    # Generate query embedding
    query_embedding = await embedding_service.generate_embedding(query)

    # Build WHERE clause for privacy
    if include_public:
        # Return user's private knowledge OR public knowledge in tenant
        where_clause = (
            (SemanticMemory.tenant_id == tenant_id) &
            (
                (SemanticMemory.user_id == user_id) |
                (SemanticMemory.is_public == True)
            )
        )
    else:
        # Return only user's private knowledge
        where_clause = (
            (SemanticMemory.tenant_id == tenant_id) &
            (SemanticMemory.user_id == user_id)
        )

    # Vector similarity search using cosine distance
    stmt = (
        select(
            SemanticMemory,
            (1 - SemanticMemory.embedding.cosine_distance(query_embedding)).label("score"),
        )
        .where(where_clause)
        .order_by((1 - SemanticMemory.embedding.cosine_distance(query_embedding)).desc())
        .limit(limit)
    )

    result = await db.execute(stmt)
    rows = result.all()

    return [
        SemanticMemoryResponse(
            id=str(row.SemanticMemory.id),
            tenant_id=str(row.SemanticMemory.tenant_id),
            user_id=row.SemanticMemory.user_id,
            content=row.SemanticMemory.content,
            metadata=row.SemanticMemory.memory_metadata,
            external_id=row.SemanticMemory.external_id,
            is_public=row.SemanticMemory.is_public,
            created_at=row.SemanticMemory.created_at.isoformat(),
            updated_at=row.SemanticMemory.updated_at.isoformat(),
            score=row.score,
        )
        for row in rows
    ]
