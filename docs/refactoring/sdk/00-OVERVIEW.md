# SDK Refactoring: Overview & Vision

**Document:** 00-OVERVIEW.md  
**Status:** 📋 Reference  
**Last Updated:** January 11, 2026

---

## Purpose

This document provides the foundational context for SDK refactoring:
- Current SDK structure and issues
- Agent progression model (Layer 1-4)
- Design rationale for structured/discoverable patterns

This is a **reference document** - no implementation tasks here.

---

## 1. Current SDK Structure

```
sdk/python/soorma/
├── agents/
│   ├── base.py      # Agent class - foundation
│   ├── planner.py   # Planner class - goal decomposition
│   ├── worker.py    # Worker class - task execution
│   └── tool.py      # Tool class - synchronous utilities
├── context.py       # PlatformContext (registry, memory, bus, tracker)
├── events.py        # EventClient (SSE streaming, publish)
├── models.py        # Re-exports from soorma-common
├── memory/          # Memory service client
├── registry/        # Registry service client  
└── ai/              # AI integration (EventToolkit)
```

---

## 2. Issues Identified

| Issue | Current Behavior | Impact | Priority |
|-------|-----------------|--------|----------|
| Topic inference | `BusClient._infer_topic()` guesses topic from event name | Implicit behavior, error-prone | 🔴 High |
| Synchronous task execution | `worker.on_task()` expects handler to return result (blocking) | Breaks async choreography pattern | 🔴 High |
| Event namespacing | Events are flat, not tied to agents | No ownership, hard to cleanup | 🟡 Medium |
| Tracker API calls | Workers call tracker service API directly | Should publish events instead | 🟡 Medium |
| Missing TaskContext persistence | Task context not saved to memory for async completion | Can't resume after delegation | 🔴 High |
| Response event specification | No way to specify which event to use for action results | Tight coupling, no dynamic routing | 🔴 High |

---

## 3. Agent Progression Model

### 3.1 Vision: Progressive Abstraction Layers

```
┌─────────────────────────────────────────────────────────────────┐
│  Layer 4: Autonomous Agents (Planner with LLM reasoning)        │
│  - planner.on_goal(), planner.on_transition()                   │
│  - Dynamic capability discovery, plan generation                │
├─────────────────────────────────────────────────────────────────┤
│  Layer 3: Async Task Agents (Worker)                            │
│  - worker.on_task(), worker.on_result()                         │
│  - Task decomposition, sub-agent delegation                     │
├─────────────────────────────────────────────────────────────────┤
│  Layer 2: Sync Tool Agents (Tool)                               │
│  - tool.on_invoke()                                             │
│  - Atomic, stateless operations                                 │
├─────────────────────────────────────────────────────────────────┤
│  Layer 1: Base Agent (Primitive)                                │
│  - agent.on_event(topic, event_type)                            │
│  - Generic event handler, no assumptions                        │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Key Principles

1. **Progressive complexity** - Simple → Structured → Discoverable → Autonomous
2. **Explicit over implicit** - No magic topic inference, clear contracts
3. **Asynchronous-first** - Event-driven, non-blocking by default
4. **Industry standards** - A2A Agent Card, CloudEvents where applicable
5. **TDD approach** - Tests define behavior before implementation
6. **Schema ownership** - Result publisher owns schema, requestor specifies event name
7. **Common library for DTOs** - `soorma-common` owns shared models

---

## 4. Design Rationale: Why Structured/Discoverable Patterns?

Our SDK supports three levels of event definition complexity:

| Level | Pattern | Event Definition | Payload Handling |
|-------|---------|------------------|------------------|
| **Simple** | String names | `"order.placed"` | Caller knows schema at compile time |
| **Structured** | EventDefinition | `EventDefinition(name=..., schema=...)` | Schema registered, validated |
| **Discoverable** | Capability-based | `AgentCapability(consumed_event=..., produced_events=...)` | LLM discovers and generates payloads |

### Why not just use Simple (string names)?

In the request/response pattern, callers need to construct payloads. Two options:

1. **Compile-time knowledge (tight coupling):**
   - Caller hardcodes the payload structure
   - Works for internal, well-known integrations
   - Breaks when producer changes schema

2. **LLM-based dynamic generation:**
   - LLM generates payloads based on registered EventDefinition schemas
   - LLM parses responses based on registered schemas
   - Enables loose coupling and runtime discovery

### Why explicit schemas even with LLMs?

While LLMs can reason about payload structures, explicit schemas provide:

| Benefit | Without Schema | With Schema |
|---------|---------------|-------------|
| **Consistency** | LLM may vary structure | Guaranteed structure |
| **Predictability** | Output varies per invocation | Reproducible results |
| **Debuggability** | "LLM generated something wrong" | "Field X doesn't match type Y" |
| **Validation** | Hope it works | Fail fast on schema mismatch |
| **Documentation** | Read the agent's code | Browse registry for contracts |

### Recommendation

Start simple, graduate to structured/discoverable as needs grow:

1. **Simple:** Prototyping, internal tools, known contracts
2. **Structured:** Production services, cross-team integration
3. **Discoverable:** Multi-agent orchestration, LLM-driven workflows

---

## 5. Decorator Contracts Summary

| Layer | Agent Type | Decorator | Topic | Behavior |
|-------|-----------|-----------|-------|----------|
| 1 | `Agent` | `@agent.on_event(topic, event_type)` | Explicit | Raw event handling |
| 2 | `Tool` | `@tool.on_invoke(event_type)` | action-requests | Request/response, auto-publish |
| 3 | `Worker` | `@worker.on_task()` / `@worker.on_result()` | action-requests/results | Async delegation |
| 4 | `Planner` | `@planner.on_goal()` / `@planner.on_transition()` | action-requests/results | State machine |

---

## Next Steps

See [README.md](README.md) for full implementation order. Start with **Phase 1 (Foundation)** - these have no dependencies and can be worked on in parallel:

1. [01-EVENT-SYSTEM.md](01-EVENT-SYSTEM.md) - BusClient, topics, convenience methods
2. [02-MEMORY-SDK.md](02-MEMORY-SDK.md) - Task/plan context persistence
3. [03-COMMON-DTOS.md](03-COMMON-DTOS.md) - Common DTOs, system events

After Phase 1, proceed to **Phase 2 (Agent Types)**:

4. [04-TOOL-MODEL.md](04-TOOL-MODEL.md) - Synchronous tool pattern (needs: 01)
5. [05-WORKER-MODEL.md](05-WORKER-MODEL.md) - Async task handling (needs: 01, 02)
6. [06-PLANNER-MODEL.md](06-PLANNER-MODEL.md) - State machine (needs: 01, 02, 03)
