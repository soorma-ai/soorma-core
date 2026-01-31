# Stage 3 Working Plan - Agent Models: Tool & Worker

**Status:** 📋 Planning Phase  
**Created:** January 30, 2026  
**Updated:** January 30, 2026 - Initial Planning Document

---

## Overview

Stage 3 implements the two core agent models for synchronous and asynchronous task handling:

1. **Tool Model (RF-SDK-005)** - Synchronous request/response pattern for stateless operations
2. **Worker Model (RF-SDK-004)** - Asynchronous task handling with state persistence and delegation

**Total Estimated Effort:** 3-5 days

**Key Design Principles:**
- Tools are stateless, synchronous, auto-complete
- Workers are stateful, asynchronous, manual completion
- Both use `action-requests` and `action-results` topics (standard)
- Response event is caller-specified (no hardcoded topic inference)
- Worker can delegate to other agents and track sub-tasks
- Memory SDK provides persistent storage for async task completion

**Dependencies:** 
- ✅ Stage 1: Event System (response_event, correlation tracking)
- ✅ Stage 2: Memory SDK (save/restore TaskContext)
- ✅ Stage 2.1: Common DTOs

---

## Reference Design Documents

Before implementing, review these documents:

| Task | Design Document | Location |
|------|-----------------|----------|
| **Tool Model** | [04-TOOL-MODEL.md](sdk/04-TOOL-MODEL.md) | SDK refactoring docs |
| **Worker Model** | [05-WORKER-MODEL.md](sdk/05-WORKER-MODEL.md) | SDK refactoring docs |

**Implementation Workflow:**
1. Read the design document for your current task
2. Write tests first (TDD) that define expected behavior
3. Implement code to pass tests
4. Tests validate design document requirements exactly

---

## Preliminary Task List (For Review)

Below is the proposed breakdown for Stage 3. **Please review, add notes, and suggest changes before we proceed with implementation.**

### Phase 1: Tool Model Refactoring (RF-SDK-005)

**Priority:** Medium  
**Estimated:** 1-2 days  
**Files Affected:** `sdk/python/soorma/agents/tool.py`

#### Task 1.1: Review Design & Dependencies
- [ ] Read [04-TOOL-MODEL.md](sdk/04-TOOL-MODEL.md) completely
- [ ] Review Stage 1 event system changes (response_event handling)
- [ ] Understand InvocationContext model
- [ ] Understand schema ownership pattern (response_event via request)
- [ ] Confirm topic migration: `tool.request` → `action-requests`

#### Task 1.2: Define InvocationContext Type
- [ ] Create lightweight context class for tool invocations
- [ ] Include request_id, event_type, correlation_id, data
- [ ] Include response_event (caller-specified)
- [ ] Include response_topic (default: "action-results")
- [ ] Include auth context: tenant_id, user_id
- [ ] Create from_event() factory method

**Questions to Review:**
- Q1: Should InvocationContext be in a new file or alongside Tool class?
- Q2: Should we validate that response_event is present in invocation request?

#### Task 1.3: Write Tool Tests (TDD)
**File:** `sdk/python/tests/agents/test_tool.py`

**Test scenarios to define:**
```python
# Basic invocation
test_tool_on_invoke_receives_request()
test_tool_handler_receives_invocation_context()

# Response publishing
test_tool_decorator_auto_publishes_to_response_event()
test_tool_publishes_to_response_topic()

# Correlation tracking
test_tool_preserves_correlation_id_in_response()
test_tool_includes_parent_event_id_in_response()

# Error handling
test_tool_handler_exception_publishes_error()

# Multiple handlers
test_tool_multiple_on_invoke_handlers()
```

**Questions to Review:**
- Q3: Should Tool support multiple on_invoke() handlers for different event types?
- Q4: Should we have a test for Tool discovery (registry registration)?

#### Task 1.4: Refactor Tool Class
**File:** `sdk/python/soorma/agents/tool.py`

**Changes needed:**
- [ ] Remove custom `tool.request` / `tool.response` topics
- [ ] Add `on_invoke(event_type: str)` decorator
- [ ] Default topic: `action-requests`
- [ ] Handler model: synchronous, returns result
- [ ] Auto-publish result to caller's response_event
- [ ] Extract request_id if not present

**Questions to Review:**
- Q5: Should Tool.on_invoke() require event_type parameter (vs optional)?
- Q6: Should we add validation that handler return type matches schema?

#### Task 1.5: Update Examples
**Files:**
- `examples/01-hello-world/tool.py` (or new example)
- Update README with tool pattern

