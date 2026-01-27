# Soorma Core Refactoring Index

**Status:** 📋 Active Planning  
**Last Updated:** January 21, 2026

---

## Overview

This directory contains planning documents for the pre-launch refactoring of Soorma Core. These documents capture architectural decisions, SDK design changes, and implementation plans.

**Guiding Principles:**
1. **Right architecture over backwards compatibility** - Pre-launch, breaking changes are OK
2. **Tests first (TDD)** - Define behavior with tests before implementation
3. **Industry standards** - Adopt standards (A2A, CloudEvents) where applicable
4. **Progressive complexity** - Simple → Structured → Discoverable → Autonomous
5. **Explicit over implicit** - No magic inference, clear contracts
6. **Common library for shared DTOs** - `soorma-common` owns DTOs shared by services & SDK
7. **Explicit schemas for LLM consistency** - While LLMs can reason about payloads, explicit schemas provide predictability and debuggability

---

## Refactoring Process

When implementing refactoring tasks:

1. **Read existing code first** - Understand actual implementation; many items already have some implementation
2. **Write tests that define behavior** (TDD):
   - Add/modify tests to specify expected behavior
   - Run tests to see them fail
   - Implement the change
   - Run tests to see them pass
3. **Adapt industry standards** - Use A2A Agent Card, CloudEvents, etc. instead of proprietary specs
4. **DTOs in common library** - Shared models go in `soorma-common`, SDK re-exports them

---

## Documents

### SDK Refactoring (Focused Implementation)

The SDK refactoring plan has been split into focused documents for implementation:

| Document | Focus | Priority | Status |
|----------|-------|----------|--------|
| [sdk/00-OVERVIEW.md](sdk/00-OVERVIEW.md) | Overview & principles | Reference | 📋 |
| [sdk/01-EVENT-SYSTEM.md](sdk/01-EVENT-SYSTEM.md) | Event publishing & decorators | 🔴 Phase 1 | ✅ |
| [sdk/02-MEMORY-SDK.md](sdk/02-MEMORY-SDK.md) | TaskContext/PlanContext persistence | 🔴 Phase 1 | ✅ |
| [sdk/03-COMMON-DTOS.md](sdk/03-COMMON-DTOS.md) | Shared DTOs in soorma-common | 🔴 Phase 1 | ✅ |
| [sdk/04-TOOL-MODEL.md](sdk/04-TOOL-MODEL.md) | Tool synchronous model | 🟡 Phase 2 | ⬜ |
| [sdk/05-WORKER-MODEL.md](sdk/05-WORKER-MODEL.md) | Worker async model | 🟡 Phase 2 | ⬜ |
| [sdk/06-PLANNER-MODEL.md](sdk/06-PLANNER-MODEL.md) | Planner state machine | 🟡 Phase 2 | ⬜ |
| [sdk/07-DISCOVERY.md](sdk/07-DISCOVERY.md) | Discovery & A2A integration | 🟡 Phase 3 | ⬜ |
| [sdk/08-MIGRATION.md](sdk/08-MIGRATION.md) | Migration guide | 🟢 Phase 4 | ⬜ |
| [sdk/README.md](sdk/README.md) | SDK docs index | Reference | 📋 |

**📦 Archive:** [archive/SDK_REFACTORING_PLAN.md](archive/SDK_REFACTORING_PLAN.md) - Original monolithic plan (archived)

### Architecture Refactoring (Focused Implementation)

The architecture refactoring plan has been split into focused documents for implementation:

| Document | Focus | Priority | Status |
|----------|-------|----------|--------|
| [arch/00-OVERVIEW.md](arch/00-OVERVIEW.md) | Service map & principles | Reference | 📋 |
| [arch/01-EVENT-SERVICE.md](arch/01-EVENT-SERVICE.md) | Event envelope enhancements | 🔴 Phase 1 | ✅ |
| [arch/02-MEMORY-SERVICE.md](arch/02-MEMORY-SERVICE.md) | Task/plan context storage | 🔴 Phase 1 | ✅ |
| [arch/03-COMMON-LIBRARY.md](arch/03-COMMON-LIBRARY.md) | Shared DTOs (soorma-common) | 🔴 Phase 1 | ✅ |
| [arch/04-TRACKER-SERVICE.md](arch/04-TRACKER-SERVICE.md) | Event-driven observability | 🟡 Phase 2 | ⬜ |
| [arch/05-REGISTRY-SERVICE.md](arch/05-REGISTRY-SERVICE.md) | Enhanced discovery & A2A | 🟡 Phase 3 | ⬜ |
| [arch/06-USER-AGENT.md](arch/06-USER-AGENT.md) | HITL pattern | 🟢 Phase 4 | ⬜ |
| [arch/README.md](arch/README.md) | Architecture docs index | Reference | 📋 |

**📦 Archive:** [archive/ARCHITECTURE_REFACTORING_PLAN.md](archive/ARCHITECTURE_REFACTORING_PLAN.md) - Original monolithic plan (archived)

