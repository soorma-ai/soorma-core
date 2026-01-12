# Architecture Refactoring: Memory Service

**Document:** 02-MEMORY-SERVICE.md  
**Status:** ⬜ Not Started  
**Priority:** 🔴 High (Foundation)  
**Last Updated:** January 11, 2026

---

## Quick Reference

| Aspect | Details |
|--------|----------|
| **Tasks** | RF-ARCH-008: TaskContext Memory Type, RF-ARCH-009: Plan/Session Query APIs |
| **Files** | Memory Service, database schema |
| **Pairs With SDK** | [sdk/02-MEMORY-SDK.md](../sdk/02-MEMORY-SDK.md) |
| **Dependencies** | None (foundational) |
| **Blocks** | Worker, Planner implementations |
| **Estimated Effort** | 2-3 days |

---

## Context

### Why This Matters

Memory Service provides **persistent storage** for async agent workflows:

1. **Task Context** - Workers persist state when delegating, restore on completion
2. **Plan Context** - Planners persist state machine across event transitions
3. **Sessions** - Group related plans for long-running conversations

### Current State

Memory Service has CoALA memory types (semantic, episodic, procedural, working) but lacks:
- Explicit task context storage for async completion
- Plan context with state machine tracking
- Query APIs for active plans/sessions

### Key Files

```
services/memory/
├── src/
│   ├── models/         # Task/Plan context schemas
│   ├── routes/         # REST API endpoints
│   └── db/            # Database layer
└── migrations/        # Schema migrations
```

---

## Summary

This document covers Memory Service enhancements:
- **RF-ARCH-008:** Add TaskContext storage for async Workers
- **RF-ARCH-009:** Add Plan/Session query APIs

These endpoints are consumed by SDK MemoryClient (see [sdk/02-MEMORY-SDK.md](../sdk/02-MEMORY-SDK.md)).

---

## Tasks

### RF-ARCH-008: TaskContext Memory Type

**Files:** Memory Service

#### Problem

Workers need to:
1. Persist task state when delegating to sub-agents
2. Restore task state when sub-task results arrive
3. Support lookup by sub-task ID (to find parent task)

Current working memory (`plan_id` + `key`) is insufficient.

#### Solution: Dedicated Task Context Storage

**New Endpoints:**

```python
# Store task context
POST /v1/memory/task-context
{
    "task_id": "task-123",
    "plan_id": "plan-456",          # Optional, for grouping
    "event_type": "research.requested",
    "response_event": "research.completed",
    "response_topic": "action-results",
    "data": {...},                   # Original request data
    "sub_tasks": [],                 # List of delegated sub-task IDs
    "state": {}                      # Worker-specific state
}

Response:
{
    "task_id": "task-123",
    "created_at": "2026-01-11T10:00:00Z"
}

# Retrieve task context
GET /v1/memory/task-context/{task_id}

Response:
{
    "task_id": "task-123",
    "plan_id": "plan-456",
    "event_type": "research.requested",
    "response_event": "research.completed",
    "response_topic": "action-results",
    "data": {...},
    "sub_tasks": ["subtask-1", "subtask-2"],
    "state": {"progress": 0.5},
    "created_at": "2026-01-11T10:00:00Z",
    "updated_at": "2026-01-11T10:05:00Z"
}

# Update task context (add sub-task, update state)
PUT /v1/memory/task-context/{task_id}
{
    "sub_tasks": ["subtask-1", "subtask-2", "subtask-3"],  # Updated list
    "state": {"progress": 0.75}                            # Updated state
}

# Find parent task by sub-task ID
GET /v1/memory/task-context/by-subtask/{subtask_id}

Response:
{
    "task_id": "task-123",
    "plan_id": "plan-456",
    ...
}

# Delete task context (on completion)
DELETE /v1/memory/task-context/{task_id}
```

#### Database Schema