**Changes needed:**
- [ ] Create simple calculator tool example
- [ ] Show on_invoke() decorator usage
- [ ] Show stateless handler returning result
- [ ] Document topic usage
- [ ] Verify example works with `soorma dev`

---

### Phase 2: Worker Model Refactoring (RF-SDK-004)

**Priority:** Medium  
**Estimated:** 2-3 days  
**Files Affected:** `sdk/python/soorma/agents/worker.py`, `sdk/python/soorma/models/task.py`

#### Task 2.1: Review Design & Dependencies
- [ ] Read [05-WORKER-MODEL.md](sdk/05-WORKER-MODEL.md) completely
- [ ] Review Task vs Worker semantics
- [ ] Understand TaskContext data structure
- [ ] Understand save/restore pattern with Memory SDK
- [ ] Understand delegation with correlation tracking
- [ ] Review on_task() and on_result() decorator pattern

#### Task 2.2: Define TaskContext Model
**File:** `sdk/python/soorma/models/task.py` (new or existing)

**Data structure needed:**
```python
@dataclass
class TaskContext:
    task_id: str
    event_type: str
    plan_id: str
    data: Dict[str, Any]
    response_event: str
    response_topic: str
    sub_tasks: Dict[str, SubTaskInfo]  # Track delegations
    state: Dict[str, Any]  # Task-specific state
    
    # Auth context
    tenant_id: str
    user_id: str
    agent_id: str
    
    # Methods
    async def save()
    async def restore()
    async def delegate()
    async def complete()
```

**Questions to Review:**
- Q7: Should TaskContext be a dataclass or Pydantic model? (Recommend dataclass for simplicity)
- Q8: Should sub_tasks be auto-tracked or manual?
- Q9: Should state dict be nested or flat?

#### Task 2.3: Write TaskContext Tests (TDD)
**File:** `sdk/python/tests/models/test_task_context.py`

**Test scenarios:**
```python
# Persistence
test_task_context_save_to_memory()
test_task_context_restore_from_memory()

# Delegation
test_task_context_delegate_publishes_request()
test_task_context_tracks_sub_task_id()
test_task_context_saves_before_delegate()

# State management
test_task_context_set_state()
test_task_context_get_state()

# Completion
test_task_context_complete_publishes_result()
test_task_context_complete_clears_state()
```

**Questions to Review:**
- Q10: Should restore() be a class method or instance method?
- Q11: Should sub-task tracking be automatic or manual in delegate()?

#### Task 2.4: Write Worker Tests (TDD)
**File:** `sdk/python/tests/agents/test_worker.py`

**Test scenarios:**
```python
# Task reception
test_worker_on_task_receives_request()
test_worker_receives_task_context()

# Async completion
test_worker_on_task_does_NOT_auto_complete()
test_worker_on_result_restores_task_context()

# Delegation
test_worker_can_delegate_to_sub_agent()
test_worker_tracks_delegations()
test_worker_waits_for_all_results()

# State persistence
test_worker_saves_task_state_before_delegating()
test_worker_restores_state_on_result()

# Error handling
test_worker_handles_failed_sub_task()
test_worker_timeout_on_delayed_result()

# Multiple results
test_worker_fan_out_multiple_delegations()
test_worker_fan_in_collects_all_results()
```

**Questions to Review:**
- Q12: Should Worker support timeout for async completion?
- Q13: Should we have explicit circuit breaker for infinite delegation loops?
- Q14: Should Worker support parallel delegation (fan-out) or just sequential?

#### Task 2.5: Define Worker Decorators
- [ ] `on_task(event_type: str)` - Receive task requests
- [ ] `on_result(event_type: str)` - Receive result from sub-agent

**Implementation notes:**
- Task handler is async, does NOT return result
- Result handler is async, restores task context and completes
- Decorators auto-route based on event_type

**Questions to Review:**
- Q15: Should on_task() auto-subscribe to `action-requests` topic?
- Q16: Should on_result() auto-subscribe to `action-results` topic?

#### Task 2.6: Refactor Worker Class
**File:** `sdk/python/soorma/agents/worker.py`

**Changes needed:**
- [ ] Remove synchronous handler assumption
- [ ] Add `on_task()` and `on_result()` decorators
- [ ] Integrate TaskContext model
- [ ] Support delegation with `task.delegate()`
- [ ] Support async completion with `task.complete()`
- [ ] Auto-publish result on task.complete()
- [ ] Restore context on result reception

