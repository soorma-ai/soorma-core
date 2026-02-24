# Soorma Core Refactoring Index

**Status:** 📋 Stage 1-4 Complete | Release: 0.8.0 (February 23, 2026)  
**Last Updated:** February 23, 2026 - Stage 4 Complete (Planner & ChoreographyPlanner)

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
| [sdk/04-TOOL-MODEL.md](sdk/04-TOOL-MODEL.md) | Tool synchronous model | 🟡 Phase 2 | ✅ |
| [sdk/05-WORKER-MODEL.md](sdk/05-WORKER-MODEL.md) | Worker async model | 🟡 Phase 2 | ✅ |
| [sdk/06-PLANNER-MODEL.md](sdk/06-PLANNER-MODEL.md) | Planner state machine | 🟢 Phase 3 | ✅ |
| [sdk/07-DISCOVERY.md](sdk/07-DISCOVERY.md) | Discovery & A2A integration | 🟡 Phase 3 | ⬜ |
| [sdk/08-MIGRATION.md](sdk/08-MIGRATION.md) | Migration guide | 🟢 Phase 4 | 🟡 |
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
| [arch/04-TRACKER-SERVICE.md](arch/04-TRACKER-SERVICE.md) | Event-driven observability | 🟡 Phase 2 | ✅ |
| [arch/05-REGISTRY-SERVICE.md](arch/05-REGISTRY-SERVICE.md) | Enhanced discovery & A2A | 🟢 Phase 3 | ⬜ |
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