```sql
CREATE TABLE task_context (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    task_id VARCHAR(100) NOT NULL,
    plan_id VARCHAR(100),
    event_type VARCHAR(255) NOT NULL,
    response_event VARCHAR(255),
    response_topic VARCHAR(100) DEFAULT 'action-results',
    data JSONB NOT NULL DEFAULT '{}',
    sub_tasks JSONB DEFAULT '[]',
    state JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, task_id)
);

CREATE INDEX task_context_plan_idx ON task_context (tenant_id, plan_id);
CREATE INDEX task_context_subtasks_idx ON task_context USING GIN (sub_tasks);

-- RLS policies
ALTER TABLE task_context ENABLE ROW LEVEL SECURITY;

CREATE POLICY task_context_tenant_isolation 
    ON task_context 
    FOR ALL 
    USING (tenant_id = current_setting('app.tenant_id')::UUID);
```

#### SDK Usage

See [sdk/02-MEMORY-SDK.md](../sdk/02-MEMORY-SDK.md) for SDK MemoryClient implementation.

```python
# Worker saves context when delegating
@worker.on_task("research.requested")
async def handle_research(task: TaskContext, ctx: PlatformContext):
    # Persist task state
    await task.save()  # → POST /v1/memory/task-context
    
    # Delegate to sub-agents
    sub_task_id = await task.delegate(...)
    
    # Update with sub-task ID
    task.sub_tasks.append(sub_task_id)
    await task.save()  # → PUT /v1/memory/task-context/{task_id}

# Worker restores context when receiving results
@worker.on_result("web.search.completed")
async def handle_search_result(result: ResultEvent, ctx: PlatformContext):
    # Restore parent task by sub-task ID
    task = await TaskContext.restore_by_subtask(result.correlation_id)
    
    # Process result, check if all sub-tasks done
    task.sub_tasks.remove(result.correlation_id)
    if not task.sub_tasks:
        await task.complete({"results": ...})
```

---

### RF-ARCH-009: Query Active Plans/Sessions

**Files:** Memory Service

#### Problem

Users and UI need to:
1. List active plans (ongoing goals)
2. List conversation sessions
3. Query plan/session details

Tracker is for observability/metrics, not user queries.

#### Solution: Memory Service Query APIs

**Plan Management:**

```python
# Create plan record
POST /v1/memory/plans
{
    "plan_id": "plan-123",
    "goal_event": "research.goal",
    "goal_data": {"topic": "AI trends"},
    "status": "running"
}

# List plans for user
GET /v1/memory/plans?status=active&limit=10

Response:
{
    "plans": [
        {
            "plan_id": "plan-123",
            "goal_event": "research.goal",
            "goal_data": {"topic": "AI trends"},
            "status": "running",
            "created_at": "2026-01-11T10:00:00Z",
            "updated_at": "2026-01-11T10:05:00Z"
        }
    ],
    "count": 1
}

# Get plan details
GET /v1/memory/plans/{plan_id}

Response:
{
    "plan_id": "plan-123",
    "goal_event": "research.goal",
    "goal_data": {"topic": "AI trends"},
    "status": "running",
    "state": {...},  # Planner state machine
    "created_at": "2026-01-11T10:00:00Z",
    "updated_at": "2026-01-11T10:05:00Z"
}

# Update plan status
PUT /v1/memory/plans/{plan_id}
{
    "status": "completed",
    "state": {...}  # Updated state machine
}

# Delete plan (cleanup)
DELETE /v1/memory/plans/{plan_id}
```

**Session Management:**

```python
# Create session
POST /v1/memory/sessions
{
    "session_id": "sess-456",
    "agent_id": "research-advisor",
    "metadata": {"source": "web-ui"}
}

# List sessions for user
GET /v1/memory/sessions?limit=10

Response:
{
    "sessions": [
        {
            "session_id": "sess-456",
            "agent_id": "research-advisor",
            "created_at": "2026-01-11T09:00:00Z",
            "last_interaction": "2026-01-11T10:30:00Z",
            "metadata": {"source": "web-ui"}
        }
    ],
    "count": 1
}

# Get session details
GET /v1/memory/sessions/{session_id}

# Update session (touch last_interaction)
PUT /v1/memory/sessions/{session_id}
{
    "last_interaction": "2026-01-11T10:35:00Z"
}

# Delete session
DELETE /v1/memory/sessions/{session_id}
```

#### Database Schema

