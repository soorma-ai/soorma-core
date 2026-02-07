# SDK Refactoring: Worker Model

**Document:** 05-WORKER-MODEL.md  
**Status:** ⬜ Not Started  
**Priority:** � Medium (Phase 2)  
**Last Updated:** January 11, 2026

---

## Quick Reference

| Aspect | Details |
|--------|----------|
| **Task** | RF-SDK-004: Worker Async Task Model |
| **Files** | `sdk/python/soorma/agents/worker.py` |
| **Dependencies** | 01-EVENT-SYSTEM, 02-MEMORY-SDK |
| **Blocks** | None |
| **Estimated Effort** | 2-3 days |

---

## Context

### Why This Matters

Workers handle **async choreography** - delegating to sub-agents and completing when results arrive:

1. Worker receives task, saves state to memory
2. Worker delegates to sub-agent(s)
3. Worker handler returns (does NOT return result)
4. Later: sub-agent result arrives
5. Worker restores state from memory
6. Worker completes original task

### Current State

- `_handle_action_request()` expects handler to return result synchronously
- No support for saving/restoring task context
- No delegation pattern with correlation tracking

### Key Files

```
sdk/python/soorma/
├── context.py          # PlatformContext (memory access)
└── agents/
    └── worker.py       # Worker class, on_task, on_result
```

### Prerequisite Concepts

From **01-EVENT-SYSTEM** (must complete first):
- `bus.request()` - Publish action request with `response_event`
- `bus.respond()` - Publish result to caller's `response_event`

From **02-MEMORY-SDK** (must complete first):
- `memory.store_task_context()` - Persist TaskContext
- `memory.get_task_by_subtask()` - Find parent task by correlation

---

## Summary

This document covers the async Worker task model refactoring:
- **RF-SDK-004:** Worker Async Task Model with TaskContext, delegation, and parallel fan-out/fan-in

This enables the core async choreography pattern.

---

## Tasks

### RF-SDK-004: Worker Async Task Model

**Files:** [worker.py](../../sdk/python/soorma/agents/worker.py)

#### Current Issue

`_handle_action_request()` expects handler to return result synchronously:
```python
# Current - BLOCKING
result = await handler(task, context)
await context.bus.publish("action.result", data={"result": result})
```

This breaks the async choreography pattern where workers delegate to sub-agents and complete asynchronously.

---

### RF-SDK-022: Worker Handler-Only Event Registration

**Files:** [worker.py](../../sdk/python/soorma/agents/worker.py), [base.py](../../sdk/python/soorma/agents/base.py)

#### Problem

Workers currently advertise or track events that don’t necessarily have handlers. This is unsafe for discovery and subscription semantics.

#### Target Behavior

- **Register events only when a handler exists** (`on_task`, `on_result`).
- **Do not populate `events_consumed/events_produced` from structured capabilities**.
- **Never treat topics as event types** (e.g., `action-requests`, `action-results`).

#### Acceptance Criteria

- `events_consumed` contains only task/result event types with handlers
- `events_produced` contains only response event types actually emitted
- Structured capabilities remain for discovery (registry) but do not auto-subscribe
- Unit tests assert no topic names appear in events lists

---

## Target Design

### 1. TaskContext with Persistence