---

## Quick Reference: Key Design Decisions

### 1. Event Publishing (RF-SDK-001, RF-SDK-002, RF-SDK-013)
```python
# OLD: Topic inferred from event name (BAD)
await context.bus.publish("order.created", data={...})

# NEW: Topic explicit, response_event specified
await context.bus.publish(
    topic="action-requests",
    event_type="research.requested",
    data={...},
    response_event="research.completed",  # Caller specifies response
)

# NEW: Utility methods to create events from events (auto-propagate metadata)
child_params = context.bus.create_child_request(
    parent_event=goal_event,
    event_type="web.search.requested",
    data={"query": "AI trends"},
    response_event="task-1.search.done",
)
await context.bus.request(**child_params)  # trace_id, parent_event_id auto-copied
```

### 2. Agent Decorators (RF-SDK-003)
```python
# OLD: Only event_type
@agent.on_event("order.created")

# NEW: Topic required for base Agent
@agent.on_event(topic="business-facts", event_type="order.created")

# Higher abstractions have defaults
@worker.on_task("process.requested")  # Implies action-requests topic
@tool.on_invoke("calculate")           # Implies action-requests topic
```

### 3. Async Task Handling (RF-SDK-004)
```python
# OLD: Handler returns result (blocking)
@worker.on_task("process")
async def handle(task, ctx):
    return {"result": "done"}  # SDK publishes

# NEW: Handler manages async completion
@worker.on_task("process.requested")
async def handle(task, ctx):
    await task.save()  # Persist for async completion
    await task.delegate(...)  # Delegate to sub-agent
    # Returns without result - async completion via on_result

@worker.on_result("sub_task.completed")
async def handle_result(result, ctx):
    task = await result.restore_task()
    await task.complete({"result": "done"})  # Explicit completion
```

### 4. Planner State Machine (RF-SDK-006)
```python
@planner.on_goal("research.goal")
async def plan(goal, ctx):
    agents = await ctx.registry.discover(goal.requirements)
    plan = await planner.create_plan(goal, agents, ctx)
    await plan.save()
    await plan.execute_next()

@planner.on_transition()
async def transition(event, ctx):
    plan = await PlanContext.restore(event.correlation_id)
    plan.update_state(event)
    if plan.is_complete():
        await plan.finalize()
    else:
        await plan.execute_next()
```

### 5. Tracker via Events (RF-SDK-009, RF-ARCH-010)
```python
# OLD: Direct API call
await context.tracker.emit_progress(plan_id, task_id, status="running")

# NEW: Publish event, Tracker subscribes
await context.bus.publish(
    topic="system-events",
    event_type="task.progress",
    data={"plan_id": plan_id, "task_id": task_id, "status": "running"}
)
```

### 6. WorkflowState Helper (RF-SDK-014)
```python
# OLD: Manual working memory management (boilerplate)
workflow_state = await context.memory.retrieve("workflow_state", plan_id=plan_id) or {}
action_history = workflow_state.get('action_history', [])
action_history.append(event_name)
workflow_state['action_history'] = action_history
await context.memory.store("workflow_state", workflow_state, plan_id=plan_id)

# NEW: Helper class
from soorma.workflow import WorkflowState

state = WorkflowState(context, plan_id)
await state.record_action(event_name)
await state.set("research_data", research_results)
history = await state.get_action_history()
```

### 7. ChoreographyPlanner (RF-SDK-015, RF-SDK-016)
```python
# OLD: 400+ lines of boilerplate (event discovery, LLM prompts, validation)

# NEW: Autonomous orchestration class
from soorma.ai.choreography import ChoreographyPlanner
from soorma.ai.decisions import PlannerDecision, PlanAction

planner = ChoreographyPlanner(
    name="orchestrator",
    reasoning_model="gpt-4o",
    max_actions=10,  # Circuit breaker
)

@planner.on_goal("research.goal")
async def handle_goal(goal, context):
    # SDK handles: discovery, LLM reasoning, validation
    decision: PlannerDecision = await planner.reason_next_action(
        trigger=f"New goal: {goal.data['objective']}",
        context=context,
        plan_id=goal.correlation_id,
    )
    
    # SDK validates event exists BEFORE publishing (prevents hallucination)
    await planner.execute_decision(decision, context, goal_event=goal)
```

### 8. EventSelector for LLM Routing (RF-SDK-017, RF-SDK-018)
```python
# OLD: 150+ lines of boilerplate (discovery, formatting, LLM calls)

# NEW: LLM-based event selection utility
from soorma.ai.selection import EventSelector

# Agent provides domain-specific prompt
ROUTING_PROMPT = """
Analyze the ticket and select best routing.
TICKET: {{state}}
AVAILABLE ROUTES: {{events}}
Respond with JSON: {"event_type": "...", "payload": {...}, "reasoning": "..."}
"""

selector = EventSelector(
    context=context,
    topic="action-requests",
    prompt_template=ROUTING_PROMPT,
    model="gpt-4o-mini",
)

@worker.on_task("ticket.created")
async def route_ticket(task, context):
    # SDK handles: discovery, formatting, LLM call, validation
    decision = await selector.select_event(
        state={"ticket_data": task.data}
    )
    await selector.publish_decision(decision, correlation_id=task.correlation_id)
```

