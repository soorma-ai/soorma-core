"""Service layer for Procedural Memory operations."""

from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from soorma_common.models import ProceduralMemoryResponse
from memory_service.crud.procedural import search_procedural_memory as crud_get_skills
from memory_service.models.memory import ProceduralMemory


class ProceduralMemoryService:
    """Service for managing procedural memory (skills) with proper transaction boundaries."""
    
    async def get_relevant_skills(
        self,
        db: AsyncSession,
        platform_tenant_id: str,
        service_tenant_id: str,
        service_user_id: str,
        agent_id: str,
        query: str,
        limit: int = 3,
    ) -> List[ProceduralMemoryResponse]:
        """Get relevant skills for a query. CRUD layer returns ProceduralMemoryResponse directly."""
        return await crud_get_skills(db, platform_tenant_id, service_tenant_id, service_user_id, agent_id, query, limit)


# Singleton instance for dependency injection
procedural_memory_service = ProceduralMemoryService()
