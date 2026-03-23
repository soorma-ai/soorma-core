"""Service layer for Episodic Memory operations."""

from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from soorma_common.models import EpisodicMemoryCreate, EpisodicMemoryResponse
from memory_service.crud.episodic import (
    create_episodic_memory as crud_log,
    get_recent_episodic_memory as crud_get_recent,
    search_episodic_memory as crud_search,
)
from memory_service.models.memory import EpisodicMemory


class EpisodicMemoryService:
    """Service for managing episodic memory (interactions) with proper transaction boundaries."""
    
    @staticmethod
    def _to_response(memory: EpisodicMemory, score: float = None) -> EpisodicMemoryResponse:
        """Convert database model to response DTO."""
        return EpisodicMemoryResponse(
            id=str(memory.id),
            tenant_id=memory.platform_tenant_id,
            user_id=memory.service_user_id or "",
            agent_id=memory.agent_id,
            role=memory.role,
            content=memory.content,
            metadata=memory.memory_metadata or {},
            created_at=memory.created_at.isoformat(),
            score=score,
        )
    
    async def log(
        self,
        db: AsyncSession,
        platform_tenant_id: str,
        service_tenant_id: str,
        service_user_id: str,
        data: EpisodicMemoryCreate,
    ) -> EpisodicMemoryResponse:
        """
        Log new episodic memory (interaction).
        
        Transaction boundary: Commits after successful logging.
        """
        memory = await crud_log(db, platform_tenant_id, service_tenant_id, service_user_id, data)
        await db.commit()
        
        return self._to_response(memory)
    
    async def get_recent(
        self,
        db: AsyncSession,
        platform_tenant_id: str,
        service_tenant_id: str,
        service_user_id: str,
        agent_id: str,
        limit: int = 10,
    ) -> List[EpisodicMemoryResponse]:
        """Get recent episodic memories for a user and agent."""
        # CRUD layer already returns EpisodicMemoryResponse objects
        return await crud_get_recent(db, platform_tenant_id, service_tenant_id, service_user_id, agent_id, limit)
    
    async def search(
        self,
        db: AsyncSession,
        platform_tenant_id: str,
        service_tenant_id: str,
        service_user_id: str,
        query: str,
        agent_id: str = None,
        limit: int = 5,
    ) -> List[EpisodicMemoryResponse]:
        """Search episodic memories by similarity."""
        # CRUD layer already returns EpisodicMemoryResponse objects with scores
        return await crud_search(db, platform_tenant_id, service_tenant_id, service_user_id, query, agent_id, limit)


# Singleton instance for dependency injection
episodic_memory_service = EpisodicMemoryService()
