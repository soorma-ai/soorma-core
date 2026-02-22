"""Event handlers for Tracker Service.

This module subscribes to events from the event bus and updates
the tracker database with plan and action progress.

Event Topics:
- action-requests: Track when tasks start
- action-results: Track when tasks complete
- system-events: Track plan lifecycle (started, completed, state changes)
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from soorma_common.events import EventEnvelope, EventTopic
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, insert
from sqlalchemy.dialects.postgresql import insert as pg_insert

from tracker_service.models.db import ActionProgress, PlanProgress, ActionStatus, PlanStatus


logger = logging.getLogger(__name__)

# Global subscription manager
_subscription_ids: list[str] = []
_bus_client: Optional[Any] = None


async def start_event_subscribers(bus_client: Any) -> None:
    """
    Start subscribing to events from the event bus.
    
    Called during application startup to begin listening for events.
    
    Args:
        bus_client: Event bus client instance (BusClient from SDK)
    """
    global _bus_client, _subscription_ids
    _bus_client = bus_client
    
    try:
        # Subscribe to action-requests topic (all action start events)
        action_req_sub = await bus_client.subscribe(
            topics=[EventTopic.ACTION_REQUESTS],
            handler=_create_db_handler(handle_action_request),
        )
        _subscription_ids.append(action_req_sub)
        logger.info(f"Subscribed to {EventTopic.ACTION_REQUESTS}")
        
        # Subscribe to action-results topic (all action completion events)
        action_res_sub = await bus_client.subscribe(
            topics=[EventTopic.ACTION_RESULTS],
            handler=_create_db_handler(handle_action_result),
        )
        _subscription_ids.append(action_res_sub)
        logger.info(f"Subscribed to {EventTopic.ACTION_RESULTS}")
        
        # Subscribe to system-events topic (plan lifecycle events)
        system_events_sub = await bus_client.subscribe(
            topics=[EventTopic.SYSTEM_EVENTS],
            handler=_create_db_handler(handle_plan_event),
        )
        _subscription_ids.append(system_events_sub)
        logger.info(f"Subscribed to {EventTopic.SYSTEM_EVENTS}")
        
        logger.info(f"Tracker Service: All event subscribers started ({len(_subscription_ids)} subscriptions)")
    except Exception as e:
        logger.error(f"Failed to start event subscribers: {e}")
        raise


async def stop_event_subscribers() -> None:
    """
   Stop all event subscriptions.
    
    Called during application shutdown to cleanly unsubscribe.
    """
    global _bus_client, _subscription_ids
    
    if not _bus_client:
        logger.warning("No bus client to unsubscribe from")
        return
    
    for sub_id in _subscription_ids:
        try:
            await _bus_client.unsubscribe(sub_id)
            logger.info(f"Unsubscribed from {sub_id}")
        except Exception as e:
            logger.error(f"Failed to unsubscribe from {sub_id}: {e}")
    
    _subscription_ids.clear()
    _bus_client = None
    logger.info("Tracker Service: All event subscribers stopped")


def _create_db_handler(handler_func):
    """
    Wrap event handler to create database session for each event.
    
    Args:
        handler_func: The actual handler function (handle_action_request, etc.)
    
    Returns:
        Async function that creates DB session and calls handler
    """
    async def wrapper(event: EventEnvelope):
        from tracker_service.core.db import get_db
        
        try:
            # Get database session
            async for db_session in get_db():
                try:
                    await handler_func(event, db_session)
                    await db_session.commit()
                except Exception as handler_error:
                    await db_session.rollback()
                    logger.error(f"Handler error for {event.type}: {handler_error}")
                    raise
                finally:
                    await db_session.close()
        except Exception as e:
            logger.error(f"Database session error: {e}")
    
    return wrapper


async def handle_action_request(
    event: EventEnvelope,
    db_session: AsyncSession,
) -> None:
    """
    Handle action request events to track task start.
    
    Subscribes to: action-requests topic
    Event types: * (all action requests)
    
    Updates:
    - action_progress table: Insert new record with PENDING status
    - plan_progress table: Increment total_actions count
    
    Args:
        event: Event envelope containing task data
        db_session: Database session for updates
    """
    tenant_id, user_id = _extract_tenant_user(event)
    data = event.data or {}
    
    # Extract action metadata
    action_id = data.get("action_id") or event.correlation_id or event.id
    plan_id = data.get("plan_id")
    action_name = data.get("action_name") or event.type
    action_type = event.type
    assigned_to = data.get("assigned_to")
    
    logger.debug(f"Tracking action request: {action_id} (plan: {plan_id})")
    
    # Insert action_progress record
    stmt = pg_insert(ActionProgress).values(
        action_id=action_id,
        plan_id=plan_id,
        tenant_id=tenant_id,
        user_id=user_id,
        action_name=action_name,
        action_type=action_type,
        status=ActionStatus.PENDING,
        assigned_to=assigned_to,
        started_at=event.time or datetime.now(timezone.utc),
    )
    
    # On conflict, update to latest state (idempotency)
    stmt = stmt.on_conflict_do_update(
        index_elements=["tenant_id", "action_id"],
        set_={
            "status": ActionStatus.PENDING,
            "started_at": event.time or datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
    )
    
    await db_session.execute(stmt)
    
    # If plan_id exists, increment total_actions count
    if plan_id:
        await _increment_plan_action_count(db_session, plan_id, tenant_id, user_id)


async def handle_action_result(
    event: EventEnvelope,
    db_session: AsyncSession,
) -> None:
    """
    Handle action result events to track task completion.
    
    Subscribes to: action-results topic
    Event types: * (all action results)
    
    Updates:
    - action_progress table: Update status to COMPLETED/FAILED, set completed_at
    - plan_progress table: Increment completed_actions or failed_actions count
    
    Args:
        event: Event envelope containing task result data
        db_session: Database session for updates
    """
    tenant_id, user_id = _extract_tenant_user(event)
    data = event.data or {}
    
    # Extract action metadata
    action_id = data.get("action_id") or event.correlation_id or event.id
    plan_id = data.get("plan_id")
    result_data = data.get("result")
    error = data.get("error")
    
    # Determine status (failed events contain "error" or "failed" in type)
    is_failed = error or "failed" in event.type.lower() or "error" in event.type.lower()
    status = ActionStatus.FAILED if is_failed else ActionStatus.COMPLETED
    
    logger.debug(f"Tracking action result: {action_id} (status: {status})")
    
    # Update action_progress record
    stmt = (
        update(ActionProgress)
        .where(ActionProgress.tenant_id == tenant_id)
        .where(ActionProgress.action_id == action_id)
        .values(
            status=status,
            completed_at=event.time or datetime.now(timezone.utc),
            result=str(result_data) if result_data else None,
            error_message=str(error) if error else None,
            updated_at=datetime.now(timezone.utc),
        )
    )
    
    await db_session.execute(stmt)
    
    # If plan_id exists, increment completed/failed count
    if plan_id:
        if is_failed:
            await _increment_plan_failed_count(db_session, plan_id, tenant_id, user_id)
        else:
            await _increment_plan_completed_count(db_session, plan_id, tenant_id, user_id)


async def handle_plan_event(
    event: EventEnvelope,
    db_session: AsyncSession,
) -> None:
    """
    Handle plan lifecycle events.
    
    Subscribes to: system-events topic
    Event types:
    - plan.started: Insert new plan_progress record
    - plan.state_changed: Update plan current state
    - plan.completed: Update plan status and completed_at
    - plan.failed: Update plan status to FAILED with error
    
    Updates:
    - plan_progress table: Insert or update plan execution records
    
    Args:
        event: Event envelope containing plan lifecycle data
        db_session: Database session for updates
    """
    tenant_id, user_id = _extract_tenant_user(event)
    data = event.data or {}
    event_type = event.type
    
    plan_id = data.get("plan_id")
    if not plan_id:
        logger.warning(f"Plan event {event_type} missing plan_id")
        return
    
    logger.debug(f"Tracking plan event: {event_type} for plan {plan_id}")
    
    if event_type == "plan.started":
        # Insert new plan_progress record
        plan_name = data.get("plan_name")
        plan_description = data.get("plan_description")
        total_actions = data.get("total_actions", 0)
        
        stmt = pg_insert(PlanProgress).values(
            plan_id=plan_id,
            tenant_id=tenant_id,
            user_id=user_id,
            plan_name=plan_name,
            plan_description=plan_description,
            status=PlanStatus.IN_PROGRESS,
            total_actions=total_actions,
            started_at=event.time or datetime.now(timezone.utc),
        )
        
        # On conflict, update to latest state
        stmt = stmt.on_conflict_do_update(
            index_elements=["tenant_id", "plan_id"],
            set_={
                "status": PlanStatus.IN_PROGRESS,
                "started_at": event.time or datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
        )
        
        await db_session.execute(stmt)
    
    elif event_type == "plan.state_changed":
        # Update plan current state (future enhancement - not in current schema)
        new_state = data.get("new_state")
        logger.debug(f"Plan {plan_id} state changed to {new_state}")
        # Note: current_state field not yet added to schema, this is a placeholder
    
    elif event_type == "plan.completed":
        # Update plan to completed status
        result = data.get("result")
        
        stmt = (
            update(PlanProgress)
            .where(PlanProgress.tenant_id == tenant_id)
            .where(PlanProgress.plan_id == plan_id)
            .values(
                status=PlanStatus.COMPLETED,
                completed_at=event.time or datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        )
        
        await db_session.execute(stmt)
    
    elif event_type == "plan.failed":
        # Update plan to failed status with error
        error = data.get("error")
        
        stmt = (
            update(PlanProgress)
            .where(PlanProgress.tenant_id == tenant_id)
            .where(PlanProgress.plan_id == plan_id)
            .values(
                status=PlanStatus.FAILED,
                error_message=str(error) if error else None,
                completed_at=event.time or datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        )
        
        await db_session.execute(stmt)


def _extract_tenant_user(event: EventEnvelope) -> tuple[str, str]:
    """
    Extract tenant_id and user_id from event envelope.
    
    Multi-tenancy helper to get authentication context from events.
    
    Args:
        event: Event envelope with tenant/user metadata
    
    Returns:
        Tuple of (tenant_id, user_id)
    """
    # Use defaults if not provided (for development/testing)
    tenant_id = event.tenant_id or "00000000-0000-0000-0000-000000000000"
    user_id = event.user_id or "00000000-0000-0000-0000-000000000001"
    
    return tenant_id, user_id


async def _increment_plan_action_count(
    db_session: AsyncSession,
    plan_id: str, 
    tenant_id: str,
    user_id: str,
) -> None:
    """Increment total_actions count for a plan."""
    stmt = (
        update(PlanProgress)
        .where(PlanProgress.tenant_id == tenant_id)
        .where(PlanProgress.plan_id == plan_id)
        .values(
            total_actions=PlanProgress.total_actions + 1,
            updated_at=datetime.now(timezone.utc),
        )
    )
    
    await db_session.execute(stmt)


async def _increment_plan_completed_count(
    db_session: AsyncSession,
    plan_id: str,
    tenant_id: str,
    user_id: str,
) -> None:
    """Increment completed_actions count for a plan."""
    stmt = (
        update(PlanProgress)
        .where(PlanProgress.tenant_id == tenant_id)
        .where(PlanProgress.plan_id == plan_id)
        .values(
            completed_actions=PlanProgress.completed_actions + 1,
            updated_at=datetime.now(timezone.utc),
        )
    )
    
    await db_session.execute(stmt)


async def _increment_plan_failed_count(
    db_session: AsyncSession,
    plan_id: str,
    tenant_id: str,
    user_id: str,
) -> None:
    """Increment failed_actions count for a plan."""
    stmt = (
        update(PlanProgress)
        .where(PlanProgress.tenant_id == tenant_id)
        .where(PlanProgress.plan_id == plan_id)
        .values(
            failed_actions=PlanProgress.failed_actions + 1,
            updated_at=datetime.now(timezone.utc),
        )
    )
    
    await db_session.execute(stmt)
