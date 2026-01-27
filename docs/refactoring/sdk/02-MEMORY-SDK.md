# SDK Refactoring: Memory SDK

**Document:** 02-MEMORY-SDK.md  
**Status:** ⬜ Not Started  
**Priority:** � High (Foundation)  
**Last Updated:** January 11, 2026

---

## Quick Reference

| Aspect | Details |
|--------|----------|
| **Tasks** | RF-SDK-010: Memory SDK Methods<br>RF-SDK-014: WorkflowState Helper Class<br>RF-SDK-019: Semantic Memory Upsert SDK (Stage 2.1)<br>RF-SDK-020: Working Memory Deletion SDK (Stage 2.1)<br>RF-SDK-021: Semantic Memory Privacy SDK (Stage 2.1) |
| **Files** | `sdk/python/soorma/context.py`, `sdk/python/soorma/workflow.py`, Memory Service |
| **Pairs With Arch** | [arch/02-MEMORY-SERVICE.md](../arch/02-MEMORY-SERVICE.md) |
| **Dependencies** | None (foundational) |
| **Blocks** | 05-WORKER-MODEL, 06-PLANNER-MODEL |
| **Estimated Effort** | 1-2 days (Stage 2)<br>2-3 days (Stage 2.1) |

---

## Context

### Why This Matters

The Memory SDK is **foundational** for the async Worker and Planner models:

1. **Workers** need to persist `TaskContext` when delegating to sub-agents, then restore it when results arrive
2. **Planners** need to persist `PlanContext` (state machine) across event-driven transitions
3. **Sessions** group related plans for long-running conversations

### Current State

The SDK has basic working memory methods (`store()`, `retrieve()`) but lacks:
- Task context storage for async Worker completion
- Plan context storage for Planner state machine
- Session/Plan management for long-running conversations

### Key Files

```
sdk/python/soorma/
├── context.py          # PlatformContext with MemoryClient
└── agents/
    ├── worker.py       # Will use memory for TaskContext
    └── planner.py      # Will use memory for PlanContext
```

---

## Summary

This document covers the Memory SDK client alignment:
- **RF-SDK-010:** Memory SDK Methods for Task/Plan Context
- **RF-SDK-014:** WorkflowState Helper Class
- **RF-SDK-019:** Semantic Memory Upsert SDK (Stage 2.1)
- **RF-SDK-020:** Working Memory Deletion SDK (Stage 2.1)
- **RF-SDK-021:** Semantic Memory Privacy SDK (Stage 2.1)

This enables async Worker completion and Planner state machine persistence.

---

## Tasks

### RF-SDK-010: Memory SDK Alignment with Service Endpoints

**Files:** [context.py](../../sdk/python/soorma/context.py), Memory Service

#### Current Issue

SDK has basic working memory methods but lacks:
- Task context storage for async Worker completion
- Plan context storage for Planner state machine
- Session/Plan management for long-running conversations

---

## Memory Service Endpoints vs SDK Methods

| Service Endpoint | SDK Method | Status |
|-----------------|------------|--------|
| **Task Context** | | |
| `POST /v1/memory/task-context` | `memory.store_task_context()` | NEW (Stage 2) |
| `GET /v1/memory/task-context/{id}` | `memory.get_task_context()` | NEW (Stage 2) |
| `DELETE /v1/memory/task-context/{id}` | `memory.delete_task_context()` | NEW (Stage 2) |
| `GET /v1/memory/task-context/by-subtask/{id}` | `memory.get_task_by_subtask()` | NEW (Stage 2) |
| **Plan Context** | | |
| `POST /v1/memory/plan-context` | `memory.store_plan_context()` | NEW (Stage 2) |
| `GET /v1/memory/plan-context/{id}` | `memory.get_plan_context()` | NEW (Stage 2) |
| `GET /v1/memory/plan-context/by-correlation/{id}` | `memory.get_plan_by_correlation()` | NEW (Stage 2) |
| **Plans & Sessions** | | |
| `POST /v1/memory/plans` | `memory.create_plan()` | NEW (Stage 2) |
| `GET /v1/memory/plans` | `memory.list_plans()` | NEW (Stage 2) |
| `PUT /v1/memory/plans/{id}` | `memory.update_plan()` | NEW (Stage 2) |
| `DELETE /v1/memory/plans/{id}` | `memory.delete_plan_record()` | NEW (Stage 2) |
| `POST /v1/memory/sessions` | `memory.create_session()` | NEW (Stage 2) |
| `GET /v1/memory/sessions` | `memory.list_sessions()` | NEW (Stage 2) |
| `GET /v1/memory/sessions/{id}` | `memory.get_session()` | NEW (Stage 2) |
| `DELETE /v1/memory/sessions/{id}` | `memory.delete_session()` | NEW (Stage 2) |
| **Semantic Memory** | | |
| `POST /v1/memory/semantic` | `memory.store_knowledge()` | Existing |
| `POST /v1/memory/semantic` (with `external_id`) | `memory.store_knowledge(external_id=...)` | **NEW (Stage 2.1 - RF-SDK-019)** |
| `POST /v1/memory/semantic/search` | `memory.search_knowledge()` | Existing |
| **Working Memory** | | |
| `PUT /v1/memory/working/{plan_id}/{key}` | `memory.set_plan_state()` | Existing |
| `GET /v1/memory/working/{plan_id}/{key}` | `memory.get_plan_state()` | Existing |
| `DELETE /v1/memory/working/{plan_id}/{key}` | `memory.delete_plan_state()` | **NEW (Stage 2.1 - RF-SDK-020)** |
| `DELETE /v1/memory/working/{plan_id}` | `memory.delete_plan()` | **NEW (Stage 2.1 - RF-SDK-020)** |
| `POST /v1/working-memory/{plan_id}` | `memory.store()` (deprecated) | Legacy |
| `GET /v1/working-memory/{plan_id}/{key}` | `memory.retrieve()` (deprecated) | Legacy |

