# Architecture Refactoring: Tracker Service

**Document:** 04-TRACKER-SERVICE.md  
**Status:** ⬜ Not Started  
**Priority:** 🟡 Medium (Phase 2)  
**Last Updated:** January 11, 2026

---

## Quick Reference

| Aspect | Details |
|--------|----------|
| **Tasks** | RF-ARCH-010: Event Listener Pattern, RF-ARCH-011: Progress Model |
| **Files** | Tracker Service (new service) |
| **Pairs With SDK** | [sdk/03-COMMON-DTOS.md](../sdk/03-COMMON-DTOS.md) |
| **Dependencies** | 01-EVENT-SERVICE, 03-COMMON-LIBRARY |
| **Blocks** | None |
| **Estimated Effort** | 3-4 days |

---

## Context

### Why This Matters

Tracker Service provides **observability** for agent workflows:

1. **Passive consumer** - Subscribes to events, doesn't expose write APIs
2. **Progress tracking** - Monitors task/plan execution
3. **Execution timeline** - Records event chains for debugging
4. **Metrics** - Agent performance, success rates

### Current State

Tracker Service is **not implemented** - currently SDK calls a planned API directly.

### Key Files

```
services/tracker/          # NEW SERVICE
├── src/
│   ├── subscribers/      # Event subscriptions
│   ├── routes/           # Read-only query APIs
│   └── db/              # Database layer
└── migrations/          # Schema migrations
```

---

## Summary

This document covers Tracker Service design:
- **RF-ARCH-010:** Passive event listener pattern
- **RF-ARCH-011:** Task progress model (states + optional progress %)

SDK publishes events (see [sdk/03-COMMON-DTOS.md](../sdk/03-COMMON-DTOS.md)), Tracker subscribes.

---

## Tasks

### RF-ARCH-010: Tracker as Event Listener

**Principle:** Tracker does NOT expose write APIs - it consumes events.

#### Event Subscriptions

Tracker subscribes to these topics:

| Topic | Event Types | Purpose |
|-------|-------------|---------|
| `system-events` | `task.progress`, `task.state_changed` | Track task execution |
| `system-events` | `plan.started`, `plan.completed` | Track plan lifecycle |
| `action-requests` | `*` | Record task starts |
| `action-results` | `*` | Record task completions |

#### Subscriber Implementation

```python
# services/tracker/src/subscribers/task_tracking.py
from soorma_sdk import Agent, PlatformContext
from soorma_common import TaskProgressEvent, TaskStateChanged

tracker = Agent(name="tracker-service")

@tracker.on_event(topic="system-events", event_type="task.progress")
async def track_progress(event, ctx: PlatformContext):
    """Record task progress updates."""
    progress = TaskProgressEvent(**event.data)
    
    await db.upsert_task_progress(
        task_id=progress.task_id,
        plan_id=progress.plan_id,
        state=progress.state,
        progress=progress.progress,
        message=progress.message,
        timestamp=event.time,
    )

@tracker.on_event(topic="system-events", event_type="task.state_changed")
async def track_state_change(event, ctx: PlatformContext):
    """Record task state transitions."""
    state_change = TaskStateChanged(**event.data)
    
    await db.record_state_transition(
        task_id=state_change.task_id,
        plan_id=state_change.plan_id,
        from_state=state_change.previous_state,
        to_state=state_change.new_state,
        reason=state_change.reason,
        timestamp=event.time,
    )

@tracker.on_event(topic="action-requests", event_type="*")
async def track_task_start(event, ctx: PlatformContext):
    """Record when tasks are requested."""
    await db.record_task_start(
        task_id=event.correlation_id,
        plan_id=event.data.get("plan_id"),
        event_type=event.type,
        data=event.data,
        timestamp=event.time,
        trace_id=event.trace_id,
        parent_event_id=event.parent_event_id,
    )

@tracker.on_event(topic="action-results", event_type="*")
async def track_task_completion(event, ctx: PlatformContext):
    """Record when tasks complete."""
    await db.record_task_completion(
        task_id=event.correlation_id,
        event_type=event.type,
        success=event.data.get("success", True),
        result=event.data,
        timestamp=event.time,
    )
```

#### Read-Only Query APIs