---

## Implementation Order & Copilot Agent Prompts

This section provides **order-based** guidance for implementing refactoring tasks. Each stage must be completed before moving to the next.

### **Stage 1: Foundation - Event System** 🔴

**Documents:** [arch/01-EVENT-SERVICE.md](arch/01-EVENT-SERVICE.md) + [sdk/01-EVENT-SYSTEM.md](sdk/01-EVENT-SYSTEM.md)

**Tasks:** RF-ARCH-003, RF-ARCH-004, RF-SDK-001, RF-SDK-002, RF-SDK-003, RF-SDK-013

**Copilot Agent Prompt:**
```
Implement Stage 1 (Foundation - Event System) of the Soorma Core refactoring.

Reference documents:
- docs/refactoring/arch/01-EVENT-SERVICE.md (Service changes)
- docs/refactoring/sdk/01-EVENT-SYSTEM.md (SDK changes)

Key deliverables:
1. Update EventEnvelope in soorma-common with response_event, response_topic, trace_id, parent_event_id, payload_schema_name
2. Update Event Service to accept and propagate new envelope fields
3. Document messaging patterns (already implemented): queue behavior, broadcast, load balancing via queue_group
4. Remove topic inference from BusClient, add explicit topic parameter
5. Add convenience methods: request(), respond(), announce()
6. Add event creation utilities: create_child_request(), create_response() for auto-propagating metadata
7. Add response_event parameter to publish() method
8. Update on_event() decorator to require topic parameter
9. Write tests for all changes (TDD)
10. Update examples to use new patterns

Note: Event Service already supports queue/broadcast/load-balancing patterns via queue_group parameter. Focus on documenting usage and updating examples.

Follow TDD: write tests first, then implement. Coordinate service and SDK changes together.
```

**Completion Criteria:**
- ✅ EventEnvelope has new fields (including payload_schema_name)
- ✅ Event Service messaging patterns documented (queue_group usage)
- ✅ BusClient.publish() requires topic
- ✅ BusClient has create_child_request() and create_response() utilities
- ✅ on_event() requires topic for base Agent
- ✅ All tests pass (64/64)
- ✅ Examples updated with pattern usage
- ✅ CHANGELOG.md updated

**Status:** ✅ **COMPLETE** (January 17, 2026)

---

### **Stage 2: Foundation - Memory & Common DTOs** 🔴

**Documents:** [arch/02-MEMORY-SERVICE.md](arch/02-MEMORY-SERVICE.md) + [sdk/02-MEMORY-SDK.md](sdk/02-MEMORY-SDK.md) + [arch/03-COMMON-LIBRARY.md](arch/03-COMMON-LIBRARY.md) + [sdk/03-COMMON-DTOS.md](sdk/03-COMMON-DTOS.md)

**Tasks:** RF-ARCH-008, RF-ARCH-009, RF-SDK-010, RF-SDK-011, RF-SDK-012, RF-SDK-014

**Copilot Agent Prompt:**
```
Implement Stage 2 (Foundation - Memory & Common DTOs) of the Soorma Core refactoring.

Reference documents:
- docs/refactoring/arch/02-MEMORY-SERVICE.md (Memory Service endpoints)
- docs/refactoring/sdk/02-MEMORY-SDK.md (Memory SDK client)
- docs/refactoring/arch/03-COMMON-LIBRARY.md (Shared DTOs)
- docs/refactoring/sdk/03-COMMON-DTOS.md (DTO usage & Tracker events)

Key deliverables:
1. Create TaskContext and PlanContext memory types in Memory Service
2. Add save/restore/query endpoints for task and plan contexts
3. Add MemoryClient methods to SDK (save_task_context, restore_task_context, etc.)
4. Create soorma-common library with shared DTOs:
   - StateConfig, StateTransition, StateAction
   - A2AAgentCard, A2ATask, A2ATaskResult
   - Progress tracking event schemas
5. Add WorkflowState helper class for managing plan-scoped state (RF-SDK-014)
6. Update Tracker to subscribe to system-events topic instead of API calls
7. Write tests for all changes (TDD)

Dependencies: Stage 1 must be complete (event system foundation).
```

**Completion Criteria:**
- ✅ Memory Service has task/plan context endpoints
- ✅ MemoryClient provides save/restore methods
- ✅ soorma-common library exists with shared DTOs
- ✅ WorkflowState helper provides plan-scoped state management
- ✅ Tracker subscribes to events (no-op, service in Stage 4)
- ✅ All tests pass

