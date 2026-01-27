# Architecture Refactoring: Memory Service

**Document:** 02-MEMORY-SERVICE.md  
**Status:** ⬜ Not Started  
**Priority:** 🔴 High (Foundation)  
**Last Updated:** January 11, 2026

---

## Quick Reference

| Aspect | Details |
|--------|----------|
| **Tasks** | RF-ARCH-008: TaskContext Memory Type<br>RF-ARCH-009: Plan/Session Query APIs<br>RF-ARCH-012: Semantic Memory Upsert (Stage 2.1)<br>RF-ARCH-013: Working Memory Deletion (Stage 2.1)<br>RF-ARCH-014: Semantic Memory Privacy (Stage 2.1) |
| **Files** | Memory Service, database schema |
| **Pairs With SDK** | [sdk/02-MEMORY-SDK.md](../sdk/02-MEMORY-SDK.md) |
| **Dependencies** | None (foundational) |
| **Blocks** | Worker, Planner implementations |
| **Estimated Effort** | 2-3 days (Stage 2)<br>3-5 days (Stage 2.1) |

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

**Stage 2 (Foundation):**
- **RF-ARCH-008:** Add TaskContext storage for async Workers
- **RF-ARCH-009:** Add Plan/Session query APIs

**Stage 2.1 (Follow-up):**
- **RF-ARCH-012:** Semantic Memory Upsert with deduplication
- **RF-ARCH-013:** Working Memory Deletion endpoints
- **RF-ARCH-014:** Semantic Memory Privacy (user-scoped by default, optional public flag)

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

## Stage 2.1 Tasks (Follow-up)

### RF-ARCH-012: Semantic Memory Upsert

**Status:** ⬜ Not Started  
**Priority:** P1 (High) - Prevents data quality issues  
**Estimated Effort:** 2-3 days

#### Problem

Current semantic memory API creates duplicate entries when storing the same content multiple times:
- Same document ingested repeatedly → multiple embeddings
- Updated content creates new entry → old version persists
- No way to identify and update existing content

This causes:
- Wasted storage and embedding costs
- Duplicate/stale content in search results
- Confusion about which version is current

#### Solution: Upsert with Dual Constraints

Add `external_id` (user-provided) and `content_hash` (system-generated) columns for deduplication.

**Design Document:** [services/memory/SEMANTIC_MEMORY_UPSERT.md](../../../services/memory/SEMANTIC_MEMORY_UPSERT.md)

**Database Schema:**

```sql
-- Add columns to semantic_memory table
ALTER TABLE semantic_memory
ADD COLUMN external_id VARCHAR(255),
ADD COLUMN content_hash VARCHAR(64);

-- Create unique constraints
CREATE UNIQUE INDEX semantic_memory_external_id_idx 
    ON semantic_memory (tenant_id, user_id, external_id)
    WHERE external_id IS NOT NULL;

CREATE UNIQUE INDEX semantic_memory_content_hash_idx
    ON semantic_memory (tenant_id, user_id, content_hash);
```

**API Update:**

```python
# Upsert by external_id (user controls identity)
POST /v1/memory/semantic
{
    "content": "Docker is a containerization platform...",
    "external_id": "doc-123",  # Optional user-provided ID
    "metadata": {"source": "docs.docker.com"}
}

# If external_id provided → upsert on external_id
# If no external_id → upsert on content_hash (automatic deduplication)
```

**Versioning Support:**

```python
# Store with timestamp in metadata for version tracking
{
    "external_id": "doc-123",
    "content": "Updated content...",
    "metadata": {
        "version": "v2",
        "updated_at": "2026-01-22T10:00:00Z"
    }
}
```

**SDK Changes:**

See [sdk/02-MEMORY-SDK.md](../sdk/02-MEMORY-SDK.md) RF-SDK-019 for SDK method updates.

**Testing:**
- Duplicate content detection (same hash)
- External ID upsert behavior
- Version tracking via metadata
- Migration for existing data

---

### RF-ARCH-013: Working Memory Deletion

