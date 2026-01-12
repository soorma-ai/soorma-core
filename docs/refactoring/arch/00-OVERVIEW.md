# Architecture Refactoring: Overview

**Document:** 00-OVERVIEW.md  
**Status:** 📋 Reference  
**Last Updated:** January 11, 2026

---

## Purpose

This document provides foundational context for architecture refactoring:
- Service responsibilities and boundaries
- Event-driven communication patterns
- Industry standards alignment
- Design principles

This is a **reference document** - no implementation tasks here.

---

## 1. Service Responsibilities Map

### Current Service Map

| Service | Current Role | Issues |
|---------|--------------|--------|
| **Registry** | Agent & event registration, discovery | Events not tied to agents |
| **Event Service** | Pub/sub backbone (NATS proxy) | Works well |
| **Memory** | CoALA memory (semantic, episodic, procedural, working) | Good foundation |
| **Tracker** | (Planned) Observability, state machine tracking | Not implemented |
| **Gateway** | (Planned) API gateway, auth | Not implemented |

### Target Service Responsibilities

```
┌─────────────────────────────────────────────────────────────────┐
│                        External Clients                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Gateway Service                              │
│  - Authentication / Authorization                                │
│  - Rate limiting                                                 │
│  - Request routing                                               │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│   Registry    │    │ Event Service │    │    Memory     │
│  - Agents     │    │  - Pub/Sub    │    │  - Semantic   │
│  - Events     │    │  - SSE        │    │  - Episodic   │
│  - Discovery  │    │  - JetStream  │    │  - Procedural │
└───────────────┘    └───────────────┘    │  - Working    │
                              │           └───────────────┘
                              │
                     ┌────────┴────────┐
                     ▼                 ▼
              ┌───────────┐     ┌───────────┐
              │  Tracker  │     │ User-Agent│
              │ (Passive) │     │  (HITL)   │
              └───────────┘     └───────────┘
```

---

## 2. Key Design Principles

1. **Event-driven architecture** - Agents communicate via events, not API calls
2. **Services are passive listeners** - Consume events, update state
3. **Clear separation of concerns** - Each service owns specific domain
4. **Progressive disclosure** - Simple → Discoverable → Autonomous
5. **Industry standards** - A2A Agent Card, CloudEvents where applicable
6. **Tests first (TDD)** - Define behavior with tests before implementation
7. **Explicit over implicit** - No magic inference, clear contracts

---

## 3. Topic Structure

Current topics defined in `soorma-common`:

| Topic | Purpose | Example Events |
|-------|---------|----------------|
| `action-requests` | Agent-to-agent task delegation, user goals | `research.goal`, `calculate.requested` |
| `action-results` | Task completion responses | `research.completed`, `calculate.done` |
| `business-facts` | Domain events / public announcements | `order.placed`, `inventory.low` |
| `notification-events` | User notifications, HITL requests | `notification.human_input` |
| `system-events` | Platform lifecycle, observability | `task.progress`, `plan.started` |
| `billing` | Billing events | `usage.recorded` |
| `audit-events` | Audit trail | `access.granted` |

### Topic Usage Guidelines

**RF-ARCH-001: business-facts vs action-requests**

| Topic | Purpose | Who publishes? | Who subscribes? |
|-------|---------|----------------|-----------------|
| `business-facts` | Public service announcements, domain observations | Any service announcing a fact | Any interested party |
| `action-requests` | Work delegation (including user goals) | Requestors, users, planners | Workers, tools, planners |

**Key Decision:** User goals go to `action-requests`, not `business-facts`. Business-facts is purely for announcing facts that any interested party can react to.

---

## 4. Service Communication Patterns

### 4.1 Request/Response Pattern (DisCo)

**Key Innovation:** Caller specifies response event name (not publisher)

```
Requestor                                  Worker
    │                                         │
    │ action-requests                         │
    │ event: calculate.requested              │
    │ response_event: my.calculation.done     │
    │────────────────────────────────────────>│
    │                                         │
    │                    action-results       │
    │          event: my.calculation.done     │
    │<────────────────────────────────────────│
```

**Why:** Enables dynamic routing, loose coupling, multiple concurrent requests.

### 4.2 Passive Service Pattern

**Tracker, User-Agent** are passive event listeners:
- Do NOT expose write APIs
- Subscribe to topics (system-events, notification-events)
- Update internal state based on events
- Expose read-only query APIs

### 4.3 Event Envelope Structure