**Status:** ✅ **COMPLETE** (January 21, 2026)

**Implementation Notes:**
- Created 5 new tables in Memory Service: `task_context`, `plan_context`, `plans`, `sessions`, `plan_context` with full RLS
- Added 23 new API endpoints across 8 files (task-context, plan-context, plans, sessions, working, semantic, episodic, procedural)
- Refactored all endpoints to API → Service → CRUD pattern with proper transaction boundaries
- TenantContext dependency injection eliminates 3-4 lines of auth boilerplate per endpoint
- Added 13 new methods to MemoryClient for task/plan context and session management
- Created WorkflowState helper class with 12 convenience methods (reduces boilerplate 8:1)
- Added 18 new DTOs to soorma-common (state.py, a2a.py, tracking.py) - 61 total exports
- Tracker integration via events (removed emit_progress, complete_task, fail_task)
- Memory Service: 37 tests passing (29 unit + 8 validation)
- SDK: 192 tests passing with full memory client coverage
- soorma-common: 44 tests passing with comprehensive DTO validation
- **Total: 273 tests passing (100% success rate)**

**Follow-up Work (Stage 2.1):**

**Architecture Tasks:**
- ⬜ **RF-ARCH-012**: Semantic Memory Upsert (Service)
  - Document: [arch/02-MEMORY-SERVICE.md](arch/02-MEMORY-SERVICE.md) RF-ARCH-012
  - Design documented in [services/memory/SEMANTIC_MEMORY_UPSERT.md](../../services/memory/SEMANTIC_MEMORY_UPSERT.md)
  - Add external_id and content_hash columns to semantic_memory table
  - Implement upsert CRUD function with dual-constraint logic
  - Update service layer and API endpoints
  - Write tests for versioning and deduplication scenarios
  - **Priority:** P1 (High) - Prevents data quality issues
  - **Estimated effort:** 2-3 days

- ⬜ **RF-ARCH-014**: Semantic Memory Privacy (Service)
  - Document: [arch/02-MEMORY-SERVICE.md](arch/02-MEMORY-SERVICE.md) RF-ARCH-014
  - Add user_id column (required) and is_public flag (optional, default false) to semantic_memory table
  - Update RLS policies for private-by-default with optional tenant-wide sharing
  - Update CRUD functions to enforce user_id requirement
  - Write tests for privacy isolation and public knowledge scenarios
  - **Rationale:** Semantic memory is agent memory (CoALA), not a RAG solution - should be private by default
  - **Priority:** P1 (High) - Fundamental privacy model
  - **Estimated effort:** 2-3 days

- ⬜ **RF-ARCH-013**: Working Memory Deletion (Service)
  - Document: [arch/02-MEMORY-SERVICE.md](arch/02-MEMORY-SERVICE.md) RF-ARCH-013
  - Add DELETE endpoints for plan state cleanup:
    * `DELETE /v1/memory/working/{plan_id}` - Delete all keys for a plan
    * `DELETE /v1/memory/working/{plan_id}/{key}` - Delete individual key
  - Implement delete CRUD functions with RLS enforcement
  - Write tests for deletion scenarios and RLS
  - **Priority:** P2 (Medium) - Not blocking, but prevents data accumulation
  - **Estimated effort:** 1-2 days

**SDK Tasks:**
- ⬜ **RF-SDK-019**: Semantic Memory Upsert SDK
  - Document: [sdk/02-MEMORY-SDK.md](sdk/02-MEMORY-SDK.md) RF-SDK-019
  - Add external_id parameter to `store_knowledge()` method
  - Update SemanticMemoryCreate DTO in soorma-common
  - Update HTTP call to include external_id
  - Write tests for upsert behavior (external_id and content_hash)
  - **Priority:** P1 (High) - Pairs with RF-ARCH-012
  - **Estimated effort:** 1-2 days

- ⬜ **RF-SDK-021**: Semantic Memory Privacy SDK
  - Document: [sdk/02-MEMORY-SDK.md](sdk/02-MEMORY-SDK.md) RF-SDK-021
  - Add user_id parameter (required) to `store_knowledge()` method
  - Add is_public parameter (optional, default False) to `store_knowledge()` method
  - Update SemanticMemoryCreate DTO in soorma-common
  - Update query methods to filter by user_id unless querying public knowledge
  - Write tests for private/public knowledge scenarios
  - **Priority:** P1 (High) - Pairs with RF-ARCH-014
  - **Estimated effort:** 1-2 days

- ⬜ **RF-SDK-020**: Working Memory Deletion SDK
  - Document: [sdk/02-MEMORY-SDK.md](sdk/02-MEMORY-SDK.md) RF-SDK-020
  - Add `delete_plan_state()` method to MemoryClient
  - Add `delete_plan()` method to MemoryClient
  - Update WorkflowState helper with `delete()` and `cleanup()` methods
  - Write tests for deletion methods
  - Document usage patterns (explicit cleanup, background job, accept persistence)
  - **Priority:** P2 (Medium) - Pairs with RF-ARCH-013
  - **Estimated effort:** 1 day

