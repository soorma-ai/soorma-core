"""CRUD operations for plans."""

from typing import Optional, List
from sqlalchemy import select, delete, desc
from sqlalchemy.ext.asyncio import AsyncSession

from memory_service.models.memory import Plan


async def create_plan(
    db: AsyncSession,
    platform_tenant_id: str,
    service_tenant_id: str,
    service_user_id: str,
    plan_id: str,
    session_id: Optional[str],
    goal_event: str,
    goal_data: dict,
    parent_plan_id: Optional[str] = None,
) -> Plan:
    """Create a new plan."""
    assert platform_tenant_id, "platform_tenant_id is required"
    plan = Plan(
        platform_tenant_id=platform_tenant_id,
        service_tenant_id=service_tenant_id,
        service_user_id=service_user_id,
        plan_id=plan_id,
        session_id=session_id,
        goal_event=goal_event,
        goal_data=goal_data,
        status='running',
        parent_plan_id=parent_plan_id,
    )
    db.add(plan)
    await db.flush()
    await db.refresh(plan)
    return plan


async def get_plan(
    db: AsyncSession,
    platform_tenant_id: str,
    service_tenant_id: str,
    service_user_id: str,
    plan_id: str,
) -> Optional[Plan]:
    """Get plan by ID."""
    result = await db.execute(
        select(Plan).where(
            Plan.platform_tenant_id == platform_tenant_id,
            Plan.service_tenant_id == service_tenant_id,
            Plan.service_user_id == service_user_id,
            Plan.plan_id == plan_id,
        )
    )
    return result.scalar_one_or_none()


async def list_plans(
    db: AsyncSession,
    platform_tenant_id: str,
    service_tenant_id: str,
    service_user_id: str,
    status: Optional[str] = None,
    session_id: Optional[str] = None,
    limit: int = 20,
) -> List[Plan]:
    """List plans for a user."""
    query = select(Plan).where(
        Plan.platform_tenant_id == platform_tenant_id,
        Plan.service_tenant_id == service_tenant_id,
        Plan.service_user_id == service_user_id,
    )
    
    if status:
        query = query.where(Plan.status == status)
    if session_id:
        query = query.where(Plan.session_id == session_id)
    
    query = query.order_by(desc(Plan.updated_at)).limit(limit)
    
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_plan(
    db: AsyncSession,
    platform_tenant_id: str,
    service_tenant_id: str,
    service_user_id: str,
    plan_id: str,
    status: Optional[str] = None,
) -> Optional[Plan]:
    """Update plan."""
    plan = await get_plan(
        db,
        platform_tenant_id,
        service_tenant_id,
        service_user_id,
        plan_id,
    )
    if not plan:
        return None
    
    if status is not None:
        plan.status = status
    
    await db.flush()
    await db.refresh(plan)
    return plan


async def delete_plan(
    db: AsyncSession,
    platform_tenant_id: str,
    service_tenant_id: str,
    service_user_id: str,
    plan_id: str,
) -> bool:
    """Delete plan."""
    result = await db.execute(
        delete(Plan).where(
            Plan.platform_tenant_id == platform_tenant_id,
            Plan.service_tenant_id == service_tenant_id,
            Plan.service_user_id == service_user_id,
            Plan.plan_id == plan_id,
        )
    )
    await db.flush()
    return result.rowcount > 0
