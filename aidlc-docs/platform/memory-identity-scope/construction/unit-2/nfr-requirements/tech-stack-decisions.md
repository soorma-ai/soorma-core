# Unit-2 Tech Stack Decisions

## Decision Context
Unit-2 is a runtime-alignment unit in an existing FastAPI + SQLAlchemy async PostgreSQL service. Goal is to harden behavior with minimal architectural churn.

## Technology Choices

### TS-U2-01 API Framework
- Choice: Keep FastAPI dependency-injection model for route-level validation.
- Rationale: Existing routers already use dependency patterns; adding/standardizing identity guards is low-risk and consistent.

### TS-U2-02 Service Boundary Validation
- Choice: Keep explicit Python-level service boundary checks for identity tuple completeness.
- Rationale: Supports fail-closed behavior and clearer error semantics before data access.

### TS-U2-03 Data Access Layer
- Choice: Keep SQLAlchemy async CRUD pattern and enforce full-identity predicates in query composition.
- Rationale: Aligns with existing codebase contracts and avoids introducing new ORM/query abstractions mid-initiative.

### TS-U2-04 Authorization Pattern for Admin Routes
- Choice: Require explicit server-side admin guard/check per endpoint in current FastAPI layer.
- Rationale: Avoids reliance on network perimeter controls; keeps privileged checks close to operational routes.

### TS-U2-05 Logging Strategy for Validation Failures
- Choice: Structured warning logs with platform tenant only; no service tenant/user logging.
- Rationale: Maintains operational filterability while minimizing sensitive identity exposure.

### TS-U2-06 Testing Strategy
- Choice: Map expected verification to existing memory service test layout:
  - `services/memory/tests/api/v1/`
  - `services/memory/tests/services/`
  - `services/memory/tests/crud/`
  - `services/memory/tests/integration/` (if present)
- Rationale: Preserves current repository organization and reviewability.

## Deferred/Out-of-Scope in Unit-2
- Schema/index migrations remain in Unit-3.
- New infrastructure components are not introduced.
- Cross-service auth framework redesign is out of scope.

## Risk and Mitigation
- Risk: Inconsistent guard application across endpoints.
  - Mitigation: Router-level dependency pattern and targeted API tests.
- Risk: Silent parameter drop in service/CRUD chain.
  - Mitigation: Mandatory signature contract + service and CRUD tests.
- Risk: Privileged admin path drift.
  - Mitigation: Explicit admin guard requirement and route-level review checklist.
