# Architecture Refactoring Documents

**Status:** 📋 Active Planning  
**Last Updated:** January 11, 2026

---

## Overview

This directory contains focused architecture refactoring documents for Soorma platform services. These documents are numbered to align with SDK dependencies and must be coordinated with corresponding SDK changes.

**Guiding Principles:**
1. **Event-driven architecture** - Services communicate via events
2. **Services are passive listeners** - Consume events, expose read APIs
3. **Coordinate with SDK** - Service changes paired with SDK changes
4. **TDD approach** - Tests define behavior before implementation

---

## Documents

### Foundation (Phase 1)

| Document | Focus | Pairs With SDK | Priority | Status |
|----------|-------|----------------|----------|--------|
| [00-OVERVIEW.md](00-OVERVIEW.md) | Service map, principles | Reference | 📋 Reference | 📋 |
| [01-EVENT-SERVICE.md](01-EVENT-SERVICE.md) | Event envelope (response_event, trace_id) | [sdk/01-EVENT-SYSTEM](../sdk/01-EVENT-SYSTEM.md) | 🔴 High | ⬜ |
| [02-MEMORY-SERVICE.md](02-MEMORY-SERVICE.md) | Task/plan context storage | [sdk/02-MEMORY-SDK](../sdk/02-MEMORY-SDK.md) | 🔴 High | ⬜ |
| [03-COMMON-LIBRARY.md](03-COMMON-LIBRARY.md) | Shared DTOs (state, A2A, tracking) | [sdk/03-COMMON-DTOS](../sdk/03-COMMON-DTOS.md) | 🔴 High | ⬜ |

### Observability (Phase 2)

| Document | Focus | Pairs With SDK | Priority | Status |
|----------|-------|----------------|----------|--------|
| [04-TRACKER-SERVICE.md](04-TRACKER-SERVICE.md) | Event-driven observability | [sdk/03-COMMON-DTOS](../sdk/03-COMMON-DTOS.md) | 🟡 Medium | ⬜ |

### Discovery (Phase 3)

| Document | Focus | Pairs With SDK | Priority | Status |
|----------|-------|----------------|----------|--------|
| [05-REGISTRY-SERVICE.md](05-REGISTRY-SERVICE.md) | Enhanced discovery, A2A | [sdk/07-DISCOVERY](../sdk/07-DISCOVERY.md) | 🟡 Medium | ⬜ |

### User Experience (Phase 4)

| Document | Focus | Pairs With SDK | Priority | Status |
|----------|-------|----------------|----------|--------|
| [06-USER-AGENT.md](06-USER-AGENT.md) | HITL pattern, UI gateway | N/A | 🟢 Low | ⬜ |

---

## Implementation Coordination

### Critical: Service + SDK Must Be Updated Together

Each architecture document **pairs with** a corresponding SDK document. Changes must be coordinated:

| Phase | Service Work | SDK Work | Coordination |
|-------|--------------|----------|--------------|
| **Phase 1** | Update Event Service envelope | Update BusClient publish signature | Deploy together |
| **Phase 1** | Add Memory Service endpoints | Add MemoryClient methods | Deploy service first |
| **Phase 1** | Create common library DTOs | SDK re-exports | Library first |
| **Phase 2** | Implement Tracker Service | Remove direct tracker API calls | Service first, then SDK |
| **Phase 3** | Enhance Registry discovery | Add RegistryClient.discover() | Deploy together |

**Implementation Pattern:**
1. Service changes (add endpoints, update schemas)
2. SDK changes (update client methods)
3. Update examples to use new patterns
4. Deploy service → Deploy SDK → Update examples

---

## Task Index

### High Priority

| ID | Description | Document | Pairs With SDK |
|----|-------------|----------|----------------|
| RF-ARCH-003 | Response event in envelope | [01-EVENT-SERVICE](01-EVENT-SERVICE.md) | RF-SDK-001, 002 |
| RF-ARCH-004 | Correlation ID semantics | [01-EVENT-SERVICE](01-EVENT-SERVICE.md) | RF-SDK-001, 002 |
| RF-ARCH-008 | TaskContext memory type | [02-MEMORY-SERVICE](02-MEMORY-SERVICE.md) | RF-SDK-010 |
| RF-ARCH-009 | Plan/session query APIs | [02-MEMORY-SERVICE](02-MEMORY-SERVICE.md) | RF-SDK-010 |

### Medium Priority

| ID | Description | Document | Pairs With SDK |
|----|-------------|----------|----------------|
| RF-ARCH-010 | Tracker as event listener | [04-TRACKER-SERVICE](04-TRACKER-SERVICE.md) | RF-SDK-011 |
| RF-ARCH-011 | Task progress model | [04-TRACKER-SERVICE](04-TRACKER-SERVICE.md) | RF-SDK-011 |
| RF-ARCH-005 | Events tied to agents | [05-REGISTRY-SERVICE](05-REGISTRY-SERVICE.md) | RF-SDK-007 |
| RF-ARCH-006 | Structured capabilities | [05-REGISTRY-SERVICE](05-REGISTRY-SERVICE.md) | RF-SDK-007 |
| RF-ARCH-007 | Enhanced discovery API | [05-REGISTRY-SERVICE](05-REGISTRY-SERVICE.md) | RF-SDK-008 |

### Lower Priority

| ID | Description | Document | Pairs With SDK |
|----|-------------|----------|----------------|
| RF-ARCH-001 | Clarify business-facts purpose | [00-OVERVIEW](00-OVERVIEW.md) | N/A |
| RF-ARCH-002 | HITL pattern | [06-USER-AGENT](06-USER-AGENT.md) | N/A |

---

## Coordination Matrix

Visual map of which service and SDK documents must be implemented together:

```
Service                           SDK
────────────────────────────────────────────────────────────
01-EVENT-SERVICE          ←→     01-EVENT-SYSTEM
  (RF-ARCH-003, 004)              (RF-SDK-001, 002, 003)

02-MEMORY-SERVICE         ←→     02-MEMORY-SDK
  (RF-ARCH-008, 009)              (RF-SDK-010)

03-COMMON-LIBRARY         ←→     03-COMMON-DTOS
  (Shared DTOs)                   (RF-SDK-011, 012)

04-TRACKER-SERVICE        ←→     03-COMMON-DTOS
  (RF-ARCH-010, 011)              (Event publishing)

05-REGISTRY-SERVICE       ←→     07-DISCOVERY
  (RF-ARCH-005, 006, 007)         (RF-SDK-007, 008)

06-USER-AGENT             ←→     (Standalone)
  (RF-ARCH-002)
```

---

## Next Steps

1. **Phase 1 (Foundation)** - Start with these (no dependencies):
   - Service: Update EventEnvelope in soorma-common
   - SDK: Update BusClient signature
   - Service: Add Memory Service endpoints
   - SDK: Add MemoryClient methods
   - Both: Create common library DTOs

2. **Phase 2 (Observability)** - After Phase 1:
   - Implement Tracker Service
   - Update SDK to publish events instead of API calls

3. **Phase 3 (Discovery)** - After Phase 1:
   - Enhance Registry Service
   - Update SDK discovery methods

4. **Phase 4 (User Experience)** - After Phase 1:
   - Implement User-Agent Service for HITL

---

## Related Documentation

- [../sdk/README.md](../sdk/README.md) - SDK refactoring index
- [../README.md](../README.md) - Overall refactoring index
- [../../ARCHITECTURE.md](../../ARCHITECTURE.md) - Current platform architecture
- [../../docs/event_system/README.md](../../docs/event_system/README.md) - Event system and topics
