"""CRUD operations for task context."""

from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy import select, delete, func, cast
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert, JSONB

from memory_service.models.memory import TaskContext


async def upsert_task_context(
    db: AsyncSession,
    tenant_id: UUID,
    user_id: UUID,
    task_id: str,
    plan_id: Optional[str],
    event_type: str,
    response_event: Optional[str],
    response_topic: str,
    data: Dict[str, Any],
    sub_tasks: List[str],
    state: Dict[str, Any],
) -> TaskContext:
    """Upsert task context (insert or update if exists)."""
    # Use PostgreSQL's INSERT ... ON CONFLICT DO UPDATE
    stmt = insert(TaskContext).values(
        tenant_id=tenant_id,
        user_id=user_id,
        task_id=task_id,
        plan_id=plan_id,
        event_type=event_type,
        response_event=response_event,
        response_topic=response_topic,
        data=data,
        sub_tasks=sub_tasks,
        state=state,
    ).on_conflict_do_update(
        index_elements=['tenant_id', 'task_id'],
        set_=dict(
            plan_id=plan_id,
            data=data,
            sub_tasks=sub_tasks,
            state=state,
        )
    ).returning(TaskContext)
    
    result = await db.execute(stmt)
    task_context = result.scalar_one()
    await db.flush()
    await db.refresh(task_context)
    return task_context


async def get_task_context(
    db: AsyncSession,
    tenant_id: UUID,
    task_id: str,
) -> Optional[TaskContext]:
    """Get task context by task ID."""
    result = await db.execute(
        select(TaskContext).where(
            TaskContext.tenant_id == tenant_id,
            TaskContext.task_id == task_id,
        )
    )
    return result.scalar_one_or_none()


async def update_task_context(
    db: AsyncSession,
    tenant_id: UUID,
    task_id: str,
    sub_tasks: Optional[List[str]] = None,
    state: Optional[Dict[str, Any]] = None,
) -> Optional[TaskContext]:
    """Update task context."""
    task_context = await get_task_context(db, tenant_id, task_id)
    if not task_context:
        return None
    
    if sub_tasks is not None:
        task_context.sub_tasks = sub_tasks
    if state is not None:
        task_context.state = state
    
    await db.flush()
    await db.refresh(task_context)
    return task_context


async def delete_task_context(
    db: AsyncSession,
    tenant_id: UUID,
    task_id: str,
) -> bool:
    """Delete task context."""
    result = await db.execute(
        delete(TaskContext).where(
            TaskContext.tenant_id == tenant_id,
            TaskContext.task_id == task_id,
        )
    )
    await db.flush()
    return result.rowcount > 0


async def get_task_by_subtask(
    db: AsyncSession,
    tenant_id: UUID,
    sub_task_id: str,
) -> Optional[TaskContext]:
    """Find parent task by sub-task ID."""
    # Check database dialect for appropriate JSON query
    dialect_name = db.bind.dialect.name if db.bind else "postgresql"
    
    if dialect_name == "postgresql":
        # Use PostgreSQL JSONB contains operator (@>)
        # Cast the Python list to JSONB so asyncpg can handle it properly
        result = await db.execute(
            select(TaskContext).where(
                TaskContext.tenant_id == tenant_id,
                TaskContext.sub_tasks.op('@>')(cast([sub_task_id], JSONB)),
            )
        )
    else:
        # For SQLite and other databases, use simple string matching
        # Note: This is less efficient but works for testing
        # In production, PostgreSQL with JSONB should be used
        result = await db.execute(
            select(TaskContext).where(
                TaskContext.tenant_id == tenant_id,
            )
        )
        # Filter in Python for non-PostgreSQL databases
        for task_context in result.scalars():
            if sub_task_id in task_context.sub_tasks:
                return task_context
        return None
    
    return result.scalar_one_or_none()