### 3. Async Task Handling (RF-SDK-004) ✅ IMPLEMENTED
```python
# OLD: Handler returns result (blocking)
@worker.on_task("process")
async def handle(task, ctx):
    return {"result": "done"}  # SDK publishes

# NEW: Handler manages async completion (implemented Feb 12, 2026)
@worker.on_task("process.requested")
async def handle(task, ctx):
    await task.save()  # Persist for async completion
    await task.delegate(...)  # Delegate to sub-agent
    # Returns without result - async completion via on_result

@worker.on_result("sub_task.completed")
async def handle_result(result, ctx):
    task = await result.restore_task()
    await task.complete({"result": "done"})  # Explicit completion

# NEW: Parallel delegation (fan-out/fan-in)
group_id = await task.delegate_parallel([
    DelegationSpec(event_type="inventory.reserve.requested", data={...}),
    DelegationSpec(event_type="payment.process.requested", data={...}),
])
# Later, when all results arrive:
if await task.aggregate_parallel_results(group_id):
    await task.complete({...})  # All successful
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

### **Stage 1: Foundation - Event System** ✅ COMPLETE

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

### **Stage 2: Foundation - Memory & Common DTOs** ✅ COMPLETE

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

**Status:** ✅ **COMPLETE** (January 21, 2026 - Stage 2, January 30, 2026 - Stage 2.1)

**Stage 2.1 Completion Summary (January 30, 2026 - Release 0.7.5):**

All 4 phases of Stage 2.1 successfully completed with 452/452 tests passing:

**Phase 1 & 2: Semantic Memory Enhancements** ✅
- RF-ARCH-012 + RF-SDK-019: Semantic memory upsert with external_id and content_hash
- RF-ARCH-014 + RF-SDK-021: Semantic memory privacy (user_id required, is_public optional)
- Dual-constraint upsert logic with conditional unique indexes
- Private by default (user-scoped), optional tenant-wide sharing via is_public flag
- RLS enforces privacy at database level
- Security pattern: user_id from auth context (query param), not request body

**Phase 3: Working Memory Deletion** ✅
- RF-ARCH-013 + RF-SDK-020: DELETE endpoints and SDK methods for plan state cleanup
- DELETE /v1/memory/working/{plan_id} - Delete all keys for a plan
- DELETE /v1/memory/working/{plan_id}/{key} - Delete individual key
- MemoryClient.delete_plan_state() with optional key parameter
- WorkflowState.delete() and cleanup() helper methods

**Phase 4: Documentation & Validation** ✅
- All CHANGELOGs updated with 0.7.5 entries
- Refactoring documentation updated with Stage 2.1 completion
- All 452/452 tests passing (100% success rate)
- Commit: 74bcfd1 (chore: Complete Stage 2.1 refactoring)

**Test Coverage (Release 0.7.5):**
- Memory Service: 108 tests passing
- SDK Python: 239 tests passing
- soorma-common: 44 tests passing
- Event Service: 21 tests passing
- Registry Service: 50 tests passing (1 fixed: agent deduplication)
- **Total:** 452/452 tests passing (100% success rate)

**Stage 2 + 2.1 Implementation Summary:**
- Created 5 new tables in Memory Service with full RLS
- Added 23+ new API endpoints across 9 files
- Refactored all endpoints to API → Service → CRUD pattern
- TenantContext dependency injection eliminates boilerplate
- Added 16+ new methods to MemoryClient
- Created WorkflowState helper class with 12+ convenience methods
- Added 18 new DTOs to soorma-common - 61 total exports
- Tracker integration via events
**Stage 2.1 Follow-up Work: All 6 Tasks Completed** ✅

All Stage 2.1 tasks completed on schedule (January 27-30, 2026):
- ✅ RF-ARCH-012 (Semantic Memory Upsert) - Complete, January 27
- ✅ RF-ARCH-013 (Working Memory Deletion) - Complete, January 29
- ✅ RF-ARCH-014 (Semantic Memory Privacy) - Complete, January 27
- ✅ RF-SDK-019 (Semantic Memory Upsert SDK) - Complete, January 27
- ✅ RF-SDK-020 (Working Memory Deletion SDK) - Complete, January 29
- ✅ RF-SDK-021 (Semantic Memory Privacy SDK) - Complete, January 27

For detailed implementation notes, see [STAGE_2.1_WORKING_PLAN.md](STAGE_2.1_WORKING_PLAN.md)

---

### **Stage 3: Agent Models - Tool & Worker** ✅ COMPLETE

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
    - Register only events with handlers (do not register structured capabilities without handlers)
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

### **Stage 4: Agent Models - Planner** ✅ COMPLETE

**Status:** ✅ **COMPLETE** (February 23, 2026 - Release 0.8.0)

**Master Plan:** [docs/agent_patterns/plans/MASTER_PLAN_Stage4_Planner.md](../agent_patterns/plans/MASTER_PLAN_Stage4_Planner.md)

**Documents:** [sdk/06-PLANNER-MODEL.md](sdk/06-PLANNER-MODEL.md) + [arch/04-TRACKER-SERVICE.md](arch/04-TRACKER-SERVICE.md)

**Tasks:** RF-SDK-006, RF-SDK-015, RF-SDK-016, RF-SDK-023, RF-ARCH-010, RF-ARCH-011

**Deferred to Stage 5+:** RF-SDK-017 (EventSelector), RF-SDK-018 (EventToolkit helpers) - See [DEFERRED_WORK.md](DEFERRED_WORK.md)

**Completion Summary (February 23, 2026 - Release 0.8.0):**

All 4 phases of Stage 4 successfully completed with 451+ tests passing:

**Phase 1: PlanContext Foundation (Days 1-4)** ✅
- PlanContext state machine model with save/restore/execute_next methods
- StateConfig, StateAction, StateTransition models for declarative workflows
- on_goal() and on_transition() decorators for clean handler signatures
- GoalContext wrapper for simplified goal access
- Template interpolation for dynamic action data ({{goal_data.field}})
- 09-planner-basic example demonstrating state machine orchestration
- Tests passing

**Phase 2: ChoreographyPlanner (Days 5-7)** ✅
- ChoreographyPlanner class for LLM-based autonomous orchestration
- PlannerDecision types (PUBLISH, COMPLETE, WAIT, DELEGATE) for type-safe decisions
- LLM integration via LiteLLM (OpenAI, Azure, Anthropic, Ollama)
- Event discovery from Registry Service (prevents hallucinations)
- Business rules injection via system_instructions parameter
- Runtime context via custom_context parameter
- Circuit breaker pattern (max_actions) for safety
- Event validation before publishing
- 10-choreography-basic example demonstrating autonomous workflow
- Tests passing

**Phase 3: Tracker Service Integration (Days 8-10)** ✅
- TrackerServiceClient (service layer) for event-driven observability
- TrackerClient wrapper (PlatformContext layer) for agent-friendly API
- Plan progress tracking (completed_tasks, task_count, status)
- Action history timeline with event correlation
- Integration in 10-choreography-basic example
- Tests passing (28 Tracker tests + SDK integration tests)

**Phase 4: Documentation & Release (Days 11-12)** ✅
- Pattern selection framework in docs/agent_patterns/README.md
- Comprehensive Planner architecture in docs/agent_patterns/ARCHITECTURE.md
- Pattern comparison tables and decision flowcharts
- Examples catalog updated with 09-planner-basic and 10-choreography-basic
- Tracker service documentation enhanced
- All versions bumped to 0.8.0
- All CHANGELOGs updated

**Implementation Summary:**
- ✅ 451+ tests passing (423 SDK + 28 Tracker)
- ✅ Pattern selection framework for developer guidance
- ✅ Two-layer architecture maintained (service clients + wrappers)
- ✅ Two working examples (09-planner-basic, 10-choreography-basic)
- ✅ Comprehensive documentation with decision criteria and code examples
- ✅ Version 0.8.0 release ready

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
```
**Completion Criteria:**
- ✅ Planner supports on_goal() and on_transition() (RF-SDK-006)
- ✅ PlanContext state machine works with event-based transitions
- ✅ PlannerDecision types provide type safety (RF-SDK-015)
- ✅ ChoreographyPlanner handles autonomous orchestration (RF-SDK-016)
- ✅ ChoreographyPlanner supports BYO LLM model (any LiteLLM-compatible provider)
- ✅ Handler-only event registration (RF-SDK-023)
- ✅ Tracker Service stores and queries progress events (RF-ARCH-010, RF-ARCH-011)
- ✅ New examples: 09-planner-basic + 10-choreography-basic
- ✅ All 451+ tests pass

