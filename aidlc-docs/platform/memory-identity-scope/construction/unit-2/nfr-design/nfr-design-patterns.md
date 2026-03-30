# Unit-2 NFR Design Patterns

## Scope
This document maps approved Unit-2 NFR requirements into implementable design patterns for memory runtime identity alignment across API, service, and CRUD layers.

## Answer Traceability
- Q1: C (dual-layer fail-closed guards: route + service backstop)
- Q2: A (shared admin guard dependency per admin endpoint)
- Q3: A (structured warning event with fixed fields; platform_tenant_id only)
- Q4: A (shared full-identity predicate helper abstraction)
- Q5: B (pattern + component boundaries + scenario-to-test-module traceability)

## Pattern 1: Dual-Layer Fail-Closed Guard
### Intent
Prevent identity-bypass risks while keeping request rejection early and deterministic.

### Design
- Route boundary guard: enforce user-context presence at user-scoped routers.
- Service boundary guard: mandatory backstop validation before CRUD entry.
- Both layers fail closed with explicit validation exception.

### Why
- Route checks provide early rejection and clear API behavior.
- Service backstop protects against internal call paths and missed route coverage.
- Supports SECURITY-05, SECURITY-08, SECURITY-15.

## Pattern 2: Shared Admin Authorization Guard Pattern
### Intent
Keep admin authorization consistent and reviewable without inline drift.

### Design
- Define shared admin authorization dependency/guard.
- Apply guard explicitly on each admin endpoint.
- Keep admin authorization concerns separate from user ownership checks.

### Why
- Reduces duplicated inline auth logic.
- Keeps privileged route behavior auditable and consistent.
- Supports SECURITY-08 and least-privilege design intent.

## Pattern 3: Structured Validation Warning Event
### Intent
Provide operational observability for validation failures while minimizing sensitive identity exposure.

### Required fields
- `event_name` (fixed value, e.g., `identity_validation_failed`)
- `severity` (`warning`)
- `platform_tenant_id` (when available)
- `failure_reason` (fixed enum/code)
- `correlation_id` or request id (if available)

### Forbidden fields
- `service_tenant_id`
- `service_user_id`
- tokens, credentials, raw payloads, PII

### Why
- Maintains tenant-level operational filtering.
- Enforces privacy and security logging boundaries.
- Supports SECURITY-03 and SECURITY-14-oriented observability posture.

## Pattern 4: Shared Identity Predicate Helper
### Intent
Guarantee consistent full-identity filtering across plans/sessions/task_context/plan_context with minimal long-term drift.

### Design
- Introduce small, identity-agnostic predicate helper surface:
  - full identity tuple predicate builder
  - optional resource-key predicate combiner
- Keep helper focused on identity constraints only.
- Keep business-specific clauses in calling CRUD modules.

### Why
- Reduces repetitive predicate composition.
- Improves consistency and maintainability across modules.
- Enables reuse by other services without memory-specific coupling.

## Pattern 5: NFR-Test Traceability Pattern
### Intent
Make NFR verification explicit without converting this stage into full test authoring.

### Design
- Pair each adopted pattern with expected verification scenarios.
- Map each scenario to expected test-module location.
- Keep detailed executable test case authoring for later stages.

### Why
- Improves implementation confidence.
- Supports focused code generation and review.
- Aligns with Q5=B and maintainability requirements.

## Scenario-to-Test Module Trace Map
- U2-NFR-S1 dual-layer fail-closed behavior -> `services/memory/tests/api/v1/`, `services/memory/tests/services/`
- U2-NFR-S2 downstream missing identity backstop -> `services/memory/tests/services/`, `services/memory/tests/crud/`
- U2-NFR-S3 full-identity predicate consistency -> `services/memory/tests/crud/`
- U2-NFR-S4 admin guard enforcement -> `services/memory/tests/api/v1/`
- U2-NFR-S5 structured warning logging policy -> `services/memory/tests/services/` (and integration if available)

## Deferred Notes
- No infrastructure pattern changes in Unit-2.
- No schema/index migration pattern changes in Unit-2 (deferred to Unit-3).