**Implementation Order:**
1. RF-ARCH-012 (Service) + RF-SDK-019 (SDK) together (semantic memory upsert)
2. RF-ARCH-014 (Service) + RF-SDK-021 (SDK) together (semantic memory privacy)
3. RF-ARCH-013 (Service) + RF-SDK-020 (SDK) together (working memory deletion)

**Total Estimated Effort:** 8-13 days for all service and SDK changes

---

### **Stage 3: Agent Models - Tool & Worker** 🟡

**Documents:** [sdk/04-TOOL-MODEL.md](sdk/04-TOOL-MODEL.md) + [sdk/05-WORKER-MODEL.md](sdk/05-WORKER-MODEL.md)

**Tasks:** RF-SDK-005, RF-SDK-004

**Copilot Agent Prompt:**
```
Implement Stage 3 (Agent Models - Tool & Worker) of the Soorma Core refactoring.

Reference documents:
- docs/refactoring/sdk/04-TOOL-MODEL.md (Tool synchronous model)
- docs/refactoring/sdk/05-WORKER-MODEL.md (Worker async model)

Key deliverables:
1. Simplify Tool model:
   - on_invoke() decorator with explicit topic default (action-requests)
   - Handler returns result directly
   - SDK publishes response to response_event from request
2. Refactor Worker model for async choreography:
   - on_task() and on_result() decorators
   - task.save() / task.restore() using Memory SDK
   - task.delegate() for sub-agent calls
   - task.complete() for explicit async completion
3. Update examples (calculator tool, research worker)
4. Write tests for both models (TDD)

Dependencies: Stage 1 (event system) and Stage 2 (memory) must be complete.
```

**Completion Criteria:**
- ✅ Tool model simplified with on_invoke()
- ✅ Worker model supports async tasks with save/restore
- ✅ Examples work with new models
- ✅ All tests pass

---

### **Stage 4: Agent Models - Planner** 🟡

**Documents:** [sdk/06-PLANNER-MODEL.md](sdk/06-PLANNER-MODEL.md) + [arch/04-TRACKER-SERVICE.md](arch/04-TRACKER-SERVICE.md)

**Tasks:** RF-SDK-006, RF-SDK-015, RF-SDK-016, RF-ARCH-010, RF-ARCH-011

**Copilot Agent Prompt:**
```
Implement Stage 4 (Agent Models - Planner) of the Soorma Core refactoring.

Reference documents:
- docs/refactoring/sdk/06-PLANNER-MODEL.md (Planner state machine)
- docs/refactoring/arch/04-TRACKER-SERVICE.md (Event-driven observability)

Key deliverables:
1. Implement Planner state machine:
   - on_goal() decorator for goal handling
   - on_transition() decorator for state transitions
   - PlanContext with state machine (states, transitions, actions)
   - plan.save() / plan.restore() using Memory SDK
   - plan.execute_next() for state-driven task execution
2. Add PlannerDecision and PlanAction types for type-safe LLM decisions (RF-SDK-015)
3. Implement ChoreographyPlanner class for autonomous orchestration (RF-SDK-016):
   - LLM-based reasoning for next action selection
   - Event discovery integration
   - Registry validation (prevent hallucinated events)
   - Type-safe decision execution
4. Update Tracker Service:
   - Subscribe to system-events topic
   - Store task progress events
   - Provide query API for progress timelines
5. Update research-advisor example with ChoreographyPlanner
6. Write tests for state machine, ChoreographyPlanner, and Tracker (TDD)

Dependencies: Stage 1 (events), Stage 2 (memory), Stage 3 (worker) must be complete.
```

**Completion Criteria:**
- ✅ Planner supports on_goal() and on_transition()
- ✅ PlanContext state machine works
- ✅ PlannerDecision types provide type safety
- ✅ ChoreographyPlanner handles autonomous orchestration
- ✅ Tracker stores and queries progress events
- ✅ All tests pass

---

### **Stage 5: Discovery & A2A** 🟡

**Documents:** [arch/05-REGISTRY-SERVICE.md](arch/05-REGISTRY-SERVICE.md) + [sdk/07-DISCOVERY.md](sdk/07-DISCOVERY.md)

**Tasks:** RF-ARCH-005, RF-ARCH-006, RF-ARCH-007, RF-SDK-007, RF-SDK-008, RF-SDK-017, RF-SDK-018

