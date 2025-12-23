"""CRUD operations for procedural memory."""

from typing import List
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from memory_service.models.memory import ProceduralMemory
from soorma_common.models import ProceduralMemoryResponse
from memory_service.services.embedding import embedding_service


async def search_procedural_memory(
    db: AsyncSession,
    tenant_id: UUID,
    user_id: UUID,
    agent_id: str,
    query: str,
    limit: int = 3,
) -> List[ProceduralMemoryResponse]:
    """Search procedural memory using vector similarity."""
    # Generate query embedding
    query_embedding = await embedding_service.generate_embedding(query)

    # Vector similarity search
    stmt = (
        select(
            ProceduralMemory,
            (1 - ProceduralMemory.embedding.cosine_distance(query_embedding)).label("score"),
        )
        .where(
            ProceduralMemory.tenant_id == tenant_id,
            ProceduralMemory.user_id == user_id,
            ProceduralMemory.agent_id == agent_id,
        )
        .order_by((1 - ProceduralMemory.embedding.cosine_distance(query_embedding)).desc())
        .limit(limit)
    )

    result = await db.execute(stmt)
    rows = result.all()

    return [
        ProceduralMemoryResponse(
            id=str(row.ProceduralMemory.id),
            tenant_id=str(row.ProceduralMemory.tenant_id),
            user_id=str(row.ProceduralMemory.user_id),
            agent_id=row.ProceduralMemory.agent_id,
            trigger_condition=row.ProceduralMemory.trigger_condition,
            procedure_type=row.ProceduralMemory.procedure_type,
            content=row.ProceduralMemory.content,
            created_at=row.ProceduralMemory.created_at.isoformat(),
            score=float(row.score),
        )
        for row in rows
    ]