---

## Authentication Context

- `tenant_id`, `user_id`, `agent_id` are derived from the authentication token
- SDK extracts these from `PlatformContext` which is initialized with auth
- Memory Service validates token and uses RLS policies based on extracted IDs
- **SDK methods do NOT need to pass these as explicit parameters**

---

## Target Design

### MemoryClient

```python
class MemoryClient:
    """
    Memory service client.
    
    Authentication context (tenant_id, user_id) is derived from the platform
    context's authentication token. All operations are automatically scoped
    to the authenticated user's tenant.
    """
    
    # === Task Context (for async Worker completion) ===
    
    async def store_task_context(
        self,
        task_id: str,
        plan_id: str,
        context: Dict[str, Any],
    ) -> bool:
        """
        Store task context for async completion.
        
        Called by TaskContext.save() when Worker delegates to sub-agent.
        """
        pass
    
    async def get_task_context(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve task context.
        
        Called by TaskContext.restore() when Worker resumes after result.
        """
        pass
    
    async def delete_task_context(self, task_id: str) -> bool:
        """
        Delete task context after completion.
        
        Called by TaskContext.complete() to cleanup.
        """
        pass
    
    async def get_task_by_subtask(self, sub_task_id: str) -> Optional[Dict[str, Any]]:
        """
        Find parent task by sub-task correlation ID.
        
        Called by ResultContext.restore_task() to find parent task.
        """
        pass
    
    # === Plan Context (for Planner state machine) ===
    
    async def store_plan_context(
        self,
        plan_id: str,
        session_id: Optional[str],
        context: Dict[str, Any],
    ) -> bool:
        """
        Store plan context.
        
        Called by PlanContext.save() after state transitions.
        """
        pass
    
    async def get_plan_context(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve plan context.
        
        Called by PlanContext.restore() to resume plan execution.
        """
        pass
    
    async def get_plan_by_correlation(self, correlation_id: str) -> Optional[Dict[str, Any]]:
        """
        Find plan by task/step correlation ID.
        
        Called when a transition event arrives to find the owning plan.
        """
        pass
    
    # === Plans & Sessions Management ===
    
    async def create_plan(
        self,
        goal_event: str,
        goal_data: Dict[str, Any],
        response_event: str,
        session_id: Optional[str] = None,
        parent_plan_id: Optional[str] = None,
    ) -> PlanSummary:
        """
        Create a new plan record.
        
        Called when a Planner receives a goal and creates a plan.
        Returns the created plan with generated plan_id.
        """
        pass
    
    async def create_session(
        self,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SessionSummary:
        """
        Create a new session/conversation record.
        
        Sessions group related plans and provide conversation context.
        """
        pass
    
    async def list_plans(
        self,
        status: Optional[str] = None,  # active, completed, failed, paused
        session_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[PlanSummary]:
        """
        List plans for the authenticated user.
        
        Sessions represent conversation threads. Plans may be grouped by session.
        """
        pass
    
    async def list_sessions(
        self,
        limit: int = 20,
    ) -> List[SessionSummary]:
        """
        List active sessions/conversations for the authenticated user.
        
        A session groups related plans and interactions over time.
        """
        pass
    
    # === Working Memory (plan-scoped key-value) ===
    
    async def store(
        self,
        key: str,
        value: Any,
        plan_id: str,
    ) -> bool:
        """Store key-value in plan-scoped working memory."""
        pass
    
    async def retrieve(
        self,
        key: str,
        plan_id: str,
    ) -> Optional[Any]:
        """Retrieve value from plan-scoped working memory."""
        pass
```