```sql
-- Plans table
CREATE TABLE plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    plan_id VARCHAR(100) NOT NULL,
    goal_event VARCHAR(255) NOT NULL,
    goal_data JSONB DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'running',  -- running, completed, failed, cancelled
    state JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, plan_id)
);

CREATE INDEX plans_user_status_idx ON plans (tenant_id, user_id, status);
CREATE INDEX plans_created_idx ON plans (tenant_id, created_at DESC);

-- Sessions table
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    session_id VARCHAR(100) NOT NULL,
    agent_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_interaction TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    UNIQUE(tenant_id, session_id)
);

CREATE INDEX sessions_user_idx ON sessions (tenant_id, user_id, last_interaction DESC);

-- RLS policies
ALTER TABLE plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY plans_user_isolation 
    ON plans 
    FOR ALL 
    USING (
        tenant_id = current_setting('app.tenant_id')::UUID 
        AND user_id = current_setting('app.user_id')::UUID
    );

CREATE POLICY sessions_user_isolation 
    ON sessions 
    FOR ALL 
    USING (
        tenant_id = current_setting('app.tenant_id')::UUID 
        AND user_id = current_setting('app.user_id')::UUID
    );
```

---

## Authentication Context

All Memory Service endpoints use JWT authentication:

- `tenant_id`, `user_id` extracted from token
- RLS policies automatically filter by tenant/user
- SDK doesn't need to pass these explicitly

**SDK MemoryClient:**
```python
# SDK extracts auth from PlatformContext
memory = ctx.memory

# No need to pass tenant_id/user_id
await memory.store_task_context(task_id="task-123", ...)
plans = await memory.list_plans(status="active")
```

---

## Implementation Steps

### Step 1: Database Migration

Create migration for new tables:
- `task_context`
- `plans`
- `sessions`

### Step 2: Add Service Endpoints

Implement REST endpoints in Memory Service:
- Task context CRUD
- Plan management
- Session management

### Step 3: Update SDK MemoryClient

See [sdk/02-MEMORY-SDK.md](../sdk/02-MEMORY-SDK.md) for SDK implementation.

### Step 4: Update Worker/Planner

Workers and Planners use new memory methods:
- [sdk/05-WORKER-MODEL.md](../sdk/05-WORKER-MODEL.md)
- [sdk/06-PLANNER-MODEL.md](../sdk/06-PLANNER-MODEL.md)

---

## Testing Strategy

### Unit Tests

```python
async def test_store_task_context():
    """Should store task context with sub-tasks."""
    context = {
        "task_id": "task-123",
        "event_type": "research.requested",
        "response_event": "research.completed",
        "data": {"query": "AI trends"},
        "sub_tasks": ["sub-1", "sub-2"]
    }
    
    response = await memory.store_task_context(**context)
    assert response["task_id"] == "task-123"

async def test_find_by_subtask():
    """Should find parent task by sub-task ID."""
    # Store parent task
    await memory.store_task_context(
        task_id="task-123",
        sub_tasks=["sub-1"]
    )
    
    # Find by sub-task
    parent = await memory.get_task_by_subtask("sub-1")
    assert parent["task_id"] == "task-123"

async def test_list_active_plans():
    """Should list only active plans for user."""
    # Create plans
    await memory.create_plan(plan_id="plan-1", status="running")
    await memory.create_plan(plan_id="plan-2", status="completed")
    
    # List active only
    plans = await memory.list_plans(status="active")
    assert len(plans) == 1
    assert plans[0]["plan_id"] == "plan-1"
```

### Integration Tests

Test full Worker async flow:
- Worker receives task → saves context
- Worker delegates → updates sub_tasks
- Results arrive → restores by sub-task ID
- All sub-tasks done → completes and deletes context

---

## Dependencies

- **Depends on:** Nothing (foundational)
- **Blocks:** Worker, Planner implementations
- **Pairs with SDK:** [sdk/02-MEMORY-SDK.md](../sdk/02-MEMORY-SDK.md)

---

## Related Documents

- [00-OVERVIEW.md](00-OVERVIEW.md) - Service responsibilities
- [../sdk/02-MEMORY-SDK.md](../sdk/02-MEMORY-SDK.md) - SDK MemoryClient methods
- [../sdk/05-WORKER-MODEL.md](../sdk/05-WORKER-MODEL.md) - Worker async pattern
- [../sdk/06-PLANNER-MODEL.md](../sdk/06-PLANNER-MODEL.md) - Planner state machine
