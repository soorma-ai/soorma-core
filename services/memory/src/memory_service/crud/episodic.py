"""CRUD operations for episodic memory."""

from typing import List, Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from memory_service.models.memory import EpisodicMemory
from soorma_common.models import EpisodicMemoryCreate, EpisodicMemoryResponse
from memory_service.services.embedding import embedding_service
from memory_service.crud._identity import require_platform_tenant_id, scoped_identity_filters


async def create_episodic_memory(
    db: AsyncSession,
    platform_tenant_id: str,
    service_tenant_id: str,
    service_user_id: str,
    data: EpisodicMemoryCreate,
) -> EpisodicMemory:
    """Create a new episodic memory entry."""
    require_platform_tenant_id(platform_tenant_id)
    # Generate embedding
    embedding = await embedding_service.generate_embedding(data.content)

    memory = EpisodicMemory(
        platform_tenant_id=platform_tenant_id,
        service_tenant_id=service_tenant_id,
        service_user_id=service_user_id,
        agent_id=data.agent_id,
        role=data.role,
        content=data.content,
        embedding=embedding,
        memory_metadata=data.metadata,
    )
    db.add(memory)
    await db.flush()
    await db.refresh(memory)
    return memory


async def get_recent_episodic_memory(
    db: AsyncSession,
    platform_tenant_id: str,
    service_tenant_id: str,
    service_user_id: str,
    agent_id: str,
    limit: int = 10,
) -> List[EpisodicMemoryResponse]:
    """Get recent episodic memories for a user/agent pair."""
    require_platform_tenant_id(platform_tenant_id)
    stmt = (
        select(EpisodicMemory)
        .where(
            *scoped_identity_filters(
                EpisodicMemory,
                platform_tenant_id,
                service_tenant_id,
                service_user_id,
            ),
            EpisodicMemory.agent_id == agent_id,
        )
        .order_by(desc(EpisodicMemory.created_at))
        .limit(limit)
    )

    result = await db.execute(stmt)
    memories = result.scalars().all()

    return [
        EpisodicMemoryResponse(
            id=str(m.id),
            tenant_id=m.platform_tenant_id,
            user_id=m.service_user_id or "",
            agent_id=m.agent_id,
            role=m.role,
            content=m.content,
            metadata=m.memory_metadata or {},
            created_at=m.created_at.isoformat(),
        )
        for m in memories
    ]


async def search_episodic_memory(
    db: AsyncSession,
    platform_tenant_id: str,
    service_tenant_id: str,
    service_user_id: str,
    query: str,
    agent_id: str,
    limit: int = 5,
) -> List[EpisodicMemoryResponse]:
    """Search episodic memory using vector similarity."""
    require_platform_tenant_id(platform_tenant_id)
    # Generate query embedding
    query_embedding = await embedding_service.generate_embedding(query)

    # Vector similarity search
    stmt = (
        select(
            EpisodicMemory,
            (1 - EpisodicMemory.embedding.cosine_distance(query_embedding)).label("score"),
        )
        .where(
            *scoped_identity_filters(
                EpisodicMemory,
                platform_tenant_id,
                service_tenant_id,
                service_user_id,
            ),
            EpisodicMemory.agent_id == agent_id,
        )
        .order_by((1 - EpisodicMemory.embedding.cosine_distance(query_embedding)).desc())
        .limit(limit)
    )

    result = await db.execute(stmt)
    rows = result.all()

    return [
        EpisodicMemoryResponse(
            id=str(row.EpisodicMemory.id),
            tenant_id=row.EpisodicMemory.platform_tenant_id,
            user_id=row.EpisodicMemory.service_user_id or "",
            agent_id=row.EpisodicMemory.agent_id,
            role=row.EpisodicMemory.role,
            content=row.EpisodicMemory.content,
            metadata=row.EpisodicMemory.memory_metadata or {},
            created_at=row.EpisodicMemory.created_at.isoformat(),
            score=float(row.score),
        )
        for row in rows
    ]
