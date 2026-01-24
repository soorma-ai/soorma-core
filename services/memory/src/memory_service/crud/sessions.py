"""CRUD operations for sessions."""

from typing import Optional, List
from uuid import UUID
from sqlalchemy import select, delete, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from memory_service.models.memory import Session


async def create_session(
    db: AsyncSession,
    tenant_id: UUID,
    user_id: UUID,
    session_id: str,
    name: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> Session:
    """Create a new session."""
    session = Session(
        tenant_id=tenant_id,
        user_id=user_id,
        session_id=session_id,
        name=name,
        session_metadata=metadata,
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return session


async def get_session(
    db: AsyncSession,
    tenant_id: UUID,
    session_id: str,
) -> Optional[Session]:
    """Get session by ID."""
    result = await db.execute(
        select(Session).where(
            Session.tenant_id == tenant_id,
            Session.session_id == session_id,
        )
    )
    return result.scalar_one_or_none()


async def list_sessions(
    db: AsyncSession,
    tenant_id: UUID,
    user_id: UUID,
    limit: int = 20,
) -> List[Session]:
    """List sessions for a user."""
    query = select(Session).where(
        Session.tenant_id == tenant_id,
        Session.user_id == user_id,
    ).order_by(desc(Session.last_interaction)).limit(limit)
    
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_session_interaction(
    db: AsyncSession,
    tenant_id: UUID,
    session_id: str,
) -> Optional[Session]:
    """Update session last_interaction timestamp."""
    session = await get_session(db, tenant_id, session_id)
    if not session:
        return None
    
    # Updating directly triggers onupdate for last_interaction
    session.last_interaction = func.now()
    
    await db.flush()
    await db.refresh(session)
    return session


async def delete_session(
    db: AsyncSession,
    tenant_id: UUID,
    session_id: str,
) -> bool:
    """Delete session."""
    result = await db.execute(
        delete(Session).where(
            Session.tenant_id == tenant_id,
            Session.session_id == session_id,
        )
    )
    await db.flush()
    return result.rowcount > 0