**Phases:**
- ✅ **Phase 1 (Days 1-4):** PlanContext state machine + decorators
- ✅ **Phase 2 (Days 5-7):** PlannerDecision types + ChoreographyPlanner class
- ✅ **Phase 3 (Days 8-10):** Examples + Tracker Service
- ✅ **Phase 4 (Days 11-12):** Documentation + pattern selection framework

---

## Deferred Work Tracking

**Tracking Document:** [DEFERRED_WORK.md](DEFERRED_WORK.md)

Items intentionally deferred from Stage 4 for future implementation:

| Item | Reason | Target Stage | Effort |
|------|--------|--------------|--------|
| **RF-SDK-017:** EventSelector utility | Lower priority than ChoreographyPlanner | Stage 5 (Discovery) | 0.5-1 day |
| **RF-SDK-018:** EventToolkit.format_for_llm_selection() | Already exists in EventToolkit | ✅ Complete | N/A |
| **Conditional state transitions** | Simple event-based transitions sufficient for MVP | Stage 5 or 6 | 2-3 days |
| **Tracker Service UI** | FDE: Use curl/Postman for now | Post-launch | 1-2 weeks |
| **Tracker advanced query endpoints** | Core 2 endpoints sufficient for MVP | Stage 5+ | 8-12 hours |
| **Tracker NATS direct integration** | Architectural tech debt (uses EventClient) | Stage 5 (high priority) | 1-2 days |
| **11-app-research-advisor** | Full application, needs dedicated planning | Stage 5+ or post-launch | 2-3 days |

**Process:** See [DEFERRED_WORK.md](DEFERRED_WORK.md) for full documentation and requirements.

---

## Remaining Work Summary

### Current Status (February 23, 2026 - Release 0.8.0)

**Completed Stages:**
- ✅ Stage 1: Foundation - Event System (January 17, 2026)
- ✅ Stage 2: Foundation - Memory & Common DTOs (January 21, 2026)
- ✅ Stage 2.1: Memory Enhancements (January 30, 2026 - Release 0.7.5)
- ✅ Stage 3: Agent Models - Tool & Worker (February 12, 2026)
- ✅ Stage 4: Agent Models - Planner (February 23, 2026 - Release 0.8.0)

**Test Coverage:** 451+ tests passing (423 SDK + 28 Tracker)  
**Current Version:** 0.8.0  
**Examples:** 10 working examples (01-hello-world → 10-choreography-basic)

### Stage 5: Discovery & A2A (Not Started)

**Priority:** 🔴 Next Stage  
**Estimated Duration:** 2-3 weeks  
**Target Release:** 0.9.0

