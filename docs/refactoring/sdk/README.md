# SDK Refactoring Documentation

**Status:** 📋 Active Planning  
**Last Updated:** January 11, 2026

---

## Overview

This directory contains focused, modular documentation for SDK refactoring tasks. Each document is **self-contained** and covers a logical chunk that can be implemented independently in a separate Copilot session.

### How to Use These Documents

1. **Start with any document** - Each has full context needed for implementation
2. **Follow dependency order** - Some documents must complete before others
3. **One session per document** - Each document is scoped for focused work
4. **TDD approach** - Write tests first, then implement

---

## Document Catalog

| # | Document | Focus | Tasks | Depends On |
|---|----------|-------|-------|------------|
| 0 | [00-OVERVIEW.md](00-OVERVIEW.md) | Vision, principles, current state | — | — |
| 1 | [01-EVENT-SYSTEM.md](01-EVENT-SYSTEM.md) | Topics, publish, on_event, convenience methods | RF-SDK-001, 002, 003 | — |
| 2 | [02-MEMORY-SDK.md](02-MEMORY-SDK.md) | Task/plan context, sessions, plans | RF-SDK-010 | — |
| 3 | [03-COMMON-DTOS.md](03-COMMON-DTOS.md) | System events, soorma-common DTOs | RF-SDK-011, 012 | — |
| 4 | [04-TOOL-MODEL.md](04-TOOL-MODEL.md) | InvocationContext, on_invoke, sync pattern | RF-SDK-005 | 01 |
| 5 | [05-WORKER-MODEL.md](05-WORKER-MODEL.md) | TaskContext, delegation, async completion | RF-SDK-004 | 01, 02 |
| 6 | [06-PLANNER-MODEL.md](06-PLANNER-MODEL.md) | PlanContext, state machine, pause/resume | RF-SDK-006 | 01, 02, 03 |
| 7 | [07-DISCOVERY.md](07-DISCOVERY.md) | Event ownership, RegistryClient, A2A Gateway | RF-SDK-007, 008 | 01, 03 |
| 8 | [08-MIGRATION.md](08-MIGRATION.md) | Breaking changes, migration patterns | — | All |

---

## Implementation Order (Dependency-Based)

```
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 1: FOUNDATION (No Dependencies - Start Here)            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   01-EVENT-SYSTEM     02-MEMORY-SDK      03-COMMON-DTOS        │
│   (BusClient,         (MemoryClient,     (Common DTOs,         │
│    topics,            task/plan          StateConfig,          │
│    convenience)       context)           A2A models)           │
│         │                  │                   │               │
│         └────────┬─────────┴───────────────────┘               │
│                  ▼                                              │
├─────────────────────────────────────────────────────────────────┤
│  PHASE 2: AGENT TYPES (Depends on Phase 1)                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   04-TOOL-MODEL       05-WORKER-MODEL     06-PLANNER-MODEL     │
│   (Sync pattern,      (Async pattern,     (State machine,      │
│    on_invoke)         TaskContext,        on_goal,             │
│                       delegation)         on_transition)       │
│   Needs: 01           Needs: 01, 02       Needs: 01, 02, 03    │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  PHASE 3: DISCOVERY & INTEGRATION                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   07-DISCOVERY                                                  │
│   (Event ownership, agent discovery, A2A Gateway)              │
│   Needs: 01, 03                                                 │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  PHASE 4: MIGRATION (After All Implementation)                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   08-MIGRATION                                                  │
│   (Breaking changes, migration guide for examples/tests)       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Recommended Sequence

**Can start in parallel (no dependencies):**
1. `01-EVENT-SYSTEM.md` - Event publishing foundation
2. `02-MEMORY-SDK.md` - Memory service client  
3. `03-COMMON-DTOS.md` - Common library DTOs

**After Event System:**
4. `04-TOOL-MODEL.md` - Synchronous tool pattern

**After Event System + Memory SDK:**
5. `05-WORKER-MODEL.md` - Async worker model

**After Event System + Memory SDK + Common DTOs:**
6. `06-PLANNER-MODEL.md` - Planner state machine

**After Event System + Common DTOs:**
7. `07-DISCOVERY.md` - Agent/event discovery, A2A

**After all implementation:**
8. `08-MIGRATION.md` - Update examples and tests

---

## Task Reference

| Task ID | Description | Document | Priority | Status |
|---------|-------------|----------|----------|--------|
| RF-SDK-001 | Remove topic inference from BusClient | [01-EVENT-SYSTEM](01-EVENT-SYSTEM.md) | 🔴 High | ⬜ |
| RF-SDK-002 | Add response_event to action requests | [01-EVENT-SYSTEM](01-EVENT-SYSTEM.md) | 🔴 High | ⬜ |
| RF-SDK-003 | Refactor on_event() signature | [01-EVENT-SYSTEM](01-EVENT-SYSTEM.md) | 🔴 High | ⬜ |
| RF-SDK-010 | Memory SDK methods | [02-MEMORY-SDK](02-MEMORY-SDK.md) | 🔴 High | ⬜ |
| RF-SDK-011 | Tracker via events | [03-COMMON-DTOS](03-COMMON-DTOS.md) | 🔴 High | ⬜ |
| RF-SDK-012 | Common library DTOs | [03-COMMON-DTOS](03-COMMON-DTOS.md) | 🔴 High | ⬜ |
| RF-SDK-005 | Tool synchronous model | [04-TOOL-MODEL](04-TOOL-MODEL.md) | 🟡 Medium | ⬜ |
| RF-SDK-004 | Worker async task model | [05-WORKER-MODEL](05-WORKER-MODEL.md) | 🟡 Medium | ⬜ |
| RF-SDK-006 | Planner on_goal and on_transition | [06-PLANNER-MODEL](06-PLANNER-MODEL.md) | 🟡 Medium | ⬜ |
| RF-SDK-007 | Event registration tied to agent | [07-DISCOVERY](07-DISCOVERY.md) | 🟡 Medium | ⬜ |
| RF-SDK-008 | Agent discovery by capability (A2A) | [07-DISCOVERY](07-DISCOVERY.md) | 🟡 Medium | ⬜ |

---

## Key Design Principles

1. **Progressive complexity** - Simple → Structured → Discoverable → Autonomous
2. **Explicit over implicit** - No magic topic inference
3. **TDD approach** - Tests define behavior before implementation
4. **Schema ownership** - Result publisher owns schema, requestor specifies event name
5. **Industry standards** - A2A Agent Card, CloudEvents where applicable

---

## Starting a New Copilot Session

Each document is designed to be self-contained. When starting a new session:

1. **Reference the specific document** - e.g., "I'm working on 01-EVENT-SYSTEM.md"
2. **Document includes:**
   - Summary and scope
   - Current state analysis
   - Target design with code
   - Tests to add (TDD)
   - Implementation checklist
   - Dependencies and blockers

3. **Context files to include:**
   - The specific document (e.g., `01-EVENT-SYSTEM.md`)
   - `00-OVERVIEW.md` for background (optional but helpful)
   - Relevant SDK source files mentioned in the document

---

## Related Documentation

- [00-OVERVIEW.md](00-OVERVIEW.md) - Design rationale and agent progression model
- [../ARCHITECTURE_REFACTORING_PLAN.md](../ARCHITECTURE_REFACTORING_PLAN.md) - Service architecture
- [../../ARCHITECTURE.md](../../ARCHITECTURE.md) - Platform architecture
- [../archive/SDK_REFACTORING_PLAN.md](../archive/SDK_REFACTORING_PLAN.md) - Original consolidated document (archived)
