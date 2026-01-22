"""Service layer for Session operations.

This layer provides business logic and transaction management,
sitting between the API layer and CRUD layer.
"""

from uuid import UUID
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from soorma_common.models import (
    SessionCreate,
    SessionSummary,
)
from memory_service.crud.sessions import (
    create_session as crud_create,
    get_session as crud_get,
    list_sessions as crud_list,
    update_session_interaction as crud_update_interaction,
    delete_session as crud_delete,
)
from memory_service.models.memory import Session


class SessionService:
    """Service for managing sessions with proper transaction boundaries."""
    
    @staticmethod
    def _to_summary(session: Session) -> SessionSummary:
        """Convert database model to summary DTO."""
        return SessionSummary(
            id=str(session.id),
            tenant_id=str(session.tenant_id),
            user_id=str(session.user_id),
            session_id=session.session_id,
            name=session.name,
            metadata=session.session_metadata,
            created_at=session.created_at.isoformat(),
            last_interaction=session.last_interaction.isoformat(),
        )
    
    async def create(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        data: SessionCreate,
    ) -> SessionSummary:
        """
        Create a new session.
        
        Transaction boundary: Commits after successful creation.
        """
        session = await crud_create(
            db,
            tenant_id,
            user_id,
            data.session_id,
            data.name,
            data.metadata,
        )
        await db.commit()
        
        return self._to_summary(session)
    
    async def get(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        session_id: str,
    ) -> Optional[SessionSummary]:
        """Get session by ID."""
        session = await crud_get(db, tenant_id, session_id)
        if not session:
            return None
        
        return self._to_summary(session)
    
    async def list(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        limit: int = 20,
    ) -> List[SessionSummary]:
        """List sessions for a user."""
        sessions = await crud_list(db, tenant_id, user_id, limit)
        return [self._to_summary(s) for s in sessions]
    
    async def update_interaction(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        session_id: str,
    ) -> Optional[SessionSummary]:
        """
        Update session's last interaction timestamp.
        
        Transaction boundary: Commits after successful update.
        """
        session = await crud_update_interaction(db, tenant_id, session_id)
        if not session:
            return None
        
        await db.commit()
        
        return self._to_summary(session)
    
    async def delete(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        session_id: str,
    ) -> bool:
        """
        Delete session.
        
        Transaction boundary: Commits after successful deletion.
        Returns True if deleted, False if not found.
        """
        deleted = await crud_delete(db, tenant_id, session_id)
        if deleted:
            await db.commit()
        
        return deleted


# Singleton instance for dependency injection
session_service = SessionService()