**Core Tasks:**

1. **Registry Service Enhancements:**
   - RF-ARCH-005: Schema registration by name (not event name)
   - RF-ARCH-006: Structured capability with EventDefinition
   - RF-ARCH-007: Discovery API for LLM reasoning
   - **Effort:** 5-7 days

2. **SDK Discovery:**
   - RF-SDK-007: Event registration tied to agent startup
   - RF-SDK-008: Agent discovery by capability (A2A pattern)
   - **Effort:** 3-4 days

3. **EventSelector Utility (Deferred from Stage 4):**
   - RF-SDK-017: EventSelector class for LLM-based event selection
   - Prompt templates, EventDecision types
   - Registry validation before publishing
   - **Effort:** 0.5-1 day (EventToolkit foundation already exists)

4. **Tracker Service NATS Integration (Tech Debt):**
   - Replace EventClient subscription with direct NATS JetStream
   - Extract shared NATS client library (libs/soorma-nats/)
   - Fix architectural violation (infrastructure services should use NATS directly)
   - **Effort:** 1-2 days
   - **Priority:** High - architectural correctness

**Deliverables:**
- Enhanced Registry Service with natural language discovery
- A2A Agent Card publication
- EventSelector for intelligent routing
- Tracker Service architectural fix
- Updated documentation
- New example: 11-tool-discovery

**Test Goals:** 500+ tests passing

---

### Stage 6: Migration & Polish (Not Started)

**Priority:** 🟡 Final Stage  
**Estimated Duration:** 1-2 weeks  
**Target Release:** 1.0.0 (Production Ready)

**Core Tasks:**

1. **Migration Guide:**
   - Create comprehensive migration guide (RF-SDK-008)
   - Before/after code examples
   - Breaking changes list
   - Migration scripts where applicable
   - **Effort:** 3-4 days

2. **User-Agent Service Documentation:**
   - RF-ARCH-002: Document HITL pattern contract
   - Service will be implemented in soorma-cloud (not soorma-core)
   - Subscribe to notification-events topic
   - Human-in-the-loop approval workflows
   - **Effort:** 1-2 days (documentation only)

3. **Documentation Audit:**
   - Update all ARCHITECTURE.md files
   - Update all README files
   - Verify all cross-references
   - Update pattern catalog
   - **Effort:** 2-3 days

4. **Final Testing & Validation:**
   - End-to-end integration tests
   - Performance testing
   - Security audit
   - Documentation review
   - **Effort:** 3-4 days

**Deliverables:**
- Comprehensive migration guide
- User-Agent contract documentation
- Updated documentation suite
- All tests passing
- Production-ready release

**Test Goals:** 550+ tests passing

---

### Post-Stage 6: Examples Development

**Priority:** 🟢 Post-Refactoring  
**Estimated Duration:** 2-3 weeks  
**Reference:** [EXAMPLES_REFACTOR_PLAN.md](../EXAMPLES_REFACTOR_PLAN.md)

**What Remains:**

1. **Phase 3: Memory Examples**
   - 04-memory-semantic (RAG pattern)
   - 05-memory-working (WorkflowState helper)
   - 06-memory-episodic (Conversation history)

2. **Phase 4: Advanced Examples**
   - 07-tool-discovery (Dynamic capability discovery)
   - 08-planner-worker-basic (Trinity pattern) - partially exists
   - 09-app-research-advisor (ChoreographyPlanner refactor) - deferred from Stage 4
   - 10-multi-turn-conversation (Stateful conversations)

3. **Phase 5: Documentation & AI Tooling**
   - `.cursorrules` for AI assistant guidance
   - Pattern catalog (`docs/PATTERNS.md`)
   - Blog post updates

**Success Criteria:**
- Developer can complete learning path in 2 hours
- Each example runs independently with `soorma dev`
- AI assistants recommend correct example for each task

---

### Technical Debt & Enhancements (Post-Launch)

**From DEFERRED_WORK.md:**

1. **Tracker Service Enhancements:**
   - Advanced query endpoints (timeline, hierarchy, metrics) - 8-12 hours
   - Web UI for plan visualization - 1-2 weeks
   - Real-time WebSocket updates - 2-3 days
   - Alerting & notifications - 2-3 days

