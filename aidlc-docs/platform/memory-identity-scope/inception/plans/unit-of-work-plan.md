# Unit of Work Plan

## Objective
Decompose implementation into clear units with minimal coupling and explicit dependency order.

## Planning Checklist
- [x] Confirm decomposition strategy across affected packages
- [x] Confirm unit sequencing and dependency constraints
- [x] Confirm testing and migration ownership per unit
- [x] Generate unit-of-work.md with unit definitions and responsibilities
- [x] Generate unit-of-work-dependency.md with dependency matrix
- [x] Generate unit-of-work-story-map.md mapping requirements to units
- [x] Validate boundaries and handoff criteria
- [x] Ensure all requirements are assigned to units

## Proposed Baseline Decomposition

- **U1: Shared Identity Dependency (soorma-service-common)**
  - Build `require_user_context`
  - Export/update package surface
  - Add/adjust shared-library tests

- **U2: Memory API + Service + CRUD Alignment**
  - Apply dependency to user-scoped routers
  - Propagate full identity tuple through services/CRUD
  - Align predicates for plans/sessions/task_context/plan_context

- **U3: Schema/Index/Migration + Validation Tests (memory service)**
  - Update model unique constraints
  - Add migration(s) for working/task/plan context and semantic index alignment
  - Add migration + isolation + negative-path tests

## Clarifying Questions

### Question 1: Unit granularity
Choose decomposition granularity:

A) Keep 3 units (U1 shared dependency, U2 runtime logic alignment, U3 schema/migration/test alignment)

B) Collapse to 2 units (U1 shared dependency, U2 all memory changes)

C) Expand to 4+ units (finer-grained by router/resource)

X) Other (please describe after [Answer]:)

[Answer]: A, address dependencies so that each unit is testable as the work completes

### Question 2: Sequencing policy
Choose sequencing policy:

A) Strict sequential U1 -> U2 -> U3

B) Hybrid: start U3 migration draft in parallel with U2, but merge only after U2 final predicates are locked

C) Mostly parallel with late integration

X) Other (please describe after [Answer]:)

[Answer]: A. Rationale:
- Strict sequential flow (U1 -> U2 -> U3) keeps dependency ordering explicit.
- Each unit becomes independently testable as soon as it completes.
- Reduces integration churn while identity predicates and migration contracts are being finalized.

### Question 3: Test ownership boundary
Where should cross-scope behavior tests primarily live?

A) Mostly in memory service tests; shared-lib only tests dependency behavior

B) Split evenly between shared-lib and memory tests

C) Heavy shared-lib coverage with lighter memory tests

X) Other (please describe after [Answer]:)

[Answer]: A. Rationale:
- Primary risk is in memory-service behavior (predicate alignment, migration safety, cross-scope isolation), so most behavioral coverage belongs in memory tests.
- Shared library should own focused unit tests only for `require_user_context` validation behavior and error semantics.
- This avoids duplicated assertions across repos while keeping ownership clear: shared lib validates dependency contract, memory service validates end-to-end data isolation outcomes.

## Generation Steps (to execute after approval)
- [x] Produce unit-of-work.md
- [x] Produce unit-of-work-dependency.md
- [x] Produce unit-of-work-story-map.md
- [x] Mark planning checklist complete

## Completion Criteria
- All [Answer]: tags completed
- No ambiguity in granularity, sequencing, and test ownership
- Unit artifacts generated and internally consistent
