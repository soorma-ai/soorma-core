"""Service layer for Semantic Memory operations."""

from uuid import UUID
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from soorma_common.models import SemanticMemoryCreate, SemanticMemoryResponse
from memory_service.crud.semantic import (
    create_semantic_memory as crud_ingest,
    search_semantic_memory as crud_search,
)
from memory_service.models.memory import SemanticMemory


class SemanticMemoryService:
    """Service for managing semantic memory (knowledge) with proper transaction boundaries."""
    
    @staticmethod
    def _to_response(memory: SemanticMemory, score: float = None) -> SemanticMemoryResponse:
        """Convert database model to response DTO."""
        return SemanticMemoryResponse(
            id=str(memory.id),
            tenant_id=str(memory.tenant_id),
            content=memory.content,
            metadata=memory.memory_metadata or {},
            created_at=memory.created_at.isoformat(),
            updated_at=memory.updated_at.isoformat(),
            score=score,
        )
    
    async def ingest(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        data: SemanticMemoryCreate,
    ) -> SemanticMemoryResponse:
        """
        Ingest new semantic memory (knowledge).
        
        Transaction boundary: Commits after successful ingestion.
        """
        memory = await crud_ingest(db, tenant_id, data)
        await db.commit()
        
        return self._to_response(memory)
    
    async def search(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        query: str,
        limit: int = 5,
    ) -> List[SemanticMemoryResponse]:
        """Search semantic memory by similarity."""
        # CRUD layer already returns SemanticMemoryResponse objects with scores
        return await crud_search(db, tenant_id, query, limit)


# Singleton instance for dependency injection
semantic_memory_service = SemanticMemoryService()