**Status:** ⬜ Not Started  
**Priority:** P2 (Medium) - Prevents data accumulation  
**Estimated Effort:** 1-2 days

#### Problem

Working memory is plan-scoped and temporary, but there's no cleanup mechanism:
- Plan state persists forever after plan completes
- No way to delete all keys for a plan
- No way to delete individual keys
- Data accumulates over time

**Current State:**
- `PUT /v1/memory/working/{plan_id}/{key}` - Set value ✅
- `GET /v1/memory/working/{plan_id}/{key}` - Get value ✅
- `DELETE /v1/memory/working/{plan_id}/{key}` - ❌ Missing
- `DELETE /v1/memory/working/{plan_id}` - ❌ Missing

#### Solution: Add DELETE Endpoints

**New Endpoints:**

```python
# Delete individual key
DELETE /v1/memory/working/{plan_id}/{key}

Response: 204 No Content (success)
          404 Not Found (key doesn't exist)

# Delete all keys for a plan
DELETE /v1/memory/working/{plan_id}

Response: 
{
    "deleted_count": 5,
    "plan_id": "plan-123"
}
```

**Database Operations:**

```python
# Delete single key
DELETE FROM working_memory 
WHERE tenant_id = $1 AND plan_id = $2 AND key = $3;

# Delete all keys for plan
DELETE FROM working_memory
WHERE tenant_id = $1 AND plan_id = $2;
```

**SDK Changes:**

See [sdk/02-MEMORY-SDK.md](../sdk/02-MEMORY-SDK.md) RF-SDK-020 for SDK method updates and usage patterns.

**Testing:**
- Delete individual keys
- Delete entire plan state
- Delete non-existent keys (idempotent)
- RLS enforcement (can't delete other tenant's data)

---

### RF-ARCH-014: Semantic Memory Privacy

**Status:** ⬜ Not Started  
**Priority:** P1 (High) - Fundamental privacy model  
**Estimated Effort:** 2-3 days

#### Problem

Current semantic memory is **tenant-scoped** (public to all users in tenant):
- ❌ Agent memory should be private to the user by default
- ❌ Cross-user memory leakage is a privacy/security concern
- ❌ No control over knowledge visibility

**Key Insight:** Semantic memory is **agent memory (CoALA framework)**, not a RAG solution. It's for individual user/agent workflows, not shared knowledge bases.

#### Solution: User-Scoped Privacy with Optional Public Flag

**Design Principle:** Private by default, explicitly public when needed.

**Database Schema:**

```sql
-- Add user_id column (required)
ALTER TABLE semantic_memory
ADD COLUMN user_id VARCHAR(255) NOT NULL;

-- Add is_public flag (default private)
ALTER TABLE semantic_memory
ADD COLUMN is_public BOOLEAN NOT NULL DEFAULT FALSE;

-- Update unique constraints
-- For private knowledge: unique per user
CREATE UNIQUE INDEX semantic_memory_user_external_id_private_idx
    ON semantic_memory (tenant_id, user_id, external_id)
    WHERE external_id IS NOT NULL AND is_public = FALSE;

-- For public knowledge: unique per tenant
CREATE UNIQUE INDEX semantic_memory_tenant_external_id_public_idx
    ON semantic_memory (tenant_id, external_id)
    WHERE external_id IS NOT NULL AND is_public = TRUE;

-- Content hash constraints
CREATE UNIQUE INDEX semantic_memory_user_content_hash_private_idx
    ON semantic_memory (tenant_id, user_id, content_hash)
    WHERE is_public = FALSE;

CREATE UNIQUE INDEX semantic_memory_tenant_content_hash_public_idx
    ON semantic_memory (tenant_id, content_hash)
    WHERE is_public = TRUE;
```

**RLS Policies:**

