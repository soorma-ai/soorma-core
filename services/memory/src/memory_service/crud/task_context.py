"""CRUD operations for task context."""

from typing import Optional, List, Dict, Any
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from memory_service.models.memory import TaskContext


async def upsert_task_context(
    db: AsyncSession,
    platform_tenant_id: str,
    service_tenant_id: str,
    service_user_id: str,
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
    assert platform_tenant_id, "platform_tenant_id is required"
    # Use PostgreSQL's INSERT ... ON CONFLICT DO UPDATE
    stmt = insert(TaskContext).values(
        platform_tenant_id=platform_tenant_id,
        service_tenant_id=service_tenant_id,
        service_user_id=service_user_id,
        task_id=task_id,
        plan_id=plan_id,
        event_type=event_type,
        response_event=response_event,
        response_topic=response_topic,
        data=data,
        sub_tasks=sub_tasks,
        state=state,
    ).on_conflict_do_update(
        index_elements=['platform_tenant_id', 'task_id'],
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
    platform_tenant_id: str,
    task_id: str,
) -> Optional[TaskContext]:
    """Get task context by task ID."""
    result = await db.execute(
        select(TaskContext).where(
            TaskContext.platform_tenant_id == platform_tenant_id,
            TaskContext.task_id == task_id,
        )
    )
    return result.scalar_one_or_none()


async def update_task_context(
    db: AsyncSession,
    platform_tenant_id: str,
    task_id: str,
    sub_tasks: Optional[List[str]] = None,
    state: Optional[Dict[str, Any]] = None,
) -> Optional[TaskContext]:
    """Update task context."""
    task_context = await get_task_context(db, platform_tenant_id, task_id)
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
    platform_tenant_id: str,
    task_id: str,
) -> bool:
    """Delete task context."""
    result = await db.execute(
        delete(TaskContext).where(
            TaskContext.platform_tenant_id == platform_tenant_id,
            TaskContext.task_id == task_id,
        )
    )
    await db.flush()
    return result.rowcount > 0


async def get_task_by_subtask(
    db: AsyncSession,
    platform_tenant_id: str,
    sub_task_id: str,
) -> Optional[TaskContext]:
    """Find parent task by sub-task ID."""
    # Fetch all tasks for the tenant and filter in Python.
    # Avoids JSONB-specific operators that are PostgreSQL-only and incompatible
    # with the SQLite test database.  The number of active tasks per tenant is
    # small, so fetching and filtering in Python is acceptable.
    result = await db.execute(
        select(TaskContext).where(
            TaskContext.platform_tenant_id == platform_tenant_id,
        )
    )
    for task in result.scalars().all():
        if sub_task_id in (task.sub_tasks or []):
            return task
    return None