```python
@dataclass
class TaskContext:
    task_id: str
    event_type: str
    plan_id: str
    data: Dict[str, Any]
    response_event: str      # ← From request envelope
    response_topic: str      # ← From request envelope
    sub_tasks: Dict[str, SubTaskInfo]  # ← Track delegated sub-tasks
    state: Dict[str, Any]    # ← Task-specific state
    
    # Authentication context (from platform context / token)
    tenant_id: str
    user_id: str
    agent_id: str
    
    async def save(self):
        """Persist task context to working memory for async completion."""
        await self._context.memory.store_task_context(
            task_id=self.task_id,
            plan_id=self.plan_id,
            context=self.to_dict(),
        )
    
    async def delegate(
        self,
        event_type: str,
        data: Dict[str, Any],
        response_event: str,
    ) -> str:
        """
        Delegate to sub-agent (sequential chaining).
        
        Uses string event_type and dict data for progressive complexity:
        - Simple agents use str + dict directly
        - Advanced agents convert EventDefinition to these arguments
        
        Returns sub_task_id for tracking.
        """
        sub_task_id = str(uuid4())
        self.sub_tasks[sub_task_id] = SubTaskInfo(
            sub_task_id=sub_task_id,
            event_type=event_type,
            response_event=response_event,
            status="pending",
        )
        await self.save()  # ← CRITICAL: Save before publish for async resume
        
        await self._context.bus.request(
            event_type=event_type,
            data=data,
            response_event=response_event,
            correlation_id=sub_task_id,
        )
        return sub_task_id
    
    async def delegate_parallel(
        self,
        sub_tasks: List[DelegationSpec],
    ) -> str:
        """
        Delegate multiple sub-tasks in parallel (fan-out).
        
        Returns parallel_group_id for tracking this fan-out group.
        """
        parallel_group_id = str(uuid4())
        
        for spec in sub_tasks:
            sub_task_id = str(uuid4())
            self.sub_tasks[sub_task_id] = SubTaskInfo(
                sub_task_id=sub_task_id,
                event_type=spec.event_type,
                response_event=spec.response_event,
                status="pending",
                parallel_group_id=parallel_group_id,
            )
        
        await self.save()  # ← Save all sub-tasks before publishing
        
        # Publish all in parallel
        for sub_task_id, info in self.sub_tasks.items():
            if info.parallel_group_id == parallel_group_id:
                spec = next(s for s in sub_tasks if s.event_type == info.event_type)
                await self._context.bus.request(
                    event_type=info.event_type,
                    data=spec.data,
                    response_event=info.response_event,
                    correlation_id=sub_task_id,
                )
        
        return parallel_group_id
    
    def aggregate_parallel_results(self, parallel_group_id: str) -> Optional[Dict[str, Any]]:
        """Check if all sub-tasks in a parallel group completed and aggregate results."""
        group_tasks = [
            info for info in self.sub_tasks.values()
            if info.parallel_group_id == parallel_group_id
        ]
        
        if all(t.status == "completed" for t in group_tasks):
            return {t.sub_task_id: t.result for t in group_tasks}
        return None
    
    def update_sub_task_result(self, sub_task_id: str, result: Dict[str, Any]):
        """Update a sub-task with its result (called from on_result handler)."""
        if sub_task_id in self.sub_tasks:
            self.sub_tasks[sub_task_id].status = "completed"
            self.sub_tasks[sub_task_id].result = result
    
    def is_complete(self) -> bool:
        """Check if all sub-tasks have completed."""
        return all(info.status == "completed" for info in self.sub_tasks.values())
    
    async def complete(self, result: Dict[str, Any]):
        """Complete the task and publish result."""
        await self._context.bus.respond(
            event_type=self.response_event,
            data={
                "task_id": self.task_id,
                "status": "completed",
                "result": result,
            },
            correlation_id=self.task_id,
            topic=self.response_topic,
        )
        # Cleanup task context
        await self._context.memory.delete_task_context(self.task_id)


@dataclass
class SubTaskInfo:
    """Tracking info for a delegated sub-task."""
    sub_task_id: str
    event_type: str
    response_event: str
    status: str  # pending, completed, failed
    parallel_group_id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


@dataclass  
class DelegationSpec:
    """Specification for a parallel delegation."""
    event_type: str
    data: Dict[str, Any]
    response_event: str
```

### 2. ResultContext for Restoring Task

```python
@dataclass
class ResultContext:
    """Context for handling sub-task results."""
    event_type: str
    correlation_id: str  # sub_task_id
    data: Dict[str, Any]
    success: bool
    error: Optional[str]
    
    async def restore_task(self) -> TaskContext:
        """
        Restore the parent task context from memory.
        Uses correlation_id (sub_task_id) to find the parent task.
        """
        task_data = await self._context.memory.get_task_by_subtask(
            self.correlation_id
        )
        return TaskContext.from_dict(task_data, self._context)
```

### 3. Worker Decorators

```python
class Worker(Agent):
    def on_task(self, event_type: str):
        """Register handler for incoming tasks (action-requests)."""
        def decorator(func):
            @self.on_event(topic="action-requests", event_type=event_type)
            async def wrapper(event, context):
                task = TaskContext.from_event(event, context)
                await func(task, context)
                # NOTE: No automatic result publishing - handler manages completion
            return func
        return decorator
    
    def on_result(self, event_type: str):
        """Register handler for sub-task results (action-results)."""
        def decorator(func):
            @self.on_event(topic="action-results", event_type=event_type)
            async def wrapper(event, context):
                result = ResultContext.from_event(event, context)
                await func(result, context)
            return func
        return decorator
```

---

## Usage Examples

