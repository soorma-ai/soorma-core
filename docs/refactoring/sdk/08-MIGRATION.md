# SDK Refactoring: Migration Guide

**Document:** 08-MIGRATION.md  
**Status:** ⬜ Reference Document  
**Priority:** 📚 Reference  
**Last Updated:** January 11, 2026

---

## Summary

This document covers breaking changes and migration guidance for the SDK refactoring. Since the project is **pre-launch**, we don't need backwards compatibility, but this guide helps existing example code and tests migrate.

---

## Breaking Changes

### 1. Topic Required in publish()

```python
# BEFORE (deprecated)
await context.bus.publish("order.created", data={...})

# AFTER (explicit topic)
await context.bus.publish(
    topic="business-facts",
    event_type="order.created",
    data={...}
)

# AFTER (convenience method)
await context.bus.announce("order.created", data={...})
```

**Migration:** Search for `bus.publish(` with single string argument and add topic.

---

### 2. on_event() Requires Topic

```python
# BEFORE (deprecated)
@agent.on_event("order.created")

# AFTER (explicit topic and event)
@agent.on_event(topic="business-facts", event_type="order.created")
```

**Migration:** Search for `@agent.on_event(` and add topic parameter.

---

### 3. Worker Handlers Don't Return Result

```python
# BEFORE (auto-publish on return)
@worker.on_task("process")
async def handle(task, ctx):
    return {"result": "done"}  # ← SDK published automatically

# AFTER (explicit completion)
@worker.on_task("process")
async def handle(task: TaskContext, ctx):
    # ... do work, potentially delegate ...
    await task.complete({"result": "done"})  # ← Explicit completion
```

**Migration:** 
1. Change return statements to `await task.complete(result)`
2. Update handler signature to receive `TaskContext`
3. For async delegation patterns, use `task.save()` and `on_result()` handler

---

### 4. Tool/Worker Events Unified on Standard Topics

```python
# BEFORE (custom topics)
# tool.request topic
# tool.response topic

# AFTER (standard topics)
# action-requests topic
# action-results topic
```

**Migration:** Update topic subscriptions and publications.

---

### 5. Use delegate() Not Direct publish() for Sub-Tasks

```python
# BEFORE (problematic - no memory persistence)
await context.bus.publish(
    topic="action-requests",
    event_type="sub.task",
    ...
)

# AFTER (correct - saves task context first)
await task.delegate(
    event_type="sub.task",
    data={...},
    response_event="sub.task.done",
)
```

**Migration:** Replace direct publish calls for sub-tasks with `task.delegate()`.

---

### 6. response_event Required for Action Requests

```python
# BEFORE (response event derived from request)
await context.bus.request("calculate.requested", data={...})

# AFTER (explicit response_event)
await context.bus.request(
    event_type="calculate.requested",
    data={...},
    response_event="calculate.completed",
)
```

**Migration:** Add `response_event` parameter to all request calls.

---

### 7. Tracker Write Methods Removed

```python
# BEFORE (direct API calls)
await context.tracker.emit_progress(task_id, 0.5)
await context.tracker.complete_task(task_id, result)

# AFTER (event publishing)
await context.bus.publish(
    topic="system-events",
    event_type="task.progress",
    data={"task_id": task_id, "progress": 0.5},
)
```

**Migration:** Replace tracker write calls with event publishing.

---

## Migration Checklist

### Phase 1: Event System (Required First)

- [ ] Update all `bus.publish()` calls to include topic
- [ ] Update all `@agent.on_event()` decorators to include topic
- [ ] Update all `bus.request()` calls to include `response_event`

### Phase 2: Worker Migration

- [ ] Change Worker handlers to not return result
- [ ] Add explicit `task.complete()` calls
- [ ] For async patterns, add `task.save()` and `on_result()` handlers
- [ ] Replace direct publish with `task.delegate()` for sub-tasks

### Phase 3: Tool Migration

- [ ] Update Tool topic from `tool.request`/`tool.response` to `action-requests`/`action-results`
- [ ] Verify `on_invoke()` decorator auto-publishes correctly

### Phase 4: Planner Migration

- [ ] Update Planner to use new `PlanContext` with state machine
- [ ] Add explicit `response_event` to goal handling
- [ ] Update `finalize()` calls to use explicit response event

### Phase 5: Tracker Migration

- [ ] Remove `tracker.emit_progress()` calls
- [ ] Remove `tracker.complete_task()` calls
- [ ] Add corresponding event publishing

---

## SDK Progression Summary

### Event Complexity Progression

| Level | Events | Agent Registration |
|-------|--------|-------------------|
| **Simple** | String event names, hardcoded | `events_consumed=["order.placed"]` |
| **Structured** | `EventDefinition` with schemas | `events_consumed=[ORDER_EVENT]` |
| **Discoverable** | Events tied to capabilities | `capabilities=[OrderCapability]` |

### Agent Complexity Progression

| Level | Agent Type | Decorator | Behavior |
|-------|-----------|-----------|----------|
| **Primitive** | `Agent` | `@agent.on_event(topic, event_type)` | Raw event handling |
| **Sync Tool** | `Tool` | `@tool.on_invoke(event_type)` | Request/response, auto-publish |
| **Async Worker** | `Worker` | `@worker.on_task()` + `@worker.on_result()` | Task delegation, async completion |
| **Autonomous** | `Planner` | `@planner.on_goal()` + `@planner.on_transition()` | LLM reasoning, state machine |

---

## File Search Patterns

Use these patterns to find code that needs migration:

```bash
# Find publish calls without topic
grep -r "bus.publish(" --include="*.py" | grep -v "topic="

# Find on_event without topic
grep -r "@.*on_event(" --include="*.py" | grep -v "topic="

# Find worker handlers that return
grep -r "def handle.*task" --include="*.py" -A 20 | grep "return {"

# Find direct tracker calls
grep -r "tracker.emit_progress\|tracker.complete_task" --include="*.py"
```

---

## Validation

After migration, run these checks:

1. **No deprecated patterns:**
   ```bash
   # Should return no results
   grep -r "bus.publish("" --include="*.py"
   ```

2. **All handlers use explicit completion:**
   ```bash
   # Verify task.complete() in worker handlers
   grep -r "@worker.on_task" --include="*.py" -A 30 | grep "task.complete"
   ```

3. **Tests pass:**
   ```bash
   pytest test/
   ```

---

## References

- [00-OVERVIEW.md](00-OVERVIEW.md) - Design principles
- [01-EVENT-SYSTEM.md](01-EVENT-SYSTEM.md) - Event system changes
- [05-WORKER-MODEL.md](05-WORKER-MODEL.md) - Worker changes
- [04-TOOL-MODEL.md](04-TOOL-MODEL.md) - Tool changes
- [06-PLANNER-MODEL.md](06-PLANNER-MODEL.md) - Planner changes
