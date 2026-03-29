# Unit of Work Definitions

## Decomposition Approach
Chosen approach from approved unit plan:
- Granularity: 3 units (Q1=A)
- Sequencing: strict sequential U1 -> U2 -> U3 (Q2=A)
- Test ownership: memory-heavy behavior coverage, shared-lib contract-focused tests (Q3=A)

## U1 - Shared Identity Dependency (soorma-service-common)

### Scope
Implement reusable user-context validation dependency in shared library.

### Responsibilities
- Add `require_user_context` dependency that validates both `service_tenant_id` and `service_user_id`
- Return HTTP 400 with generic message when either is missing
- Export dependency from package public surface
- Add focused shared-library tests for dependency behavior

### Inputs
- Approved requirements FR-2, FR-3, NFR-1, NFR-5

### Outputs
- Shared dependency implementation
- Shared dependency tests
- Updated package exports

### Exit Criteria
- Dependency importable by memory service
- Tests verify pass/fail behavior for missing identity dimensions
- No memory-specific logic leaked into shared library

## U2 - Memory Runtime Alignment (API + Services + CRUD)

### Scope
Apply shared dependency to user-scoped APIs and align runtime query logic.

### Responsibilities
- Apply `require_user_context` at router level for user-scoped routers
- Keep admin endpoints exempt
- Propagate full identity tuple through service layer and CRUD signatures
- Align predicates for plans/sessions/task_context/plan_context list/get/update/delete
- Align semantic upsert conflict-target definitions with scoped index model

### Inputs
- U1 completed dependency
- FR-3 through FR-7, FR-9, FR-10

### Outputs
- Updated route dependencies
- Updated service and CRUD method signatures/call chains
- Updated conflict targets and runtime filtering behavior

### Exit Criteria
- User-scoped endpoints fail fast with 400 when identity context missing
- Runtime queries consistently use full identity tuple
- Public/admin behavior remains intentional and explicit

## U3 - Schema/Index/Migration + Validation Tests

### Scope
Align database constraints/indexes and verify behavior via tests.

### Responsibilities
- Update SQLAlchemy model unique constraints:
  - working_memory
  - task_context
  - plan_context
- Add/adjust Alembic migrations for constraint/index alignment
- Include semantic index updates per approved scope decision (Q3=B)
- Add/adjust tests for:
  - missing service tenant/user validation
  - cross-user and cross-service-tenant isolation
  - upsert collision prevention
  - migration upgrade/downgrade expectations

### Inputs
- U2 runtime predicate and conflict-target decisions
- FR-8, FR-9, FR-11, NFR-3, NFR-4

### Outputs
- Migration revisions and model updates
- Passing test coverage for isolation and migration paths

### Exit Criteria
- Constraint/index definitions match runtime upsert/query semantics
- Migration paths are deterministic and reversible
- Isolation tests prove no cross-scope leakage/collision

## Handoff and Gate Criteria
- U1 must complete before U2 starts
- U2 must complete before U3 finalizes migration/index definitions
- Each unit includes local verification before handoff
- Final integration verification occurs in Build and Test stage