### Sequential Delegation
```python
@worker.on_task(event_type="research.requested")
async def handle_research(task: TaskContext, context: PlatformContext):
    # Save task context for async completion
    await task.save()
    
    # Delegate to sub-agent
    await task.delegate(
        event_type="web.search.requested",
        data={"query": task.data["topic"]},
        response_event="web.search.completed",
    )
    # Handler returns - async completion via on_result

@worker.on_result(event_type="web.search.completed")
async def handle_search_result(result: ResultContext, context: PlatformContext):
    task = await result.restore_task()
    
    if task.is_complete():
        await task.complete(result={"findings": result.data})
    else:
        await task.delegate(...)  # Chain to next sub-task
```

### Parallel Fan-out / Fan-in
```python
@worker.on_task(event_type="analyze.requested")
async def handle_analyze(task: TaskContext, context: PlatformContext):
    # Fan-out: Delegate to multiple workers in parallel
    group_id = await task.delegate_parallel([
        DelegationSpec("sentiment.analyze", {"text": task.data["text"]}, "sentiment.completed"),
        DelegationSpec("entity.extract", {"text": task.data["text"]}, "entity.completed"),
        DelegationSpec("topic.classify", {"text": task.data["text"]}, "topic.completed"),
    ])
    
    task.state["pending_group"] = group_id
    await task.save()

@worker.on_result(event_type="sentiment.completed")
@worker.on_result(event_type="entity.completed")
@worker.on_result(event_type="topic.classify")
async def handle_analysis_result(result: ResultContext, context: PlatformContext):
    task = await result.restore_task()
    
    # Update sub-task result
    task.update_sub_task_result(result.correlation_id, result.data)
    
    # Check if all parallel tasks completed (fan-in)
    group_id = task.state.get("pending_group")
    aggregated = task.aggregate_parallel_results(group_id)
    
    if aggregated:
        await task.complete(result={
            "sentiment": aggregated[...]["result"],
            "entities": aggregated[...]["result"],
            "topics": aggregated[...]["result"],
        })
    else:
        await task.save()  # Still waiting for other sub-tasks
```

---

## Tests to Add

```python
# test/test_worker.py

async def test_task_context_save_restore():
    """TaskContext should persist to memory and restore correctly."""
    task = TaskContext(task_id="t1", ...)
    await task.save()
    
    restored = await TaskContext.restore("t1", context)
    assert restored.task_id == "t1"

async def test_worker_delegates_to_sub_agent():
    """Worker should be able to delegate to sub-agent."""
    @worker.on_task(event_type="parent.task")
    async def handler(task, ctx):
        await task.delegate(
            event_type="sub.task",
            data={"key": "value"},
            response_event="sub.done",
        )
    
    # Verify action-request published with correct response_event

async def test_worker_completes_after_sub_task_result():
    """Worker should complete task when sub-task returns."""
    pass

async def test_worker_chains_multiple_sub_tasks():
    """Worker should support chaining multiple sequential sub-tasks."""
    pass

async def test_worker_parallel_fan_out():
    """Worker should support parallel delegation."""
    pass

async def test_worker_parallel_fan_in():
    """Worker should aggregate parallel results."""
    pass
```

---

## Implementation Checklist

- [ ] **Read existing code** in `worker.py`
- [ ] **Write tests first** for TaskContext persistence
- [ ] **Implement** `TaskContext` dataclass with `save()`, `delegate()`, `complete()`
- [ ] **Write tests first** for parallel delegation
- [ ] **Implement** `delegate_parallel()` and `aggregate_parallel_results()`
- [ ] **Write tests first** for ResultContext
- [ ] **Implement** `ResultContext` with `restore_task()`
- [ ] **Update** Worker class with new `on_task()` and `on_result()` decorators
- [ ] **Update examples** to use new async pattern

---

## Dependencies

- **Depends on:** [01-EVENT-SYSTEM.md](01-EVENT-SYSTEM.md) (RF-SDK-001, RF-SDK-002, RF-SDK-003)
- **Depends on:** [02-MEMORY-SDK.md](02-MEMORY-SDK.md) (memory.store_task_context, etc.)
- **Blocks:** None

---

## Open Questions

None currently - design is settled.

---

## Related Documents

- [00-OVERVIEW.md](00-OVERVIEW.md) - Agent progression model
- [01-EVENT-SYSTEM.md](01-EVENT-SYSTEM.md) - Event publishing (dependency)
- [02-MEMORY-SDK.md](02-MEMORY-SDK.md) - Memory client (dependency)
- [04-TOOL-MODEL.md](04-TOOL-MODEL.md) - Simpler sync pattern (comparison)
