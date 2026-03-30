# Unit-2 NFR Requirements

## Scope
Unit-2 covers runtime identity alignment in Memory Service across API, service, and CRUD boundaries, including explicit admin boundary hardening.

## Inputs
- Functional Design artifacts from `construction/unit-2/functional-design/`
- Answers from `construction/plans/unit-2-nfr-requirements-plan.md`

## NFR Decisions (from answered questions)
- Q1: A - No hard numeric latency SLO in this initiative; best-effort low overhead.
- Q2: A - Explicit server-side admin role/permission guard required on every admin endpoint now.
- Q3: B - Validation-failure logging allows `platform_tenant_id` only; never service tenant/user.
- Q4: A - Fail closed with explicit validation exception at service boundary.
- Q5: B - Require behavior scenarios plus explicit test-module mapping and minimum scenario list.

## Non-Functional Requirements

### NFR-U2-01 Runtime Overhead Minimization
Identity validation and propagation logic must remain lightweight for user-scoped routes.

Acceptance:
- No additional network I/O in identity checks.
- No redundant DB round-trips for identity-only validation.
- Additional runtime checks remain best-effort minimal and deterministic.

### NFR-U2-02 Admin Authorization Baseline
Admin routes must enforce explicit server-side admin authorization on every endpoint.

Acceptance:
- Each admin endpoint has a dedicated authorization guard/check.
- Network location controls are not considered sufficient by themselves.
- Admin authorization remains separate from user ownership checks.

### NFR-U2-03 Validation Logging Privacy Contract
Identity-validation failures (HTTP 400) must preserve privacy and operational usefulness.

Acceptance:
- Allowed in warning logs: `platform_tenant_id` only.
- Forbidden in warning logs: `service_tenant_id`, `service_user_id`, tokens, secrets, and PII.
- Error response bodies remain generic and transport-agnostic.

### NFR-U2-04 Fail-Closed Reliability
Service and CRUD boundaries must fail closed when required identity context is missing.

Acceptance:
- Service boundary validation raises explicit exception before CRUD execution.
- No fallback to platform-only filtering when user-scope context is required.
- DB constraints are a final safeguard, not the primary validation mechanism.

### NFR-U2-05 Testability and Maintainability Bar
Unit-2 must include explicit behavior scenarios and expected test-module mapping before NFR Design.

Acceptance:
- Scenario set includes route gate behavior, service propagation, CRUD predicate consistency, and admin-route authorization baseline.
- Expected test locations are mapped for API, services, CRUD, and integration layers.
- Full test case authoring is deferred to code generation/testing stages and QA extension artifacts.

## Minimum Scenario Set (Design-Level)
- U2-NFR-S1: Missing user context returns fail-closed 400 at boundary.
- U2-NFR-S2: Missing identity in downstream call path is rejected before write/read operations.
- U2-NFR-S3: Plans/sessions/task_context/plan_context predicates use full identity tuple.
- U2-NFR-S4: Admin endpoints enforce explicit admin authorization guard.
- U2-NFR-S5: Validation warning logs include platform tenant only and never service tenant/user.

## Traceability
- FR-3, FR-4, FR-5, FR-6, FR-7, FR-10
- NFR-1, NFR-2, NFR-4, NFR-6
- SECURITY-03, SECURITY-05, SECURITY-08, SECURITY-11, SECURITY-15