**Questions to Review:**
- Q17: Should Worker have a max action counter to prevent infinite loops?
- Q18: Should we auto-validate that handler is async?

#### Task 2.7: Update Examples
**Files:**
- `examples/05-memory-working/worker.py` (update or new)
- Create research advisor v2 using new Worker pattern
- Update README with worker pattern

**Changes needed:**
- [ ] Show on_task() and on_result() decorators
- [ ] Show task.save() / task.restore() pattern
- [ ] Show task.delegate() for sub-agent calls
- [ ] Show task.complete() for explicit completion
- [ ] Show state persistence across async boundaries
- [ ] Verify example works with `soorma dev`

---

## High-Level Implementation Approach

### Step 1: Prepare & Review (Today)
- [ ] Share this working plan with team
- [ ] Gather feedback on task breakdown
- [ ] Address open questions above
- [ ] Finalize task list and acceptance criteria

### Step 2: Tool Model (Day 1-2)
- [ ] Implement Tasks 1.1 - 1.5 in order
- [ ] Run tests continuously
- [ ] Update examples
- [ ] Commit: `feat(sdk): refactor Tool model to synchronous pattern`

### Step 3: Worker Model (Day 2-4)
- [ ] Implement Tasks 2.1 - 2.7 in order
- [ ] Run tests continuously
- [ ] Update examples
- [ ] Commit: `feat(sdk): refactor Worker model with async TaskContext`

### Step 4: Integration Testing (Day 4-5)
- [ ] Test Tool ↔ Worker interaction
- [ ] Test delegation chains
- [ ] Test state persistence
- [ ] End-to-end example validation
- [ ] Commit: `test(sdk): add integration tests for Tool/Worker`

### Step 5: Documentation & Finalization (Day 5)
- [ ] Update CHANGELOG.md with 0.8.0 entries
- [ ] Update ARCHITECTURE.md with new models
- [ ] Update README with examples
- [ ] Create migration guide stub
- [ ] Commit: `docs: Stage 3 documentation and migration notes`

---

## Acceptance Criteria

### Tool Model (RF-SDK-005)
- ✅ InvocationContext class defined and tested
- ✅ on_invoke() decorator works with event_type parameter
- ✅ Handler receives InvocationContext, returns result
- ✅ Result auto-published to response_event
- ✅ Correlation IDs preserved in response
- ✅ Uses action-requests topic (not tool.request)
- ✅ Calculator example working
- ✅ All tests passing

### Worker Model (RF-SDK-004)
- ✅ TaskContext class defined with persistence methods
- ✅ on_task() decorator receives task requests
- ✅ on_result() decorator receives sub-task results
- ✅ task.save() persists to memory
- ✅ task.restore() retrieves from memory
- ✅ task.delegate() creates sub-task and publishes request
- ✅ task.complete() publishes result and cleans up state
- ✅ Sub-task tracking works (manual or auto)
- ✅ Async completion works across event boundaries
- ✅ Example working with sequential delegation
- ✅ All tests passing

### General
- ✅ No breaking changes to Stage 1 & 2 code
- ✅ All existing tests still passing
- ✅ CHANGELOG updated with entries
- ✅ Documentation updated with new patterns

---

## Open Questions Summary

| ID | Question | Options/Discussion | Status |
|----|----------|------------------|--------|
| Q1 | InvocationContext location? | New file vs alongside Tool | ⏳ Needs review |
| Q2 | Validate response_event present? | Yes/No - recommend Yes | ⏳ Needs review |
| Q3 | Multiple on_invoke() handlers? | Yes/No - recommend Yes | ⏳ Needs review |
| Q4 | Test Tool discovery? | Yes/No - recommend separate doc | ⏳ Needs review |
| Q5 | on_invoke() event_type required? | Yes/No - recommend Yes | ⏳ Needs review |
| Q6 | Validate return type? | Yes/No - recommend No (runtime only) | ⏳ Needs review |
| Q7 | TaskContext: dataclass or Pydantic? | dataclass vs Pydantic - recommend dataclass | ⏳ Needs review |
| Q8 | Sub-tasks auto-tracked? | Yes/No - recommend auto | ⏳ Needs review |
| Q9 | State dict flat or nested? | flat vs nested - recommend flat | ⏳ Needs review |
| Q10 | restore() class method? | Yes/No - recommend class method | ⏳ Needs review |
| Q11 | Sub-task tracking automatic? | Yes/No - recommend auto | ⏳ Needs review |
| Q12 | Worker timeout support? | Yes/No - recommend stage 4 (Planner) | ⏳ Needs review |
| Q13 | Circuit breaker for loops? | Yes/No - recommend stage 4 | ⏳ Needs review |
| Q14 | Parallel delegation? | Yes/No - recommend stage 4 (Planner) | ⏳ Needs review |
| Q15 | on_task() auto-subscribe? | Yes/No - recommend Yes | ⏳ Needs review |
| Q16 | on_result() auto-subscribe? | Yes/No - recommend Yes | ⏳ Needs review |
| Q17 | Max action counter? | Yes/No - recommend stage 4 | ⏳ Needs review |
| Q18 | Auto-validate async? | Yes/No - recommend Yes | ⏳ Needs review |