### Summary DTOs

```python
@dataclass
class PlanSummary:
    """Summary of a plan for listing."""
    plan_id: str
    goal_event: str
    status: str
    session_id: Optional[str]
    created_at: str
    updated_at: str


@dataclass
class SessionSummary:
    """Summary of a session for listing."""
    session_id: str
    name: Optional[str]
    plan_count: int
    created_at: str
    last_activity: str
```

---

## Sessions vs Plans

- **Session:** A conversation/interaction thread. Can contain multiple plans.
- **Plan:** A specific goal execution. Belongs to one session (optional).

### Example: Chatbot Scenario

- Each conversation topic = one session
- Each user goal within that conversation = one plan
- Multiple plans can be active within a session

```
User (tenant_id + user_id)
├── Session A (conversation about "AI research")
│   ├── Plan A1 (goal: "find papers") - completed
│   ├── Plan A2 (goal: "summarize findings") - running
│   │   └── Sub-plan A2.1 (delegated sub-goal) - running
│   └── Plan A3 (goal: "draft report") - pending
│
├── Session B (conversation about "budget planning")
│   └── Plan B1 (goal: "analyze expenses") - paused
```

---

## Usage Examples

### Worker Using Memory for Async Completion

```python
@worker.on_task(event_type="research.requested")
async def handle_research(task: TaskContext, context: PlatformContext):
    # TaskContext.save() calls memory.store_task_context()
    await task.save()
    
    await task.delegate(
        event_type="web.search.requested",
        data={"query": task.data["topic"]},
        response_event="web.search.completed",
    )

@worker.on_result(event_type="web.search.completed")
async def handle_result(result: ResultContext, context: PlatformContext):
    # ResultContext.restore_task() calls memory.get_task_by_subtask()
    task = await result.restore_task()
    await task.complete({"findings": result.data})
    # task.complete() calls memory.delete_task_context()
```

### Planner Creating Plans with Sessions

```python
@planner.on_goal(event_type="research.goal")
async def handle_goal(goal: GoalContext, context: PlatformContext):
    # Create or find session
    session = await context.memory.create_session(
        name="Research: " + goal.data.get("topic", "unknown"),
    )
    
    # Create plan with session
    plan_summary = await context.memory.create_plan(
        goal_event=goal.event_type,
        goal_data=goal.data,
        response_event=goal.response_event,
        session_id=session.session_id,
    )
    
    # Build PlanContext with state machine
    plan = PlanContext(
        plan_id=plan_summary.plan_id,
        session_id=session.session_id,
        ...
    )
    await plan.execute_next()
```

### Listing Plans and Sessions

```python
# List active plans for current user
active_plans = await context.memory.list_plans(status="active")

# List plans in a specific session
session_plans = await context.memory.list_plans(session_id="session-123")

# List all sessions
sessions = await context.memory.list_sessions()
```

---

## Tests to Add

```python
# test/test_memory_client.py

async def test_store_task_context():
    """store_task_context should persist task data."""
    pass

async def test_get_task_context():
    """get_task_context should retrieve stored task."""
    pass

async def test_get_task_by_subtask():
    """get_task_by_subtask should find parent task."""
    pass

async def test_delete_task_context():
    """delete_task_context should cleanup task."""
    pass

async def test_store_plan_context():
    """store_plan_context should persist plan data."""
    pass

async def test_get_plan_context():
    """get_plan_context should retrieve stored plan."""
    pass

async def test_create_plan():
    """create_plan should return new plan with ID."""
    pass

async def test_create_session():
    """create_session should return new session with ID."""
    pass

async def test_list_plans_filters():
    """list_plans should filter by status and session."""
    pass
```

---

### RF-SDK-014: WorkflowState Helper Class

**Files:** [context.py](../../sdk/python/soorma/context.py) or new `workflow.py`

#### Motivation

Example code (research-advisor planner) has ~50+ lines of boilerplate for managing plan state:
```python
# Manual working memory management (boilerplate)
workflow_state = await context.memory.retrieve("workflow_state", plan_id=plan_id) or {}
action_history = workflow_state.get('action_history', [])
action_history.append(event_name)
workflow_state['action_history'] = action_history
await context.memory.store("workflow_state", workflow_state, plan_id=plan_id)
```

This pattern repeats across all planner examples. Should be a helper.

#### Target Design