See [01-EVENT-SERVICE.md](01-EVENT-SERVICE.md) for detailed envelope structure with:
- `response_event` - Caller-specified response routing
- `trace_id` - Root trace for distributed tracing
- `correlation_id` - Response routing identifier
- `parent_event_id` - Immediate parent for trace tree

---

## 5. Industry Standards Alignment

### A2A (Agent-to-Agent) Protocol
Reference: [Google A2A](https://google.github.io/agent-to-agent/)

**Relevant Concepts:**
- **Agent Card** - Agent discovery metadata (align with AgentDefinition)
- **Task** - Unit of work (align with TaskContext)
- **Artifact** - Intermediate/final outputs

**See:** [05-REGISTRY-SERVICE.md](05-REGISTRY-SERVICE.md) for A2A alignment details.

### MCP (Model Context Protocol)
Reference: [Anthropic MCP](https://github.com/anthropics/model-context-protocol)

**Relevant Concepts:**
- Tool definitions with JSON Schema
- Resource abstraction

**See:** SDK [04-TOOL-MODEL.md](../sdk/04-TOOL-MODEL.md) for MCP alignment.

---

## 6. Implementation Philosophy

### TDD Approach
1. **Read existing code first** - Understand what exists
2. **Write tests that define behavior**:
   - Add/modify tests to specify expected behavior
   - Run tests to see them fail
   - Implement the change
   - Run tests to see them pass
3. **Iterate** - Refine based on test feedback

### Common Library Strategy

**`soorma-common` owns shared DTOs:**
- Services import from `soorma-common`
- SDK re-exports from `soorma-common`
- Single source of truth for contracts

**See:** [03-COMMON-LIBRARY.md](03-COMMON-LIBRARY.md) for DTO ownership.

---

## 7. Service ↔ SDK Coordination

Architecture changes must be coordinated with SDK changes:

| ARCH Document | Pairs With SDK | Coordination |
|---------------|----------------|--------------|
| [01-EVENT-SERVICE.md](01-EVENT-SERVICE.md) | [sdk/01-EVENT-SYSTEM.md](../sdk/01-EVENT-SYSTEM.md) | Event envelope, BusClient |
| [02-MEMORY-SERVICE.md](02-MEMORY-SERVICE.md) | [sdk/02-MEMORY-SDK.md](../sdk/02-MEMORY-SDK.md) | Task/plan context APIs |
| [03-COMMON-LIBRARY.md](03-COMMON-LIBRARY.md) | [sdk/03-COMMON-DTOS.md](../sdk/03-COMMON-DTOS.md) | Shared DTOs |
| [04-TRACKER-SERVICE.md](04-TRACKER-SERVICE.md) | [sdk/03-COMMON-DTOS.md](../sdk/03-COMMON-DTOS.md) | Progress events |
| [05-REGISTRY-SERVICE.md](05-REGISTRY-SERVICE.md) | [sdk/07-DISCOVERY.md](../sdk/07-DISCOVERY.md) | Discovery, capabilities |

**Rule:** Service changes → SDK changes → Examples updated → Deploy together

---

## Next Steps

See [README.md](README.md) for full implementation order. Architecture documents are numbered to align with SDK dependencies:

**Phase 1 (Foundation):**
1. [01-EVENT-SERVICE.md](01-EVENT-SERVICE.md) - Event envelope enhancements
2. [02-MEMORY-SERVICE.md](02-MEMORY-SERVICE.md) - Task/plan context storage
3. [03-COMMON-LIBRARY.md](03-COMMON-LIBRARY.md) - Shared DTOs

**Phase 2 (Observability):**
4. [04-TRACKER-SERVICE.md](04-TRACKER-SERVICE.md) - Event-driven tracking

**Phase 3 (Discovery):**
5. [05-REGISTRY-SERVICE.md](05-REGISTRY-SERVICE.md) - Enhanced discovery

**Phase 4 (User Experience):**
6. [06-USER-AGENT.md](06-USER-AGENT.md) - HITL pattern

---

## Related Documentation

- [../sdk/00-OVERVIEW.md](../sdk/00-OVERVIEW.md) - SDK refactoring overview
- [../../ARCHITECTURE.md](../../ARCHITECTURE.md) - Current platform architecture
- [../../DESIGN_PATTERNS.md](../../DESIGN_PATTERNS.md) - Agent design patterns
- [../../EVENT_PATTERNS.md](../../EVENT_PATTERNS.md) - Event-driven patterns
- [../../TOPICS.md](../../TOPICS.md) - Topic definitions
