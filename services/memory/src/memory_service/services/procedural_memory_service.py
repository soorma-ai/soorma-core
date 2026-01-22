"""Service layer for Procedural Memory operations."""

from uuid import UUID
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from soorma_common.models import ProceduralMemoryResponse
from memory_service.crud.procedural import search_procedural_memory as crud_get_skills
from memory_service.models.memory import ProceduralMemory


class ProceduralMemoryService:
    """Service for managing procedural memory (skills) with proper transaction boundaries."""
    
    @staticmethod
    def _to_response(memory: ProceduralMemory, score: float = None) -> ProceduralMemoryResponse:
        """Convert database model to response DTO."""
        return ProceduralMemoryResponse(
            id=str(memory.id),
            tenant_id=str(memory.tenant_id),
            user_id=str(memory.user_id),
            skill_name=memory.skill_name,
            description=memory.description,
            parameters=memory.parameters,
            examples=memory.examples,
            metadata=memory.metadata,
            created_at=memory.created_at.isoformat(),
            score=score,
        )
    
    async def get_relevant_skills(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        query: str,
        limit: int = 3,
    ) -> List[ProceduralMemoryResponse]:
        """Get relevant skills for a query."""
        results = await crud_get_skills(db, tenant_id, user_id, query, limit)
        return [self._to_response(memory, score) for memory, score in results]


# Singleton instance for dependency injection
procedural_memory_service = ProceduralMemoryService()