```python
from soorma.workflow import WorkflowState

@planner.on_goal("research.goal")
async def handle_goal(goal, context):
    plan_id = goal.correlation_id
    state = WorkflowState(context, plan_id)
    
    # Simple state operations
    await state.record_action("research.requested")
    await state.set("research_data", research_results)
    
    # Query state
    history = await state.get_action_history()
    data = await state.get("research_data")
    all_state = await state.get_all()
```

#### Implementation

```python
# sdk/python/soorma/workflow.py
from typing import Any, Dict, List, Optional
from .context import PlatformContext

class WorkflowState:
    """
    Helper for managing plan-scoped working memory state.
    
    **Concurrency Note:** Each instance represents a snapshot of state.
    In distributed scenarios with concurrent updates (multiple agents updating
    same plan), always create a fresh instance per event handler to avoid
    stale reads. The Memory Service should handle concurrent writes via
    optimistic locking or last-write-wins.
    """
    
    def __init__(self, context: PlatformContext, plan_id: str):
        self.context = context
        self.plan_id = plan_id
    
    async def _load_state(self) -> Dict[str, Any]:
        """Load state from memory (always fresh from Memory Service)."""
        return await self.context.memory.retrieve(
            "workflow_state", 
            plan_id=self.plan_id
        ) or {"action_history": []}
    
    async def _save_state(self, state: Dict[str, Any]):
        """Save state to memory."""
        await self.context.memory.store(
            "workflow_state", 
            state, 
            plan_id=self.plan_id
        )
    
    async def record_action(self, event_name: str):
        """
        Append action to history.
        
        **Concurrency:** Uses read-modify-write. In high-concurrency scenarios,
        consider Memory Service providing atomic append operations.
        """
        state = await self._load_state()
        state["action_history"].append(event_name)
        await self._save_state(state)
    
    async def get_action_history(self) -> List[str]:
        """Get action history (fresh read from Memory Service)."""
        state = await self._load_state()
        return state.get("action_history", [])
    
    async def set(self, key: str, value: Any):
        """Set a state value (read-modify-write)."""
        state = await self._load_state()
        state[key] = value
        await self._save_state(state)
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Get a state value (fresh read from Memory Service)."""
        state = await self._load_state()
        return state.get(key, default)
    
    async def get_all(self) -> Dict[str, Any]:
        """Get entire state dictionary (fresh read from Memory Service)."""
        return await self._load_state()
    
    async def clear(self):
        """Clear all state."""
        await self._save_state({"action_history": []})
```

#### Concurrency Considerations

**Problem:** In DisCo distributed architecture, multiple agents may update the same plan state concurrently:
- Planner publishes task → Worker A starts
- Worker A publishes sub-task → Worker B starts  
- Both Workers try to update plan state simultaneously

**Solutions:**

1. **No Instance Caching** (implemented above):
   - Each operation reads fresh from Memory Service
   - Prevents stale reads within same event handler
   - Still has race condition on read-modify-write

2. **Memory Service Atomic Operations** (future enhancement):
   ```python
   # Instead of read-modify-write
   await state.record_action("event")  # Race condition!
   
   # Atomic append in Memory Service
   await context.memory.append_to_list(
       key="workflow_state.action_history",
       plan_id=plan_id,
       value="event"
   )
   ```

3. **Optimistic Locking** (future enhancement):
   ```python
   # Memory Service returns version with state
   state, version = await context.memory.retrieve_with_version(...)
   
   # Update with version check
   await context.memory.store_if_version_matches(
       data=state,
       expected_version=version,
       plan_id=plan_id
   )  # Raises ConflictError if version changed
   ```

**Recommendation for MVP:**
- Use WorkflowState for **single-agent sequential workflows** (safe)
- For **concurrent multi-agent workflows**, add Memory Service atomic operations in Phase 2
- Document concurrency limitations clearly

#### Benefits

- **Reduces boilerplate**: 50+ lines → 10 lines in examples
- **Prevents errors**: No manual dict manipulation
- **Fresh reads**: No stale cached data
- **Consistent API**: Same pattern across all planners

#### Limitations

- **Read-modify-write race conditions** in concurrent scenarios
- **No atomic operations** (future Memory Service enhancement)
- **Best for sequential workflows** where one agent owns plan state at a time

---

## Stage 2.1 SDK Tasks (Follow-up)

### RF-SDK-019: Semantic Memory Upsert SDK

**Status:** ⬜ Not Started  
**Priority:** P1 (High) - Pairs with RF-ARCH-012  
**Estimated Effort:** 1-2 days

#### Problem

Current `store_knowledge()` method always creates new entries, causing duplicates. Need to support upsert behavior with deduplication.

**Pairs with:** [arch/02-MEMORY-SERVICE.md](../arch/02-MEMORY-SERVICE.md) RF-ARCH-012

#### Solution: Add external_id Parameter