**Copilot Agent Prompt:**
```
Implement Stage 5 (Discovery & A2A) of the Soorma Core refactoring.

Reference documents:
- docs/refactoring/arch/05-REGISTRY-SERVICE.md (Registry enhancements)
- docs/refactoring/sdk/07-DISCOVERY.md (Discovery & A2A gateway)

Key deliverables:
1. Update Registry Service:
   - Schema registration by schema name (not event name)
   - Events nested within capabilities (EventDefinition with payload_schema_name)
   - Structured capability with input/output schemas
   - Discovery API with natural language search
   - A2AAgentCard publication
2. Update SDK:
   - Event registration tied to agent startup
   - RegistryClient.discover() for capability-based discovery
   - A2A Gateway for external protocol clients
3. Add EventSelector utility for LLM-based event selection (RF-SDK-017):
   - Customizable prompt templates
   - Type-safe EventDecision output
   - Registry validation before publishing
4. Add EventToolkit.format_for_llm_selection() helper (RF-SDK-018)
5. Event payloads include payload_schema_name for LLM schema lookup
6. Update examples to use discovery and EventSelector
7. Write tests for discovery, EventSelector, and A2A (TDD)

Dependencies: Stage 1 (events), Stage 2 (common DTOs) must be complete.
```

**Completion Criteria:**
- ✅ Registry supports schema registration by name
- ✅ Events reference payload_schema_name (not embedded schemas)
- ✅ Discovery API works with natural language
- ✅ EventSelector provides LLM-based event selection
- ✅ EventToolkit has LLM formatting helpers
- ✅ A2A Gateway exposes agents
- ✅ All tests pass

---

### **Stage 6: Migration & Polish** 🟢

**Documents:** [sdk/08-MIGRATION.md](sdk/08-MIGRATION.md) + [arch/06-USER-AGENT.md](arch/06-USER-AGENT.md)

**Tasks:** RF-ARCH-002, Migration Guide

**Copilot Agent Prompt:**
```
Implement Stage 6 (Migration & Polish) of the Soorma Core refactoring.

Reference documents:
- docs/refactoring/sdk/08-MIGRATION.md (Migration guide)
- docs/refactoring/arch/06-USER-AGENT.md (HITL pattern reference)

Key deliverables:
1. Create comprehensive migration guide:
   - Breaking changes list
   - Before/after code examples
   - Migration scripts where possible
2. Note: User-Agent service will be implemented in soorma-cloud (not soorma-core)
   - Document HITL pattern contract for soorma-cloud implementation
   - Subscribe to notification-events topic
   - Human-in-the-loop pattern
   - Approval workflows
3. Update all documentation (ARCHITECTURE.md, README.md, etc.)
4. Final testing and validation

Dependencies: All previous stages must be complete.
```

**Completion Criteria:**
- ✅ Migration guide complete with examples
- ✅ User-Agent service contract documented (for soorma-cloud)
- ✅ All documentation updated
- ✅ All examples working
- ✅ All tests passing

---

## Task Reference Index

Quick lookup table for all refactoring tasks:

