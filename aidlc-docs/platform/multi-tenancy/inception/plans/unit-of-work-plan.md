# Unit of Work Plan
## Initiative: Multi-Tenancy Model Implementation
**INITIATIVE_ROOT**: `aidlc-docs/platform/multi-tenancy/`
**Stage**: Units Generation
**Date**: 2026-03-22

---

## Step 1: Context from Application Design

The Application Design phase fully resolved the unit decomposition. Seven units across five packages were identified (U1–U7), with an explicit dependency order and parallelization constraints. This plan confirms that decomposition and resolves two remaining open questions before generating artifacts.

---

## Step 2: Artifacts to Generate

- [ ] `inception/application-design/unit-of-work.md` — unit definitions, responsibilities, and construction scope per unit
- [ ] `inception/application-design/unit-of-work-dependency.md` — dependency matrix and parallelization schedule
- [ ] `inception/application-design/unit-of-work-story-map.md` — story/requirement traceability per unit
- [ ] Validate unit boundaries and ensure all FR/NFR requirements are assigned to a unit

---

## Step 3: Clarifying Questions

The unit decomposition itself is settled. These two questions affect how the Construction phase is sequenced and how unit boundaries are tested.

---

### Q1 — Construction execution order

The dependency graph allows some parallelism:
- **U2** (`soorma-service-common`) and **U3** (`services/registry`) are independent of each other — both depend only on U1
- **U4** (`services/memory`), **U5** (`services/tracker`), and **U7** (`services/event-service`) can all proceed once U1 + U2 are done
- **U6** (`sdk/python`) waits for U4 + U5

When executing the Construction phase, which approach do you prefer?

**A** — Sequential order (U1 → U2 → U3 → U4 → U5 → U7 → U6): simpler to follow, one unit at a time.

**B** — Respect parallelism in the stated order (U1 → U2∥U3 → U4∥U5∥U7 → U6): explicitly marks parallel groups in the unit-of-work artifacts so the sequencing is documented even if construction executes one unit at a time.

[Answer]: B

---

### Q2 — Integration test scope per unit

Each unit will have its own Code Generation + Build and Test. For units that depend on earlier units (e.g., U4 memory service depends on U2 soorma-service-common), should the Build and Test stage for U4:

**A** — Unit tests only for U4's own code; integration testing deferred to a final cross-unit integration pass at the end (after U6).

**B** — Include integration tests with already-completed dependency units as part of each unit's Build and Test (e.g., U4 tests include integration with U2 middleware).

[Answer]: B

---

## Step 4: Generation Checklist (to be executed after approval)

- [x] Generate `unit-of-work.md`
- [x] Generate `unit-of-work-dependency.md`
- [x] Generate `unit-of-work-story-map.md`
- [x] Mark all steps [x] and update aidlc-state.md