```python
class MemoryClient:
    async def store_knowledge(
        self,
        content: str,
        user_id: str,
        external_id: Optional[str] = None,  # NEW
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SemanticMemoryResponse:
        """
        Store or update knowledge in semantic memory.
        
        Args:
            content: Text content to store (required)
            user_id: User identifier (required in single-tenant mode)
            external_id: Optional user-provided ID for deduplication.
                        If provided, upserts on external_id.
                        If omitted, upserts on content_hash (automatic deduplication).
            metadata: Optional metadata dict (tags, source, version, etc.)
        
        Returns:
            SemanticMemoryResponse with id, content, embedding vector
        
        Behavior:
            - With external_id: Upserts on (tenant_id, user_id, external_id)
            - Without external_id: Upserts on (tenant_id, user_id, content_hash)
            - Updates existing entry if constraint matches
            - Creates new entry if no match found
        
        Examples:
            # Explicit deduplication by ID
            await memory.store_knowledge(
                content="Docker is a container platform",
                user_id="user-123",
                external_id="doc-docker-intro",
                metadata={"source": "docs.docker.com", "version": "v2"}
            )
            
            # Automatic deduplication by content hash
            await memory.store_knowledge(
                content="Python was created by Guido van Rossum",
                user_id="user-123"
            )
        """
```

#### Implementation Details

**Request Body:**
```python
# New field in SemanticMemoryCreate DTO (soorma-common)
@dataclass
class SemanticMemoryCreate:
    content: str
    external_id: Optional[str] = None  # NEW
    metadata: Dict[str, Any] = field(default_factory=dict)
```

**HTTP Call:**
```python
response = await self._client.post(
    f"{self.base_url}/v1/memory/semantic",
    json={
        "content": content,
        "external_id": external_id,  # NEW
        "metadata": metadata or {},
    },
    params={"user_id": user_id},
)
```

#### Testing

```python
async def test_store_knowledge_with_external_id():
    """Should upsert on external_id."""
    # First store
    result1 = await memory.store_knowledge(
        content="Docker v1",
        user_id="user-1",
        external_id="doc-docker"
    )
    
    # Update same document
    result2 = await memory.store_knowledge(
        content="Docker v2",
        user_id="user-1",
        external_id="doc-docker"
    )
    
    # Should have same ID (upsert)
    assert result1.id == result2.id

async def test_store_knowledge_auto_dedupe():
    """Should upsert on content_hash when no external_id."""
    content = "Python was created by Guido"
    
    # First store
    result1 = await memory.store_knowledge(
        content=content,
        user_id="user-1"
    )
    
    # Store same content again
    result2 = await memory.store_knowledge(
        content=content,
        user_id="user-1"
    )
    
    # Should have same ID (auto-dedupe)
    assert result1.id == result2.id
```

---

### RF-SDK-020: Working Memory Deletion SDK

**Status:** ⬜ Not Started  
**Priority:** P2 (Medium) - Pairs with RF-ARCH-013  
**Estimated Effort:** 1 day

#### Problem

No SDK methods to delete working memory state, causing data accumulation.

**Pairs with:** [arch/02-MEMORY-SERVICE.md](../arch/02-MEMORY-SERVICE.md) RF-ARCH-013

#### Solution: Add Delete Methods

```python
class MemoryClient:
    async def delete_plan_state(
        self,
        plan_id: str,
        key: str,
    ) -> bool:
        """
        Delete a specific key from plan state.
        
        Args:
            plan_id: Plan identifier
            key: State key to delete
        
        Returns:
            True if deleted, False if key didn't exist
        
        Example:
            await memory.delete_plan_state(
                plan_id="plan-123",
                key="research_data"
            )
        """
        try:
            response = await self._client.delete(
                f"{self.base_url}/v1/memory/working/{plan_id}/{key}",
            )
            response.raise_for_status()
            return True
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return False
            raise
    
    async def delete_plan(
        self,
        plan_id: str,
    ) -> int:
        """
        Delete all state for a plan.
        
        Args:
            plan_id: Plan identifier
        
        Returns:
            Number of keys deleted
        
        Example:
            count = await memory.delete_plan(plan_id="plan-123")
            print(f"Deleted {count} keys")
        """
        response = await self._client.delete(
            f"{self.base_url}/v1/memory/working/{plan_id}",
        )
        response.raise_for_status()
        result = response.json()
        return result["deleted_count"]
```

#### WorkflowState Helper Updates

