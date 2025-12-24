"""CRUD operations for semantic memory."""

from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pgvector.sqlalchemy import Vector

from memory_service.models.memory import SemanticMemory
from soorma_common.models import SemanticMemoryCreate, SemanticMemoryResponse
from memory_service.services.embedding import embedding_service


async def create_semantic_memory(
    db: AsyncSession,
    tenant_id: UUID,
    data: SemanticMemoryCreate,
) -> SemanticMemory:
    """Create a new semantic memory entry."""
    # Generate embedding
    embedding = await embedding_service.generate_embedding(data.content)

    memory = SemanticMemory(
        tenant_id=tenant_id,
        content=data.content,
        embedding=embedding,
        memory_metadata=data.metadata,
    )
    db.add(memory)
    await db.flush()
    await db.refresh(memory)
    return memory


async def search_semantic_memory(
    db: AsyncSession,
    tenant_id: UUID,
    query: str,
    limit: int = 5,
) -> List[SemanticMemoryResponse]:
    """Search semantic memory using vector similarity."""
    # Generate query embedding
    query_embedding = await embedding_service.generate_embedding(query)

    # Vector similarity search using cosine distance
    stmt = (
        select(
            SemanticMemory,
            (1 - SemanticMemory.embedding.cosine_distance(query_embedding)).label("score"),
        )
        .where(SemanticMemory.tenant_id == tenant_id)
        .order_by((1 - SemanticMemory.embedding.cosine_distance(query_embedding)).desc())
        .limit(limit)
    )

    result = await db.execute(stmt)
    rows = result.all()

    return [
        SemanticMemoryResponse(
            id=str(row.SemanticMemory.id),
            tenant_id=str(row.SemanticMemory.tenant_id),
            content=row.SemanticMemory.content,
            metadata=row.SemanticMemory.memory_metadata,
            created_at=row.SemanticMemory.created_at.isoformat(),
            updated_at=row.SemanticMemory.updated_at.isoformat(),
            score=float(row.score),
        )
        for row in rows
    ]