```sql
-- Read: Users can read their own private OR public knowledge in tenant
CREATE POLICY semantic_memory_read_policy ON semantic_memory
FOR SELECT
USING (
  (tenant_id = current_setting('app.current_tenant_id')::TEXT)
  AND (
    (user_id = current_setting('app.current_user_id')::TEXT) OR
    (is_public = TRUE)
  )
);

-- Write: Users can only write their own knowledge
CREATE POLICY semantic_memory_write_policy ON semantic_memory
FOR INSERT
WITH CHECK (
  (tenant_id = current_setting('app.current_tenant_id')::TEXT)
  AND (user_id = current_setting('app.current_user_id')::TEXT)
);

-- Update: Users can only update their own knowledge
CREATE POLICY semantic_memory_update_policy ON semantic_memory
FOR UPDATE
USING (
  (tenant_id = current_setting('app.current_tenant_id')::TEXT)
  AND (user_id = current_setting('app.current_user_id')::TEXT)
);
```

**Updated CRUD Functions:**

```python
async def upsert_semantic_memory(
    db: AsyncSession,
    tenant_id: str,
    user_id: str,              # NEW: Required
    content: str,
    embedding: List[float],
    metadata: Optional[Dict] = None,
    external_id: Optional[str] = None,
    content_hash: Optional[str] = None,
    is_public: bool = False,    # NEW: Default private
    tags: Optional[List[str]] = None,
    source: Optional[str] = None,
    plan_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> SemanticMemory:
    """
    Upsert semantic memory entry (private by default).
    
    Args:
        user_id: Required. User who owns this knowledge.
        is_public: If True, visible to all users in tenant.
                  If False (default), only visible to this user.
    """

async def query_semantic_memory(
    db: AsyncSession,
    tenant_id: str,
    user_id: str,              # NEW: Required
    query_embedding: List[float],
    top_k: int = 10,
    include_public: bool = True, # NEW: Include public knowledge
    filters: Optional[Dict] = None,
) -> List[SemanticMemory]:
    """
    Query semantic memory (user's private + optional public knowledge).
    
    Returns:
        User's private knowledge + public knowledge (if include_public=True)
    """
```

**API Update:**

```python
# Store private knowledge (default)
POST /v1/memory/semantic
{
    "content": "My personal research notes...",
    "user_id": "user-123",          # Required
    "external_id": "research-2026",  # Optional
    "is_public": false               # Default
}

# Store public knowledge (explicitly shared)
POST /v1/memory/semantic
{
    "content": "Team-approved best practices...",
    "user_id": "user-123",
    "external_id": "best-practices",
    "is_public": true  # Visible to all users in tenant
}
```

**Query Behavior:**

```python
# Query returns user's private + public knowledge
GET /v1/memory/semantic/query
{
    "query_embedding": [...],
    "user_id": "user-123",
    "include_public": true  # Default
}
# Returns: User's private knowledge + tenant's public knowledge

# Query only private knowledge
GET /v1/memory/semantic/query
{
    "query_embedding": [...],
    "user_id": "user-123",
    "include_public": false
}
# Returns: User's private knowledge only
```

**SDK Changes:**

See [sdk/02-MEMORY-SDK.md](../sdk/02-MEMORY-SDK.md) RF-SDK-021 for SDK method updates.

**Migration Strategy:**

For existing rows without user_id:
```python
# Create system user or use current user context
UPDATE semantic_memory
SET user_id = 'system-user'  # or migrate to specific user
WHERE user_id IS NULL;
```

**Testing:**
- Private knowledge isolation between users
- Public knowledge visible across users in tenant
- Cross-tenant isolation (public knowledge not visible across tenants)
- Upsert behavior with privacy constraints
- Query returns correct union (private + public)
- RLS enforcement at database level
- Backward compatibility for existing clients

**Use Cases:**

```python
# Use Case 1: User's personal research findings (private)
await memory.store_knowledge(
    content="Research findings on quantum computing...",
    user_id="alice",
    external_id="quantum-research-2026",
    is_public=False  # Only Alice sees this
)

# Use Case 2: Shared team best practices (public)
await memory.store_knowledge(
    content="Our team's API design best practices...",
    user_id="bob",
    external_id="api-best-practices",
    is_public=True  # All team members see this
)

# Use Case 3: Query returns both private and public
results = await memory.query_knowledge(
    query_embedding=embedding,
    user_id="alice",
    include_public=True  # Returns Alice's private + team's public
)
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
