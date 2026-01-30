"""CRUD operations for working memory."""

from typing import Optional, Dict, Any
from uuid import UUID
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from memory_service.models.memory import WorkingMemory
from soorma_common.models import WorkingMemorySet, WorkingMemoryResponse


async def set_working_memory(
    db: AsyncSession,
    tenant_id: UUID,
    user_id: UUID,
    plan_id: UUID,
    key: str,
    data: WorkingMemorySet,
) -> WorkingMemory:
    """Set or update working memory value."""
    # Use PostgreSQL INSERT ... ON CONFLICT UPDATE (upsert)
    stmt = insert(WorkingMemory).values(
        tenant_id=tenant_id,
        user_id=user_id,
        plan_id=plan_id,
        key=key,
        value=data.value,
    )
    stmt = stmt.on_conflict_do_update(
        constraint="plan_key_unique",
        set_={"value": data.value},
    )

    await db.execute(stmt)
    await db.flush()

    # Fetch the updated record
    result = await db.execute(
        select(WorkingMemory).where(
            WorkingMemory.tenant_id == tenant_id,
            WorkingMemory.plan_id == plan_id,
            WorkingMemory.key == key,
        )
    )
    memory = result.scalar_one()
    return memory


async def get_working_memory(
    db: AsyncSession,
    tenant_id: UUID,
    user_id: UUID,
    plan_id: UUID,
    key: str,
) -> Optional[WorkingMemory]:
    """Get working memory value."""
    stmt = select(WorkingMemory).where(
        WorkingMemory.tenant_id == tenant_id,
        WorkingMemory.user_id == user_id,
        WorkingMemory.plan_id == plan_id,
        WorkingMemory.key == key,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def delete_working_memory_key(
    db: AsyncSession,
    tenant_id: UUID,
    user_id: UUID,
    plan_id: UUID,
    key: str,
) -> bool:
    """
    Delete a single working memory key.
    
    Args:
        db: Database session
        tenant_id: Tenant identifier (for RLS enforcement)
        plan_id: Plan identifier
        key: Key to delete
    
    Returns:
        True if key was deleted, False if key did not exist
    """
    # Build query to delete
    stmt = delete(WorkingMemory).where(
        WorkingMemory.tenant_id == tenant_id,
        WorkingMemory.user_id == user_id,
        WorkingMemory.plan_id == plan_id,
        WorkingMemory.key == key,
    )
    
    result = await db.execute(stmt)
    await db.flush()
    
    # Return True if a row was deleted, False otherwise
    return result.rowcount > 0


async def delete_working_memory_plan(
    db: AsyncSession,
    tenant_id: UUID,
    user_id: UUID,
    plan_id: UUID,
) -> int:
    """
    Delete all working memory for a plan.
    
    Args:
        db: Database session
        tenant_id: Tenant identifier (for RLS enforcement)
        plan_id: Plan identifier
    
    Returns:
        Count of rows deleted
    """
    # Build query to delete all keys for this plan
    stmt = delete(WorkingMemory).where(
        WorkingMemory.tenant_id == tenant_id,
        WorkingMemory.user_id == user_id,
        WorkingMemory.plan_id == plan_id,
    )
    
    result = await db.execute(stmt)
    await db.flush()
    
    # Return count of deleted rows
    return result.rowcount