Tracker exposes **read-only** endpoints:

```python
# Query plan execution status
GET /v1/tracker/plans/{plan_id}

Response:
{
    "plan_id": "plan-123",
    "status": "running",
    "started_at": "2026-01-11T10:00:00Z",
    "task_count": 5,
    "completed_tasks": 3,
    "failed_tasks": 0,
    "current_state": "analyzing"
}

# Query task history for plan
GET /v1/tracker/plans/{plan_id}/tasks

Response:
{
    "tasks": [
        {
            "task_id": "task-1",
            "event_type": "web.search.requested",
            "state": "completed",
            "started_at": "2026-01-11T10:01:00Z",
            "completed_at": "2026-01-11T10:02:30Z",
            "duration_seconds": 90
        },
        {
            "task_id": "task-2",
            "event_type": "analyze.text",
            "state": "running",
            "started_at": "2026-01-11T10:02:35Z",
            "progress": 0.6
        }
    ]
}

# Query execution timeline (trace tree)
GET /v1/tracker/plans/{plan_id}/timeline

Response:
{
    "trace_id": "trace-abc123",
    "events": [
        {
            "event_id": "event-1",
            "event_type": "research.goal",
            "timestamp": "2026-01-11T10:00:00Z",
            "parent_event_id": null
        },
        {
            "event_id": "event-2",
            "event_type": "web.search.requested",
            "timestamp": "2026-01-11T10:01:00Z",
            "parent_event_id": "event-1"
        },
        {
            "event_id": "event-3",
            "event_type": "web.search.completed",
            "timestamp": "2026-01-11T10:02:30Z",
            "parent_event_id": "event-2"
        }
    ]
}

# Query agent metrics
GET /v1/tracker/metrics?agent_id={agent_id}&period=7d

Response:
{
    "agent_id": "research-worker",
    "period": "7d",
    "total_tasks": 150,
    "completed_tasks": 145,
    "failed_tasks": 5,
    "avg_duration_seconds": 45.3,
    "success_rate": 0.967
}
```

---

### RF-ARCH-011: Task Progress Model

#### Two-Level Progress Tracking

**Coarse-grained (Required):** State transitions

```python
from soorma_common import TaskState, TaskStateChanged

# Worker publishes state change
await ctx.bus.publish(
    topic="system-events",
    event_type="task.state_changed",
    data=TaskStateChanged(
        task_id="task-123",
        plan_id="plan-456",
        previous_state=TaskState.PENDING,
        new_state=TaskState.RUNNING,
    ).model_dump()
)
```

**Fine-grained (Optional):** Progress percentage

```python
from soorma_common import TaskState, TaskProgressEvent

# Worker publishes progress update
await ctx.bus.publish(
    topic="system-events",
    event_type="task.progress",
    data=TaskProgressEvent(
        task_id="task-123",
        plan_id="plan-456",
        state=TaskState.RUNNING,
        progress=0.5,  # 50%
        message="Processing document 3 of 6",
    ).model_dump()
)
```

#### Task States

Defined in `soorma-common/tracking.py`:

| State | Description | Terminal? |
|-------|-------------|-----------|
| `pending` | Task created, not started | No |
| `running` | Task in progress | No |
| `delegated` | Task delegated to sub-agent | No |
| `waiting` | Waiting for sub-task results | No |
| `completed` | Successfully completed | Yes |
| `failed` | Failed with error | Yes |
| `cancelled` | Cancelled by user/system | Yes |

#### Database Schema