---

## Task Tracking Matrix

### Phase 1: Tool Model

| Task | Description | Estimated | Status | Owner | Notes |
|------|-------------|-----------|--------|-------|-------|
| 1.1 | Review design & dependencies | 0.5d | ⏳ | TBD | |
| 1.2 | Define InvocationContext | 0.5d | ⏳ | TBD | |
| 1.3 | Write Tool tests (TDD) | 0.5d | ⏳ | TBD | |
| 1.4 | Refactor Tool class | 0.5d | ⏳ | TBD | |
| 1.5 | Update examples | 0.5d | ⏳ | TBD | |
| **Phase 1 Total** | | **2.5d** | | | |

### Phase 2: Worker Model

| Task | Description | Estimated | Status | Owner | Notes |
|------|-------------|-----------|--------|-------|-------|
| 2.1 | Review design & dependencies | 0.5d | ⏳ | TBD | |
| 2.2 | Define TaskContext model | 0.5d | ⏳ | TBD | |
| 2.3 | Write TaskContext tests | 0.5d | ⏳ | TBD | |
| 2.4 | Write Worker tests (TDD) | 1d | ⏳ | TBD | |
| 2.5 | Define Worker decorators | 0.5d | ⏳ | TBD | |
| 2.6 | Refactor Worker class | 1d | ⏳ | TBD | |
| 2.7 | Update examples | 1d | ⏳ | TBD | |
| **Phase 2 Total** | | **5d** | | | |

### Integration & Documentation

| Task | Description | Estimated | Status | Owner | Notes |
|------|-------------|-----------|--------|-------|-------|
| 3.1 | Integration testing | 1d | ⏳ | TBD | Tool ↔ Worker, delegation chains |
| 3.2 | Documentation updates | 0.5d | ⏳ | TBD | ARCHITECTURE.md, README, migration |
| **Other Total** | | **1.5d** | | | |

**Grand Total: 9 days** (breakdown: 2.5d Tool, 5d Worker, 1.5d integration)

---

## Success Metrics

### Code Quality
- [ ] 100% test coverage for new models
- [ ] All tests passing on first run
- [ ] No linting errors (ruff check)
- [ ] Type hints on all functions

### Examples
- [ ] Calculator tool works with `soorma dev`
- [ ] Research worker example works end-to-end
- [ ] Both examples have clear README documentation
- [ ] Examples work without external API keys

### Documentation
- [ ] Migration guide from old pattern drafted
- [ ] Design patterns documented
- [ ] README updated with tool/worker patterns
- [ ] CHANGELOG.md updated for 0.8.0

### Testing
- [ ] All new code tested (TDD approach)
- [ ] Integration tests verify Tool ↔ Worker
- [ ] No regression in existing tests
- [ ] Example code runs without errors

---

## Next Actions

**Ready to proceed?**

1. ✅ **Review Questions** - Please address Q1-Q18 above
2. ✅ **Add/Update Tasks** - Any tasks to add, remove, or modify?
3. ✅ **Assign Owners** - Who will own each phase?
4. ✅ **Set Timeline** - Adjust estimates as needed
5. ✅ **Finalize Plan** - Once approved, we start implementation

**Once approved, the team will:**
- Create STAGE_3_IN_PROGRESS.md to track daily execution
- Update manage_todo_list with detailed tasks
- Begin TDD implementation starting with Phase 1

---

## Related Documentation

- [README.md](README.md) - Refactoring index and stage overview
- [sdk/04-TOOL-MODEL.md](sdk/04-TOOL-MODEL.md) - Detailed tool design
- [sdk/05-WORKER-MODEL.md](sdk/05-WORKER-MODEL.md) - Detailed worker design
- [AGENT.md](../AGENT.md) - Development instructions
- [STAGE_2.1_WORKING_PLAN.md](STAGE_2.1_WORKING_PLAN.md) - Reference template
