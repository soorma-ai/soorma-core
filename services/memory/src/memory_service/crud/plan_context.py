"""CRUD operations for plan context."""

from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from memory_service.models.memory import PlanContext


async def create_plan_context(
    db: AsyncSession,
    tenant_id: UUID,
    plan_id: str,
    session_id: Optional[str],
    goal_event: str,
    goal_data: Dict[str, Any],
    response_event: Optional[str],
    state: Dict[str, Any],
    current_state: Optional[str],
    correlation_ids: List[str],
) -> PlanContext:
    """Create a new plan context."""
    plan_context = PlanContext(
        tenant_id=tenant_id,
        plan_id=plan_id,
        session_id=session_id,
        goal_event=goal_event,
        goal_data=goal_data,
        response_event=response_event,
        state=state,
        current_state=current_state,
        correlation_ids=correlation_ids,
    )
    db.add(plan_context)
    await db.flush()
    await db.refresh(plan_context)
    return plan_context


async def get_plan_context(
    db: AsyncSession,
    tenant_id: UUID,
    plan_id: str,
) -> Optional[PlanContext]:
    """Get plan context by plan ID."""
    result = await db.execute(
        select(PlanContext).where(
            PlanContext.tenant_id == tenant_id,
            PlanContext.plan_id == plan_id,
        )
    )
    return result.scalar_one_or_none()


async def update_plan_context(
    db: AsyncSession,
    tenant_id: UUID,
    plan_id: str,
    state: Optional[Dict[str, Any]] = None,
    current_state: Optional[str] = None,
    correlation_ids: Optional[List[str]] = None,
) -> Optional[PlanContext]:
    """Update plan context."""
    plan_context = await get_plan_context(db, tenant_id, plan_id)
    if not plan_context:
        return None
    
    if state is not None:
        plan_context.state = state
    if current_state is not None:
        plan_context.current_state = current_state
    if correlation_ids is not None:
        plan_context.correlation_ids = correlation_ids
    
    await db.flush()
    await db.refresh(plan_context)
    return plan_context


async def delete_plan_context(
    db: AsyncSession,
    tenant_id: UUID,
    plan_id: str,
) -> bool:
    """Delete plan context."""
    result = await db.execute(
        delete(PlanContext).where(
            PlanContext.tenant_id == tenant_id,
            PlanContext.plan_id == plan_id,
        )
    )
    await db.flush()
    return result.rowcount > 0


async def get_plan_by_correlation(
    db: AsyncSession,
    tenant_id: UUID,
    correlation_id: str,
) -> Optional[PlanContext]:
    """Find plan by task/step correlation ID."""
    result = await db.execute(
        select(PlanContext).where(
            PlanContext.tenant_id == tenant_id,
            func.jsonb_contains(PlanContext.correlation_ids, [correlation_id]),
        )
    )
    return result.scalar_one_or_none()
