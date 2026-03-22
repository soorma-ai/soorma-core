# Unit of Work — Dependency Matrix
## Initiative: Multi-Tenancy Model Implementation
**Date**: 2026-03-22

---

## Dependency Matrix

| Unit | Component | Wave | Depends On | Unblocks | Integration Test With |
|---|---|---|---|---|---|
| U1 | `libs/soorma-common` | 1 | — | U2, U3, U4, U5, U6, U7 | — (unit tests only) |
| U2 | `libs/soorma-service-common` | 2 | U1 | U4, U5, U7 | U1 |
| U3 | `services/registry` | 2 | U1 | — | U1, U2 |
| U4 | `services/memory` | 3 | U1, U2 | U6 | U1, U2 |
| U5 | `services/tracker` | 3 | U1, U2 | U6 | U1, U2 |
| U7 | `services/event-service` | 3 | U1, U2 | — | U1, U2 |
| U6 | `sdk/python` | 4 | U4, U5 | — | U4, U5 |

---

## Parallelization Schedule

### Wave 1
```
U1 — libs/soorma-common
```
- Must complete before any other unit begins
- Deliverable: `DEFAULT_PLATFORM_TENANT_ID` constant; `EventEnvelope.platform_tenant_id` field

### Wave 2 (after Wave 1)
```
U2 — libs/soorma-service-common     (independent of U3)
U3 — services/registry              (independent of U2)
```
- U2 and U3 have no dependency on each other
- U3 depends on U2 for `TenancyMiddleware` + `get_platform_tenant_id` — but U3 can be *developed* in parallel; it simply cannot be *tested* with U2 until U2 is complete
- Recommended sequence if one developer: U2 → U3 (U2 first, then U3 tests can include U2 integration)

### Wave 3 (after Wave 1 + Wave 2)
```
U4 — services/memory          (independent of U3, U5, U7)
U5 — services/tracker         (independent of U3, U4, U7)
U7 — services/event-service   (independent of U3, U4, U5)
```
- All three depend on U1 + U2 only; no dependency among themselves
- Recommended sequence if one developer: U4 → U5 → U7 (memory first as largest unit)

### Wave 4 (after Wave 3, specifically U4 + U5)
```
U6 — sdk/python
```
- Depends on U4 + U5 API surfaces being stable
- U7 does NOT need to complete before U6 (event-service is not called by SDK clients directly)

---

## Critical Path

```
U1  →  U2  →  U4  →  U6
```
The critical path through the longest chain. U2 (new library) and U4 (memory service — largest unit) are the highest-risk units and should be prioritised.

---

## Dependency Graph

```
libs/soorma-common (U1)
        │
        ├──────────────────────────────────────────┐
        │                                          │
libs/soorma-service-common (U2)          services/registry (U3)
        │
        ├──────────────────────┬──────────────────────┐
        │                      │                      │
services/memory (U4)  services/tracker (U5)  services/event-service (U7)
        │                      │
        └──────────────────────┘
                    │
              sdk/python (U6)
```

---

## Build Gate Rules

| Gate | Condition |
|---|---|
| Start U2 | U1 complete and tested |
| Start U3 | U1 complete and tested |
| Full test U3 | U2 complete (integration with TenancyMiddleware) |
| Start U4 | U1 + U2 complete and tested |
| Start U5 | U1 + U2 complete and tested |
| Start U7 | U1 + U2 complete and tested |
| Start U6 | U4 + U5 complete and tested |
| Final integration pass | U6 complete |