```sql
-- Task execution records
CREATE TABLE task_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL,
    task_id VARCHAR(100) NOT NULL,
    plan_id VARCHAR(100),
    event_type VARCHAR(255) NOT NULL,
    state VARCHAR(50) NOT NULL,
    progress FLOAT CHECK (progress >= 0 AND progress <= 1),
    message TEXT,
    data JSONB DEFAULT '{}',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    trace_id VARCHAR(100),
    parent_event_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, task_id)
);

CREATE INDEX task_executions_plan_idx ON task_executions (tenant_id, plan_id);
CREATE INDEX task_executions_trace_idx ON task_executions (tenant_id, trace_id);
CREATE INDEX task_executions_state_idx ON task_executions (tenant_id, state);

-- State transition history
CREATE TABLE state_transitions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL,
    task_id VARCHAR(100) NOT NULL,
    plan_id VARCHAR(100),
    from_state VARCHAR(50) NOT NULL,
    to_state VARCHAR(50) NOT NULL,
    reason TEXT,
    transitioned_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX state_transitions_task_idx ON state_transitions (tenant_id, task_id, transitioned_at);

-- Event timeline (for trace visualization)
CREATE TABLE event_timeline (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL,
    event_id VARCHAR(100) NOT NULL,
    event_type VARCHAR(255) NOT NULL,
    topic VARCHAR(100),
    trace_id VARCHAR(100),
    parent_event_id VARCHAR(100),
    correlation_id VARCHAR(100),
    data JSONB DEFAULT '{}',
    occurred_at TIMESTAMPTZ NOT NULL,
    UNIQUE(tenant_id, event_id)
);

CREATE INDEX event_timeline_trace_idx ON event_timeline (tenant_id, trace_id, occurred_at);
CREATE INDEX event_timeline_correlation_idx ON event_timeline (tenant_id, correlation_id);

-- Agent metrics (aggregated)
CREATE TABLE agent_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL,
    agent_id VARCHAR(100) NOT NULL,
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    total_tasks INT DEFAULT 0,
    completed_tasks INT DEFAULT 0,
    failed_tasks INT DEFAULT 0,
    avg_duration_seconds FLOAT,
    success_rate FLOAT,
    UNIQUE(tenant_id, agent_id, period_start)
);

CREATE INDEX agent_metrics_agent_period_idx ON agent_metrics (tenant_id, agent_id, period_start DESC);
```

---

## Implementation Steps

### Step 1: Create Tracker Service

```bash
# Create service structure
mkdir -p services/tracker/src/{subscribers,routes,db}
cd services/tracker

# Initialize service
poetry init
poetry add soorma-sdk soorma-common fastapi uvicorn asyncpg
```

### Step 2: Implement Event Subscribers

Create subscribers for each event type (shown above).

### Step 3: Implement Query APIs

Create FastAPI routes for read-only queries.

### Step 4: Database Migration

Create Alembic migration for schema.

### Step 5: Deploy & Subscribe

Deploy service, it automatically subscribes to topics.

### Step 6: Update SDK

Remove direct tracker API calls from SDK (see [sdk/03-COMMON-DTOS.md](../sdk/03-COMMON-DTOS.md)).

---

## Testing Strategy

### Unit Tests

```python
async def test_track_progress_event():
    """Tracker should record progress events."""
    event = EventEnvelope(
        source="worker",
        type="task.progress",
        topic="system-events",
        data={
            "task_id": "task-123",
            "state": "running",
            "progress": 0.5,
            "message": "Half done"
        }
    )
    
    await tracker.handle_event(event)
    
    # Verify database record
    task = await db.get_task_execution("task-123")
    assert task.progress == 0.5
    assert task.state == "running"

async def test_query_plan_status():
    """Should query plan execution status."""
    # Create test data
    await db.create_task_execution(task_id="task-1", plan_id="plan-123", state="completed")
    await db.create_task_execution(task_id="task-2", plan_id="plan-123", state="running")
    
    # Query via API
    response = await client.get("/v1/tracker/plans/plan-123")
    
    assert response["task_count"] == 2
    assert response["completed_tasks"] == 1
```

### Integration Tests

Test full flow:
- Worker publishes progress events
- Tracker receives and records
- Query APIs return correct data

---

## Dependencies

- **Depends on:** 01-EVENT-SERVICE (event envelope), 03-COMMON-LIBRARY (tracking DTOs)
- **Blocks:** None
- **Pairs with SDK:** [sdk/03-COMMON-DTOS.md](../sdk/03-COMMON-DTOS.md)

---

## Related Documents

- [00-OVERVIEW.md](00-OVERVIEW.md) - Passive service pattern
- [01-EVENT-SERVICE.md](01-EVENT-SERVICE.md) - Event envelope with trace_id
- [03-COMMON-LIBRARY.md](03-COMMON-LIBRARY.md) - Tracking DTOs
- [../sdk/03-COMMON-DTOS.md](../sdk/03-COMMON-DTOS.md) - SDK event publishing
