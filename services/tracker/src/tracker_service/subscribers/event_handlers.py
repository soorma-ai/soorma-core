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
from soorma.events import EventClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, insert
from sqlalchemy.dialects.postgresql import insert as pg_insert

from tracker_service.models.db import ActionProgress, PlanProgress, ActionStatus, PlanStatus


logger = logging.getLogger(__name__)

# Global EventClient used for SSE subscription
_event_client: Optional[Any] = None


async def start_event_subscribers(event_service_url: str) -> None:
    """
    Start subscribing to events from the event bus via SSE.

    Creates an EventClient, registers a catch-all dispatcher that routes
    events to the appropriate handler by topic, then connects.

    Args:
        event_service_url: Base URL of the Event Service (e.g. "http://event-service:8082")
    """
    global _event_client

    _event_client = EventClient(
        event_service_url=event_service_url,
        agent_id="tracker-service",
        source="tracker-service",
    )

    @_event_client.on_all_events
    async def _dispatch(event: EventEnvelope) -> None:
        """Route every inbound event to the correct handler by topic."""
        topic_value = event.topic.value if isinstance(event.topic, EventTopic) else str(event.topic)

        if topic_value == EventTopic.ACTION_REQUESTS.value:
            handler = handle_action_request
        elif topic_value == EventTopic.ACTION_RESULTS.value:
            handler = handle_action_result
        elif topic_value == EventTopic.SYSTEM_EVENTS.value:
            handler = handle_plan_event
        else:
            logger.debug(f"Tracker: ignoring event on untracked topic '{topic_value}'")
            return

        await _create_db_handler(handler)(event)

    await _event_client.connect([
        EventTopic.ACTION_REQUESTS,
        EventTopic.ACTION_RESULTS,
        EventTopic.SYSTEM_EVENTS,
    ])

    logger.info(
        f"Tracker Service: subscribed to "
        f"{EventTopic.ACTION_REQUESTS.value}, "
        f"{EventTopic.ACTION_RESULTS.value}, "
        f"{EventTopic.SYSTEM_EVENTS.value} "
        f"via {event_service_url}"
    )


async def stop_event_subscribers() -> None:
    """Stop all event subscriptions and disconnect from the event bus."""
    global _event_client

    if _event_client:
        await _event_client.disconnect()
        _event_client = None
        logger.info("Tracker Service: event subscribers stopped")
    else:
        logger.debug("Tracker Service: no active event client to stop")


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
    
    # Extract action metadata from envelope and data
    action_id = data.get("action_id") or event.correlation_id or event.id
    plan_id = event.plan_id  # Read from envelope metadata (not data payload)
    action_name = data.get("action_name") or event.type
    action_type = event.type
    assigned_to = data.get("assigned_to")
    
    logger.debug(f"Tracking action request: {action_id} (plan: {plan_id})")

    # Tracker requires a plan_id to record progress — standalone/unplanned
    # events (e.g. from direct worker publishers not under a planner) have no
    # plan_id, so there is nothing to track. Skip silently.
    if not plan_id:
        logger.debug(
            f"Tracker: skipping action_progress insert for {action_id} — "
            "no plan_id in event envelope (unplanned task)"
        )
        return

    # Auto-upsert plan_progress so action_progress FK is satisfied even when
    # no explicit plan.started system event was published (choreography pattern).
    if plan_id:
        plan_stmt = pg_insert(PlanProgress).values(
            plan_id=plan_id,
            tenant_id=tenant_id,
            user_id=user_id,
            status=PlanStatus.IN_PROGRESS,
            total_actions=0,
            started_at=event.time or datetime.now(timezone.utc),
        )
        plan_stmt = plan_stmt.on_conflict_do_update(
            index_elements=["plan_id"],  # unique constraint uq_plan_id
            set_={"updated_at": datetime.now(timezone.utc)},
        )
        await db_session.execute(plan_stmt)

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
    
    # Extract action metadata from envelope and data
    action_id = data.get("action_id") or event.correlation_id or event.id
    plan_id = event.plan_id  # Read from envelope metadata (not data payload)
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
    
    result_proxy = await db_session.execute(stmt)
    rows_updated = result_proxy.rowcount
    
    # Only increment plan counters when we actually updated a known action row.
    # Unmatched events (e.g. the final client response on ACTION_RESULTS) have
    # no action_progress row, so rowcount == 0 and the counter must stay clean.
    if plan_id and rows_updated > 0:
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
            index_elements=["plan_id"],  # unique constraint uq_plan_id
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
