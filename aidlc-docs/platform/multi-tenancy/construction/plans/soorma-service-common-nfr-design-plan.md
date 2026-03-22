# NFR Design Plan — soorma-service-common (U2)
## Initiative: Multi-Tenancy Model Implementation
**Date**: 2026-03-22

---

## Assessment

Three security NFRs drive NFR Design for U2. All patterns are deterministic from the functional design and NFR requirements; no clarifying questions needed.

The key NFR Design concerns:
1. **set_config transaction-scoping pattern** — how RLS activation is bound to the transaction lifecycle
2. **Session variable lifecycle** — connection pool safety (transaction-scoped vs. session-scoped)
3. **NATS path pattern** — RLS activation without HTTP middleware

---

## Plan Steps

- [x] Step 1: Analyze NFR requirements for U2
- [x] Step 2: Design set_config transaction-scoping pattern
- [x] Step 3: Design connection pool safety pattern
- [x] Step 4: Design NATS path RLS activation pattern
- [x] Step 5: Generate nfr-design-patterns.md
- [x] Step 6: Generate logical-components.md