| Task ID | Description | Stage | Document | Status |
|---------|-------------|-------|----------|--------|
| RF-ARCH-003 | Event envelope enhancements | Stage 1 | [01-EVENT-SERVICE](arch/01-EVENT-SERVICE.md) | ✅ |
| RF-ARCH-004 | Correlation ID semantics | Stage 1 | [01-EVENT-SERVICE](arch/01-EVENT-SERVICE.md) | ✅ |
| RF-SDK-001 | Remove topic inference from BusClient | Stage 1 | [01-EVENT-SYSTEM](sdk/01-EVENT-SYSTEM.md) | ✅ |
| RF-SDK-002 | Add response_event to action requests | Stage 1 | [01-EVENT-SYSTEM](sdk/01-EVENT-SYSTEM.md) | ✅ |
| RF-SDK-003 | Refactor on_event() signature | Stage 1 | [01-EVENT-SYSTEM](sdk/01-EVENT-SYSTEM.md) | ✅ |
| RF-SDK-013 | Event creation utilities (auto-propagate metadata) | Stage 1 | [01-EVENT-SYSTEM](sdk/01-EVENT-SYSTEM.md) | ✅ |
| RF-ARCH-008 | TaskContext memory type | Stage 2 | [02-MEMORY-SERVICE](arch/02-MEMORY-SERVICE.md) | ✅ |
| RF-ARCH-009 | Plan/session query APIs | Stage 2 | [02-MEMORY-SERVICE](arch/02-MEMORY-SERVICE.md) | ✅ |
| RF-SDK-010 | Memory SDK methods | Stage 2 | [02-MEMORY-SDK](sdk/02-MEMORY-SDK.md) | ✅ |
| RF-SDK-011 | Tracker via events, not API | Stage 2 | [03-COMMON-DTOS](sdk/03-COMMON-DTOS.md) | ✅ |
| RF-SDK-012 | Common library DTOs (State, A2A) | Stage 2 | [03-COMMON-DTOS](sdk/03-COMMON-DTOS.md) | ✅ |
| RF-SDK-014 | WorkflowState helper for plan state | Stage 2 | [02-MEMORY-SDK](sdk/02-MEMORY-SDK.md) | ✅ |
| RF-ARCH-012 | Semantic memory upsert (external_id + content_hash) | Stage 2.1 | [SEMANTIC_MEMORY_UPSERT](../../services/memory/SEMANTIC_MEMORY_UPSERT.md) | ⬜ |
| RF-ARCH-013 | Working memory deletion (DELETE endpoints) | Stage 2.1 | [02-MEMORY-SERVICE](arch/02-MEMORY-SERVICE.md) | ⬜ |
| RF-ARCH-014 | Semantic memory privacy (user_id + is_public) | Stage 2.1 | [02-MEMORY-SERVICE](arch/02-MEMORY-SERVICE.md) | ⬜ |
| RF-SDK-019 | Semantic memory upsert SDK (external_id parameter) | Stage 2.1 | [02-MEMORY-SDK](sdk/02-MEMORY-SDK.md) | ⬜ |
| RF-SDK-020 | Working memory deletion SDK (delete methods) | Stage 2.1 | [02-MEMORY-SDK](sdk/02-MEMORY-SDK.md) | ⬜ |
| RF-SDK-021 | Semantic memory privacy SDK (user_id + is_public) | Stage 2.1 | [02-MEMORY-SDK](sdk/02-MEMORY-SDK.md) | ⬜ |
| RF-SDK-005 | Tool synchronous model simplify | Stage 3 | [04-TOOL-MODEL](sdk/04-TOOL-MODEL.md) | ⬜ |
| RF-SDK-004 | Worker async task model | Stage 3 | [05-WORKER-MODEL](sdk/05-WORKER-MODEL.md) | ⬜ |
| RF-SDK-006 | Planner on_goal and on_transition | Stage 4 | [06-PLANNER-MODEL](sdk/06-PLANNER-MODEL.md) | ⬜ |
| RF-SDK-015 | PlannerDecision and PlanAction types | Stage 4 | [06-PLANNER-MODEL](sdk/06-PLANNER-MODEL.md) | ⬜ |
| RF-SDK-016 | ChoreographyPlanner class | Stage 4 | [06-PLANNER-MODEL](sdk/06-PLANNER-MODEL.md) | ⬜ |
| RF-ARCH-010 | Tracker as event listener | Stage 4 | [04-TRACKER-SERVICE](arch/04-TRACKER-SERVICE.md) | ⬜ |
| RF-ARCH-011 | Task progress model | Stage 4 | [04-TRACKER-SERVICE](arch/04-TRACKER-SERVICE.md) | ⬜ |
| RF-ARCH-005 | Schema registration by name (not event name) | Stage 5 | [05-REGISTRY-SERVICE](arch/05-REGISTRY-SERVICE.md) | ⬜ |
| RF-ARCH-006 | Structured capability with EventDefinition | Stage 5 | [05-REGISTRY-SERVICE](arch/05-REGISTRY-SERVICE.md) | ⬜ |
| RF-ARCH-007 | Discovery API for LLM reasoning | Stage 5 | [05-REGISTRY-SERVICE](arch/05-REGISTRY-SERVICE.md) | ⬜ |
| RF-SDK-007 | Event registration tied to agent | Stage 5 | [07-DISCOVERY](sdk/07-DISCOVERY.md) | ⬜ |
| RF-SDK-008 | Agent discovery by capability (A2A) | Stage 5 | [07-DISCOVERY](sdk/07-DISCOVERY.md) | ⬜ |
| RF-SDK-017 | EventSelector utility for LLM event selection | Stage 5 | [07-DISCOVERY](sdk/07-DISCOVERY.md) | ⬜ |
| RF-SDK-018 | EventToolkit.format_for_llm_selection() | Stage 5 | [07-DISCOVERY](sdk/07-DISCOVERY.md) | ⬜ |
| RF-ARCH-002 | HITL pattern (User-Agent in soorma-cloud) | Stage 6 | [06-USER-AGENT](arch/06-USER-AGENT.md) | ⬜ |
| RF-ARCH-001 | Clarify business-facts purpose | Reference | [00-OVERVIEW](arch/00-OVERVIEW.md) | ⬜ |

---

## Open Questions Summary

| Question | Options | Decision/Status | Document |
|----------|---------|-----------------|----------|
| Event registration within capabilities? | A) Always nested, B) Both, C) Progressive | ✅ C) Progressive | [07-DISCOVERY](sdk/07-DISCOVERY.md) |
| HITL events topic? | A) notifications, B) action-requests, C) new topic | ✅ A) notifications | [03-COMMON-DTOS](sdk/03-COMMON-DTOS.md) |
| Planner without Tracker service? | Yes/No | Yes (Working Memory) | [06-PLANNER-MODEL](sdk/06-PLANNER-MODEL.md) |
| Re-entrant plans for long-running conversations? | Design support | ✅ Supported | [06-PLANNER-MODEL](sdk/06-PLANNER-MODEL.md) |
| Schema validation at runtime? | A) None, B) Publish, C) Receive, D) Both | Leaning B) Publish | [01-EVENT-SYSTEM](sdk/01-EVENT-SYSTEM.md) |
| Event versioning strategy? | A) In name, B) In payload, C) Schema registry | B) for MVP | [01-EVENT-SERVICE](arch/01-EVENT-SERVICE.md) |
| Multi-tenancy enforcement? | A) Trust, B) Validate at Event Service | B) Validate | [01-EVENT-SERVICE](arch/01-EVENT-SERVICE.md) |
| Event retention? | A) None, B) Time-based, C) Selective | B) Time-based | [04-TRACKER-SERVICE](arch/04-TRACKER-SERVICE.md) |
| Produced events needed? | Yes (for docs & business-facts) | Yes | [05-REGISTRY-SERVICE](arch/05-REGISTRY-SERVICE.md) |