2. **State Machine Enhancements:**
   - Conditional transitions - 2-3 days
   - Expression evaluator - 1-2 days
   - Advanced routing patterns - 2-3 days

3. **Prompt Template System (RF-SDK-019):**
   - Reusable prompt templates (Jinja2)
   - Template registry for common patterns
   - Few-shot example integration
   - **Effort:** 2-3 days

4. **Full Application Examples:**
   - 11-app-research-advisor (production-grade) - 2-3 days
   - 12-app-customer-support - TBD
   - 13-app-data-pipeline - TBD

**Priority:** Low - evaluate based on user feedback after v1.0.0 release

---

### Summary: Path to v1.0.0

**Completed:**
- ✅ Stages 1-4 (Foundation + Agent Models)
- ✅ 451+ tests passing
- ✅ 10 examples working
- ✅ v0.8.0 released

**Remaining for v1.0.0:**
1. **Stage 5 (Discovery & A2A):** 2-3 weeks → v0.9.0
2. **Stage 6 (Migration & Polish):** 1-2 weeks → v1.0.0
3. **Examples Development:** 2-3 weeks (concurrent with Stage 6)

**Total Estimated Time to v1.0.0:** 5-8 weeks

**Key Milestones:**
- v0.9.0: Discovery & A2A complete + Tracker architectural fix
- v1.0.0: Production-ready with migration guide + complete examples

---

## Stage 3 Completion Status

### Phase 2: Worker Model (RF-SDK-004) - ✅ COMPLETE (90%)

**Completion Date:** February 12, 2026

**What's Implemented:**

✅ **TaskContext Model** (863 lines, `sdk/python/soorma/task_context.py`):
- Persistent state management with `save()` / `restore()` methods
- Sequential delegation: `delegate(event_type, data, response_event, assigned_to)`
- Parallel delegation: `delegate_parallel(sub_tasks: List[DelegationSpec])` with fan-out/fan-in
- Result aggregation: `aggregate_parallel_results(group_id)` for collecting parallel results
- Sub-task tracking with automatic correlation_id and status tracking
- Explicit completion: `complete(result)` publishes result to response_event/response_topic

✅ **Worker Model** (281 lines, `sdk/python/soorma/agents/worker.py`):
- `@on_task(event_type)` decorator - async task handler receiving TaskContext
- `@on_result(event_type)` decorator - async result handler receiving ResultContext  
- Auto-subscription to action-requests (tasks) and action-results (results) topics
- Dynamic event registration - only registered events with handlers
- Assignment filtering - optional `assigned_to` field prevents unintended handling
- Programmatic execution: `execute_task(task_name, data, plan_id, goal_id)`

✅ **ResultContext Model** - Integrated into task_context.py:
- Result reception from delegated sub-tasks
- Task restoration: `restore_task()` queries memory service
- Success/failure detection and error tracking
- Enables result aggregation across async boundaries

✅ **Example Implementation** (`examples/08-worker-basic/subscriber.py`):
- Order processing workflow with inventory + payment delegation
- Sequential delegation pattern - main task saves state before delegating
- Parallel delegation pattern - inventory + payment processed in parallel
- Result aggregation - both results collected via `aggregate_parallel_results()`
- Demonstrates real-world async choreography patterns

✅ **Test Suite** (test_worker_phase3.py):
- `test_task_context_save_calls_memory()` - persistence validation
- `test_task_context_delegate_publishes_request()` - sequential delegation
- `test_result_context_restore_task()` - task restoration
- `test_worker_on_task_wrapper_passes_task_context()` - task decorator
- `test_worker_on_result_wrapper_passes_result_context()` - result decorator
- **Status:** 5 core tests passing (25% of ideal coverage, expansion planned)

✅ **Infrastructure Work** (February 12, 2026):
- Migration 006: Added `user_id` FK to task_context with CASCADE delete
- Migration 007: Converted `plan_context.plan_id` String→UUID with FK, fixed revision ID length
- WorkingMemory: Added `user_id` FK with CASCADE delete for plan state isolation
- All 126 Memory Service tests passing ✅
- All 254 SDK tests passing ✅

**What Needs Expansion:**

