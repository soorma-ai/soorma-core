"""Service layer for Semantic Memory operations with upsert and privacy support.

RF-ARCH-012: Upsert via external_id or content_hash
RF-ARCH-014: User-scoped privacy (default private, optional public)
"""

from uuid import UUID
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from soorma_common.models import SemanticMemoryCreate, SemanticMemoryResponse
from memory_service.models.memory import SemanticMemory


class SemanticMemoryService:
    """Service for managing semantic memory (knowledge) with proper transaction boundaries.
    
    Provides upsert and privacy-aware operations.
    """
    
    @staticmethod
    def _to_response(memory: SemanticMemory, score: float = None) -> SemanticMemoryResponse:
        """Convert database model to response DTO."""
        return SemanticMemoryResponse(
            id=str(memory.id),
            tenant_id=str(memory.tenant_id),
            user_id=memory.user_id,
            content=memory.content,
            external_id=memory.external_id,
            is_public=memory.is_public,
            metadata=memory.memory_metadata or {},
            created_at=memory.created_at.isoformat(),
            updated_at=memory.updated_at.isoformat(),
            score=score,
        )
    
    async def store_knowledge(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        user_id: str,
        data: SemanticMemoryCreate,
    ) -> SemanticMemoryResponse:
        """
        Store or update semantic memory (knowledge) - upsert behavior.
        
        RF-ARCH-012: Upserts by external_id (if provided) or content_hash (automatic)
        RF-ARCH-014: Defaults to private (user-scoped)
        
        Transaction boundary: Commits after successful storage.
        
        Args:
            db: Database session
            tenant_id: Tenant identifier
            user_id: User who owns this knowledge
            data: SemanticMemoryCreate DTO
        
        Returns:
            SemanticMemoryResponse
        """
        # Import here to avoid circular imports
        from memory_service.crud.semantic import upsert_semantic_memory
        
        memory = await upsert_semantic_memory(
            db=db,
            tenant_id=tenant_id,
            user_id=user_id,
            content=data.content,
            external_id=getattr(data, 'external_id', None),
            is_public=getattr(data, 'is_public', False),
            metadata=data.metadata,
            tags=getattr(data, 'tags', None),
            source=getattr(data, 'source', None),
        )
        await db.commit()
        
        return self._to_response(memory)
    
    async def query_knowledge(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        user_id: str,
        query: str,
        limit: int = 5,
        include_public: bool = True,
    ) -> List[SemanticMemoryResponse]:
        """
        Query semantic memory by similarity with privacy support.
        
        RF-ARCH-014: Returns user's private knowledge + optional public knowledge.
        
        Args:
            db: Database session
            tenant_id: Tenant identifier
            user_id: User performing the query
            query: Query text
            limit: Maximum number of results
            include_public: If True, includes public knowledge from all users
        
        Returns:
            List of SemanticMemoryResponse sorted by similarity score
        """
        # Import here to avoid circular imports
        from memory_service.crud.semantic import search_semantic_memory
        
        return await search_semantic_memory(
            db=db,
            tenant_id=tenant_id,
            user_id=user_id,
            query=query,
            limit=limit,
            include_public=include_public,
        )
    
    async def ingest(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        user_id: str,
        data: SemanticMemoryCreate,
    ) -> SemanticMemoryResponse:
        """
        Ingest new semantic memory (knowledge) - backward compatibility wrapper.
        
        Delegates to store_knowledge() which provides upsert behavior.
        """
        return await self.store_knowledge(db, tenant_id, user_id, data)
    
    async def search(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        user_id: str,
        query: str,
        limit: int = 5,
    ) -> List[SemanticMemoryResponse]:
        """Search semantic memory by similarity - backward compatibility wrapper.
        
        Delegates to query_knowledge() which provides privacy-aware results.
        """
        return await self.query_knowledge(
            db=db,
            tenant_id=tenant_id,
            user_id=user_id,
            query=query,
            limit=limit,
            include_public=True,  # Default: include public knowledge
        )


# Singleton instance for dependency injection
semantic_memory_service = SemanticMemoryService()
