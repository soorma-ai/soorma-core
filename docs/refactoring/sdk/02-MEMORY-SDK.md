# SDK Refactoring: Memory SDK

**Document:** 02-MEMORY-SDK.md  
**Status:** ⬜ Not Started  
**Priority:** � High (Foundation)  
**Last Updated:** January 11, 2026

---

## Quick Reference

| Aspect | Details |
|--------|----------|
| **Tasks** | RF-SDK-010: Memory SDK Methods<br>RF-SDK-014: WorkflowState Helper Class |
| **Files** | `sdk/python/soorma/context.py`, Memory Service |
| **Pairs With Arch** | [arch/02-MEMORY-SERVICE.md](../arch/02-MEMORY-SERVICE.md) |
| **Dependencies** | None (foundational) |
| **Blocks** | 05-WORKER-MODEL, 06-PLANNER-MODEL |
| **Estimated Effort** | 1-2 days |

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
| `POST /v1/memory/task-context` | `memory.store_task_context()` | NEW |
| `GET /v1/memory/task-context/{id}` | `memory.get_task_context()` | NEW |
| `DELETE /v1/memory/task-context/{id}` | `memory.delete_task_context()` | NEW |
| `GET /v1/memory/task-context/by-subtask/{id}` | `memory.get_task_by_subtask()` | NEW |
| `POST /v1/memory/plan-context` | `memory.store_plan_context()` | NEW |
| `GET /v1/memory/plan-context/{id}` | `memory.get_plan_context()` | NEW |
| `POST /v1/memory/plans` | `memory.create_plan()` | NEW |
| `GET /v1/memory/plans` | `memory.list_plans()` | NEW |
| `POST /v1/memory/sessions` | `memory.create_session()` | NEW |
| `GET /v1/memory/sessions` | `memory.list_sessions()` | NEW |
| `POST /v1/working-memory/{plan_id}` | `memory.store()` | Existing |
| `GET /v1/working-memory/{plan_id}/{key}` | `memory.retrieve()` | Existing |

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