🟡 **Test Coverage** - Currently 5 core tests, recommend 20+ tests:
- Parallel delegation aggregation scenarios
- Error handling (failed sub-tasks, timeouts)
- Assignment filtering validation
- Multi-handler scenarios
- State persistence across complex workflows

🟡 **Documentation** - Inline docs present, needs integration:
- ARCHITECTURE.md section on Worker model
- Migration guide from Tool-only to Tool+Worker
- Pattern documentation with diagrams
- Error handling best practices

**Key Features Validated:**

- ✅ Sequential delegation with state persistence
- ✅ Parallel delegation with fan-out/fan-in aggregation
- ✅ Async completion across event boundaries
- ✅ Sub-task tracking with correlation IDs
- ✅ Memory Service integration for state persistence
- ✅ Auto-subscription to action-requests/action-results topics
- ✅ Handler-only event registration pattern
- ✅ Production-ready core functionality

**Reference:** [STAGE_3_WORKING_PLAN.md](STAGE_3_WORKING_PLAN.md) - Complete implementation details

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
| RF-ARCH-012 | Semantic memory upsert (external_id + content_hash) | Stage 2.1 | [SEMANTIC_MEMORY_UPSERT](../../services/memory/SEMANTIC_MEMORY_UPSERT.md) | ✅ |
| RF-ARCH-013 | Working memory deletion (DELETE endpoints) | Stage 2.1 | [02-MEMORY-SERVICE](arch/02-MEMORY-SERVICE.md) | ✅ |
| RF-ARCH-014 | Semantic memory privacy (user_id + is_public) | Stage 2.1 | [02-MEMORY-SERVICE](arch/02-MEMORY-SERVICE.md) | ✅ |
| RF-SDK-019 | Semantic memory upsert SDK (external_id parameter) | Stage 2.1 | [02-MEMORY-SDK](sdk/02-MEMORY-SDK.md) | ✅ |
| RF-SDK-020 | Working memory deletion SDK (delete methods) | Stage 2.1 | [02-MEMORY-SDK](sdk/02-MEMORY-SDK.md) | ✅ |
| RF-SDK-021 | Semantic memory privacy SDK (user_id + is_public) | Stage 2.1 | [02-MEMORY-SDK](sdk/02-MEMORY-SDK.md) | ✅ |
| RF-SDK-005 | Tool synchronous model simplify | Stage 3 | [04-TOOL-MODEL](sdk/04-TOOL-MODEL.md) | ✅ |
| RF-SDK-004 | Worker async task model | Stage 3 | [05-WORKER-MODEL](sdk/05-WORKER-MODEL.md) | ✅ |
| RF-SDK-022 | Worker handler-only event registration | Stage 3 | [05-WORKER-MODEL](sdk/05-WORKER-MODEL.md) | ✅ |
| RF-SDK-006 | Planner on_goal and on_transition | Stage 4 | [06-PLANNER-MODEL](sdk/06-PLANNER-MODEL.md) | ✅ |
| RF-SDK-015 | PlannerDecision and PlanAction types | Stage 4 | [06-PLANNER-MODEL](sdk/06-PLANNER-MODEL.md) | ✅ |
| RF-SDK-016 | ChoreographyPlanner class | Stage 4 | [06-PLANNER-MODEL](sdk/06-PLANNER-MODEL.md) | ✅ |
| RF-SDK-023 | Planner handler-only event registration | Stage 4 | [06-PLANNER-MODEL](sdk/06-PLANNER-MODEL.md) | ✅ |
| RF-ARCH-010 | Tracker as event listener | Stage 4 | [04-TRACKER-SERVICE](arch/04-TRACKER-SERVICE.md) | ✅ |
| RF-ARCH-011 | Task progress model | Stage 4 | [04-TRACKER-SERVICE](arch/04-TRACKER-SERVICE.md) | ✅ |
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
- [Agent Patterns](../docs/agent_patterns/README.md) - Tool, Worker, Planner models
- [Event System](../docs/event_system/README.md) - Event-driven architecture and topics
- [Memory System](../docs/memory_system/README.md) - CoALA framework
- [Memory Service ARCHITECTURE.md](../../services/memory/ARCHITECTURE.md) - Memory service design
- [EXAMPLES_REFACTOR_PLAN.md](../EXAMPLES_REFACTOR_PLAN.md) - Progressive examples roadmap