```python
class WorkflowState:
    async def delete(self, key: str) -> bool:
        """
        Delete a key from plan state.
        
        Returns:
            True if deleted, False if key didn't exist
        
        Example:
            state = WorkflowState(context.memory, plan_id)
            deleted = await state.delete("temp_data")
        """
        return await self.context.memory.delete_plan_state(
            plan_id=self.plan_id,
            key=key
        )
    
    async def cleanup(self) -> int:
        """
        Delete all state for this plan.
        
        Returns:
            Number of keys deleted
        
        Example:
            state = WorkflowState(context.memory, plan_id)
            await state.set("status", "completed")
            count = await state.cleanup()  # Delete all keys
        """
        return await self.context.memory.delete_plan(self.plan_id)
```

#### Usage Patterns

```python
# Pattern 1: Explicit cleanup on completion
@planner.on_goal("research.goal")
async def handle_goal(goal, ctx):
    state = WorkflowState(ctx.memory, plan_id)
    
    # Execute plan...
    
    # Mark as completed
    await state.set("status", "completed")
    
    # Cleanup all state
    await state.cleanup()

# Pattern 2: Delete temporary keys
@worker.on_task("process.data")
async def handle_task(task, ctx):
    state = WorkflowState(ctx.memory, task.plan_id)
    
    # Store temporary data
    await state.set("temp_results", data)
    
    # Process...
    
    # Delete temporary data
    await state.delete("temp_results")

# Pattern 3: Background cleanup job
async def cleanup_old_plans():
    """Cleanup completed plans older than 7 days."""
    plans = await memory.list_plans(
        status="completed",
        older_than="7d"
    )
    
    for plan in plans:
        count = await memory.delete_plan(plan["plan_id"])
        print(f"Cleaned up {count} keys for {plan['plan_id']}")
```

#### Testing

```python
async def test_delete_plan_state():
    """Should delete individual key."""
    # Store key
    await memory.set_plan_state(
        plan_id="plan-1",
        key="data",
        value={"test": "value"}
    )
    
    # Delete key
    deleted = await memory.delete_plan_state(
        plan_id="plan-1",
        key="data"
    )
    assert deleted is True
    
    # Verify deleted
    with pytest.raises(Exception):  # 404
        await memory.get_plan_state("plan-1", "data")

async def test_delete_plan():
    """Should delete all keys for plan."""
    # Store multiple keys
    await memory.set_plan_state("plan-1", "key1", {"a": 1})
    await memory.set_plan_state("plan-1", "key2", {"b": 2})
    await memory.set_plan_state("plan-1", "key3", {"c": 3})
    
    # Delete all
    count = await memory.delete_plan("plan-1")
    assert count == 3

async def test_workflow_state_cleanup():
    """WorkflowState.cleanup() should delete all keys."""
    state = WorkflowState(memory, "plan-1")
    
    # Store data
    await state.set("goal", "test")
    await state.set("status", "running")
    await state.record_action("started")
    
    # Cleanup
    count = await state.cleanup()
    assert count >= 2  # At least goal + status
```

---

### RF-SDK-021: Semantic Memory Privacy SDK

**Status:** ⬜ Not Started  
**Priority:** P1 (High) - Pairs with RF-ARCH-014  
**Estimated Effort:** 1-2 days

#### Problem

