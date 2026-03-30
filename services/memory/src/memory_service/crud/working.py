"""CRUD operations for working memory."""

from typing import Optional, Dict, Any
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from memory_service.models.memory import WorkingMemory
from soorma_common.models import WorkingMemorySet
from memory_service.crud._identity import require_platform_tenant_id, scoped_identity_filters


async def set_working_memory(
    db: AsyncSession,
    platform_tenant_id: str,
    service_tenant_id: str,
    service_user_id: str,
    plan_id: str,
    key: str,
    data: WorkingMemorySet,
) -> WorkingMemory:
    """Set or update working memory value."""
    require_platform_tenant_id(platform_tenant_id)
    # Use PostgreSQL INSERT ... ON CONFLICT UPDATE (upsert)
    stmt = insert(WorkingMemory).values(
        platform_tenant_id=platform_tenant_id,
        service_tenant_id=service_tenant_id,
        service_user_id=service_user_id,
        plan_id=plan_id,
        key=key,
        value=data.value,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[
            "platform_tenant_id",
            "service_tenant_id",
            "service_user_id",
            "plan_id",
            "key",
        ],
        set_={"value": data.value},
    )

    await db.execute(stmt)
    await db.flush()

    # Fetch the updated record
    result = await db.execute(
        select(WorkingMemory).where(
            *scoped_identity_filters(
                WorkingMemory,
                platform_tenant_id,
                service_tenant_id,
                service_user_id,
            ),
            WorkingMemory.plan_id == plan_id,
            WorkingMemory.key == key,
        )
    )
    memory = result.scalar_one()
    return memory


async def get_working_memory(
    db: AsyncSession,
    platform_tenant_id: str,
    service_tenant_id: str,
    service_user_id: str,
    plan_id: str,
    key: str,
) -> Optional[WorkingMemory]:
    """Get working memory value."""
    require_platform_tenant_id(platform_tenant_id)
    stmt = select(WorkingMemory).where(
        *scoped_identity_filters(
            WorkingMemory,
            platform_tenant_id,
            service_tenant_id,
            service_user_id,
        ),
        WorkingMemory.plan_id == plan_id,
        WorkingMemory.key == key,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def delete_working_memory_key(
    db: AsyncSession,
    platform_tenant_id: str,
    service_tenant_id: str,
    service_user_id: str,
    plan_id: str,
    key: str,
) -> bool:
    """
    Delete a single working memory key.
    
    Args:
        db: Database session
        platform_tenant_id: Platform tenant identifier (for RLS enforcement)
        plan_id: Plan identifier
        key: Key to delete
    
    Returns:
        True if key was deleted, False if key did not exist
    """
    require_platform_tenant_id(platform_tenant_id)
    # Build query to delete
    stmt = delete(WorkingMemory).where(
        *scoped_identity_filters(
            WorkingMemory,
            platform_tenant_id,
            service_tenant_id,
            service_user_id,
        ),
        WorkingMemory.plan_id == plan_id,
        WorkingMemory.key == key,
    )
    
    result = await db.execute(stmt)
    await db.flush()
    
    # Return True if a row was deleted, False otherwise
    return result.rowcount > 0


async def delete_working_memory_plan(
    db: AsyncSession,
    platform_tenant_id: str,
    service_tenant_id: str,
    service_user_id: str,
    plan_id: str,
) -> int:
    """
    Delete all working memory for a plan.
    
    Args:
        db: Database session
        platform_tenant_id: Platform tenant identifier (for RLS enforcement)
        plan_id: Plan identifier
    
    Returns:
        Count of rows deleted
    """
    require_platform_tenant_id(platform_tenant_id)
    # Build query to delete all keys for this plan
    stmt = delete(WorkingMemory).where(
        *scoped_identity_filters(
            WorkingMemory,
            platform_tenant_id,
            service_tenant_id,
            service_user_id,
        ),
        WorkingMemory.plan_id == plan_id,
    )
    
    result = await db.execute(stmt)
    await db.flush()
    
    # Return count of deleted rows
    return result.rowcount