---

## Next Steps

1. **Review focused documents** - Each SDK and Architecture document is now self-contained
2. **Note coordination requirements** - See SDK ↔ Architecture coordination matrix below
3. **Write Tests** - Define behavior with tests before implementation
4. **Implement in phases** - Execute refactoring tasks in dependency order
5. **Document** - Update ARCHITECTURE.md and other docs as changes land

---

## SDK ↔ Architecture Coordination

**Critical:** Service and SDK changes must be coordinated. Here's the pairing:

```
Service                           SDK
────────────────────────────────────────────────────────────
arch/01-EVENT-SERVICE      ←→    sdk/01-EVENT-SYSTEM
  (Envelope fields)               (BusClient methods)
  RF-ARCH-003, 004                RF-SDK-001, 002, 003

arch/02-MEMORY-SERVICE     ←→    sdk/02-MEMORY-SDK
  (Task/plan endpoints)           (MemoryClient methods)
  RF-ARCH-008, 009                RF-SDK-010

arch/03-COMMON-LIBRARY     ←→    sdk/03-COMMON-DTOS
  (Shared DTOs)                   (SDK re-exports)
  State, A2A, Tracking            RF-SDK-011, 012

arch/04-TRACKER-SERVICE    ←→    sdk/03-COMMON-DTOS
  (Event subscribers)             (Publish progress events)
  RF-ARCH-010, 011                RF-SDK-011

arch/05-REGISTRY-SERVICE   ←→    sdk/07-DISCOVERY
  (Discovery API)                 (RegistryClient.discover)
  RF-ARCH-005, 006, 007           RF-SDK-007, 008

arch/06-USER-AGENT         ←→    (Standalone)
  (HITL service)
  RF-ARCH-002
```

**Implementation Pattern:**
1. Update service (endpoints, schemas)
2. Update SDK (client methods)
3. Update examples
4. Deploy service → Deploy SDK → Update examples

---

## Post-Refactoring: Examples Development

**After completing all stages (1-6), proceed to examples development:**

📍 **Next:** [EXAMPLES_REFACTOR_PLAN.md](../EXAMPLES_REFACTOR_PLAN.md) Phase 3-5

**Dependencies:**
- ✅ Stage 1-5 SDK primitives complete
- ✅ WorkflowState, ChoreographyPlanner, EventSelector available
- ✅ Stage 6 migration guide complete

**What's Next:**
1. **Phase 3: Memory Examples** (Week 2)
   - `04-memory-semantic/` - RAG pattern
   - `05-memory-working/` - Plan-scoped state (uses WorkflowState)
   - `06-memory-episodic/` - Conversation history

2. **Phase 4: Advanced Examples** (Week 2-3)
   - `07-tool-discovery/` - Dynamic capability discovery
   - `08-planner-worker-basic/` - Trinity pattern
   - `09-app-research-advisor/` - Uses ChoreographyPlanner
   - `10-multi-turn-conversation/` - Stateful conversations

3. **Phase 5: Documentation & AI Tooling** (Week 3)
   - Create `.cursorrules` for AI assistant guidance
   - Pattern catalog (`docs/PATTERNS.md`)
   - Update blog posts with example references

**Estimated Timeline:** 2-3 weeks after Stage 6 completion

**Success Criteria:**
- [ ] Developer can complete learning path in 2 hours
- [ ] Each example runs independently with `soorma dev`
- [ ] AI assistants recommend correct example for each task
- [ ] `research-advisor` planner is <100 lines (vs current 485)

---

## Related Documentation

- [ARCHITECTURE.md](../ARCHITECTURE.md) - Current platform architecture
- [DESIGN_PATTERNS.md](../DESIGN_PATTERNS.md) - Agent design patterns
- [EVENT_PATTERNS.md](../EVENT_PATTERNS.md) - Event-driven patterns
- [TOPICS.md](../TOPICS.md) - Topic definitions
- [Memory ARCHITECTURE.md](../../services/memory/ARCHITECTURE.md) - Memory service design
- [EXAMPLES_REFACTOR_PLAN.md](../EXAMPLES_REFACTOR_PLAN.md) - Progressive examples roadmap