Semantic memory is tenant-scoped without user isolation. This causes:
- Privacy concerns (users see each other's agent memory)
- No control over knowledge visibility
- Doesn't match CoALA framework use case (agent memory, not shared knowledge)

**Pairs with:** [arch/02-MEMORY-SERVICE.md](../arch/02-MEMORY-SERVICE.md) RF-ARCH-014

#### Solution: User-Scoped Privacy with Optional Public Flag

Add `user_id` parameter (required) and `is_public` flag (optional, default False) to semantic memory methods.

**MemoryClient Updates:**

```python
class MemoryClient:
    async def store_knowledge(
        self,
        content: str,
        embedding: List[float],
        user_id: str,              # NEW: Required
        metadata: Optional[Dict[str, Any]] = None,
        external_id: Optional[str] = None,
        is_public: bool = False,    # NEW: Default private
        tags: Optional[List[str]] = None,
        source: Optional[str] = None,
        plan_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Store knowledge in semantic memory (private by default).
        
        Args:
            user_id: Required. User who owns this knowledge.
            is_public: If True, visible to all users in tenant.
                      If False (default), only visible to this user.
        
        Example:
            # Store private research (default)
            await memory.store_knowledge(
                content="My findings on quantum computing...",
                embedding=embedding_vector,
                user_id="alice"
            )
            
            # Store public best practices
            await memory.store_knowledge(
                content="Team's API design best practices...",
                embedding=embedding_vector,
                user_id="bob",
                is_public=True
            )
        """
        payload = {
            "content": content,
            "embedding": embedding,
            "user_id": user_id,  # Required
            "is_public": is_public,  # Default False
            "metadata": metadata or {},
            "external_id": external_id,
            "tags": tags or [],
            "source": source,
            "plan_id": plan_id,
            "session_id": session_id,
        }
        
        response = await self._client.post(
            f"{self.base_url}/v1/memory/semantic",
            json=payload,
        )
        response.raise_for_status()
        return response.json()
    
    async def query_knowledge(
        self,
        query_embedding: List[float],
        user_id: str,              # NEW: Required
        top_k: int = 10,
        include_public: bool = True, # NEW: Include public knowledge
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query semantic memory (user's private + optional public knowledge).
        
        Args:
            user_id: Required. User performing the query.
            include_public: If True (default), includes public knowledge from all users.
                           If False, only returns user's private knowledge.
        
        Returns:
            List of knowledge entries matching query, with user_id and is_public fields.
        
        Example:
            # Query includes Alice's private + team's public
            results = await memory.query_knowledge(
                query_embedding=embedding,
                user_id="alice",
                include_public=True
            )
            
            # Query only Alice's private knowledge
            private_only = await memory.query_knowledge(
                query_embedding=embedding,
                user_id="alice",
                include_public=False
            )
        """
        payload = {
            "query_embedding": query_embedding,
            "user_id": user_id,
            "include_public": include_public,
            "top_k": top_k,
            "filters": filters or {},
        }
        
        response = await self._client.post(
            f"{self.base_url}/v1/memory/semantic/query",
            json=payload,
        )
        response.raise_for_status()
        return response.json()
```

#### WorkflowState Helper Updates

```python
class WorkflowState:
    async def store_knowledge(
        self,
        user_id: str,
        content: str,
        embedding: List[float],
        external_id: Optional[str] = None,
        is_public: bool = False,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Store knowledge for this workflow (as part of plan context).
        
        Args:
            user_id: User who owns this knowledge
            is_public: If True, visible to all users in tenant
        
        Example:
            state = WorkflowState(context.memory, plan_id)
            await state.store_knowledge(
                user_id="alice",
                content="Research findings...",
                embedding=embedding,
                is_public=False  # Private to Alice
            )
        """
        return await self.context.memory.store_knowledge(
            content=content,
            embedding=embedding,
            user_id=user_id,
            external_id=external_id,
            is_public=is_public,
            tags=tags,
            plan_id=self.plan_id
        )
    
    async def query_knowledge(
        self,
        user_id: str,
        query_embedding: List[float],
        include_public: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Query knowledge for this workflow (user's private + optional public).
        
        Example:
            state = WorkflowState(context.memory, plan_id)
            results = await state.query_knowledge(
                user_id="alice",
                query_embedding=embedding,
                include_public=True  # Include team knowledge
            )
        """
        return await self.context.memory.query_knowledge(
            query_embedding=query_embedding,
            user_id=user_id,
            include_public=include_public,
        )
```

#### Usage Patterns

```python
# Pattern 1: Private user research
@worker.on_task("research.requested")
async def research(task, ctx):
    state = WorkflowState(ctx.memory, task.plan_id)
    
    # Store research findings (private to user)
    await state.store_knowledge(
        user_id=task.user_id,
        content=f"Research on {task.query}...",
        embedding=embedding,
        is_public=False  # Default, private to user
    )

# Pattern 2: Shared team knowledge
@worker.on_task("share.knowledge")
async def share(task, ctx):
    state = WorkflowState(ctx.memory, task.plan_id)
    
    # Store as public (shared with team)
    await state.store_knowledge(
        user_id=task.creator_id,
        content="Best practice: ...",
        embedding=embedding,
        is_public=True  # Visible to all team members
    )

# Pattern 3: Query includes private + public
@planner.on_goal("research.goal")
async def plan(goal, ctx):
    state = WorkflowState(ctx.memory, plan_id)
    
    # Query includes user's private + team's public knowledge
    relevant_knowledge = await state.query_knowledge(
        user_id=goal.user_id,
        query_embedding=goal_embedding,
        include_public=True  # Defaults to True
    )
    
    # Process knowledge...
```

#### Testing

```python
async def test_store_knowledge_private():
    """Should store private knowledge by default."""
    result = await memory.store_knowledge(
        content="Private research...",
        embedding=[...],
        user_id="alice"
    )
    assert result["is_public"] is False
    assert result["user_id"] == "alice"

async def test_store_knowledge_public():
    """Should store public knowledge when flag set."""
    result = await memory.store_knowledge(
        content="Shared best practices...",
        embedding=[...],
        user_id="bob",
        is_public=True
    )
    assert result["is_public"] is True

async def test_query_private_only():
    """Should query only user's private knowledge."""
    # Store Alice's private knowledge
    await memory.store_knowledge(
        content="Alice's private",
        embedding=[...],
        user_id="alice",
        is_public=False
    )
    
    # Store Bob's private knowledge
    await memory.store_knowledge(
        content="Bob's private",
        embedding=[...],
        user_id="bob",
        is_public=False
    )
    
    # Alice queries with include_public=False
    results = await memory.query_knowledge(
        query_embedding=[...],
        user_id="alice",
        include_public=False
    )
    
    # Should only get Alice's private knowledge
    assert len(results) == 1
    assert results[0]["user_id"] == "alice"

async def test_query_private_and_public():
    """Should query user's private + public knowledge."""
    # Store private knowledge
    await memory.store_knowledge(
        content="Alice's private",
        embedding=[...],
        user_id="alice",
        is_public=False
    )
    
    # Store public knowledge from Bob
    await memory.store_knowledge(
        content="Bob's public",
        embedding=[...],
        user_id="bob",
        is_public=True
    )
    
    # Alice queries with include_public=True
    results = await memory.query_knowledge(
        query_embedding=[...],
        user_id="alice",
        include_public=True
    )
    
    # Should get both Alice's private + Bob's public
    assert len(results) == 2
    user_ids = {r["user_id"] for r in results}
    assert user_ids == {"alice", "bob"}

async def test_privacy_isolation():
    """Should not expose private knowledge across users."""
    # Store Alice's private knowledge
    await memory.store_knowledge(
        content="Alice's secret research",
        embedding=[...],
        user_id="alice",
        is_public=False
    )
    
    # Bob queries with include_public=False
    results = await memory.query_knowledge(
        query_embedding=[...],
        user_id="bob",
        include_public=False
    )
    
    # Should not see Alice's private knowledge
    assert len(results) == 0

async def test_workflow_state_privacy():
    """WorkflowState should respect privacy settings."""
    state = WorkflowState(memory, "plan-1")
    
    # Store private knowledge
    await state.store_knowledge(
        user_id="alice",
        content="Research...",
        embedding=[...],
        is_public=False
    )
    
    # Query with include_public=False
    results = await state.query_knowledge(
        user_id="alice",
        query_embedding=[...],
        include_public=False
    )
    
    assert len(results) == 1
    assert results[0]["is_public"] is False
```

---

## Implementation Checklist

- [ ] **Define** Memory Service API endpoints (if not already)
- [ ] **Write tests first** for task context methods
- [ ] **Implement** `store_task_context()`, `get_task_context()`, `delete_task_context()`
- [ ] **Write tests first** for `get_task_by_subtask()`
- [ ] **Implement** `get_task_by_subtask()` (requires index on sub_task_ids)
- [ ] **Write tests first** for plan context methods
- [ ] **Implement** `store_plan_context()`, `get_plan_context()`
- [ ] **Write tests first** for session management
- [ ] **Implement** `create_plan()`, `create_session()`, `list_plans()`, `list_sessions()`
- [ ] **Write tests first** for WorkflowState helper (RF-SDK-014):
  - [ ] Test sequential operations (set, get, record_action)
  - [ ] Test fresh reads (no stale cached data)
  - [ ] Test concurrent writes (document race condition behavior)
  - [ ] Test action history append
  - [ ] Test clear() operation
- [ ] **Implement** WorkflowState class in `workflow.py`
- [ ] **Document** concurrency limitations in docstrings
- [ ] **Add integration tests** for multi-agent concurrent scenarios
- [ ] **Update** Memory Service with new endpoints

---

## Future Enhancements (Post-MVP)

### Atomic Operations for Concurrency

Add Memory Service endpoints for atomic state updates:

```python
# Atomic list append (no race condition)
POST /v1/memory/atomic/append
{
  "plan_id": "...",
  "path": "workflow_state.action_history",
  "value": "event_name"
}

# Atomic counter increment
POST /v1/memory/atomic/increment
{
  "plan_id": "...",
  "path": "workflow_state.retry_count"
}

# Optimistic locking
POST /v1/memory/plan-context
{
  "plan_id": "...",
  "context": {...},
  "expected_version": 5  # Fails if version != 5
}
```

This eliminates read-modify-write race conditions in concurrent workflows.

---

## Dependencies

- **Depends on:** Nothing (foundational)
- **Blocks:** [05-WORKER-MODEL.md](05-WORKER-MODEL.md), [06-PLANNER-MODEL.md](06-PLANNER-MODEL.md)

---

## Open Questions

None currently - design is settled.

---

## Related Documents

- [05-WORKER-MODEL.md](05-WORKER-MODEL.md) - Uses task context storage
- [06-PLANNER-MODEL.md](06-PLANNER-MODEL.md) - Uses plan context storage
