# Functional Design Plan — U5: services/tracker
## Initiative: Multi-Tenancy Model Implementation
**Created**: 2026-03-23T06:20:19Z

---

## Unit Context
- **Unit**: U5 — `services/tracker`
- **Wave**: 3 (parallel with U4, U7)
- **Change Type**: Moderate
- **Depends On**: U1 (`libs/soorma-common`), U2 (`libs/soorma-service-common`) — both COMPLETE
- **Construction Stages**: Functional Design, Code Generation (NFR Requirements/NFR Design/Infrastructure Design are skipped per unit spec)

---

## Architecture Alignment (docs/ARCHITECTURE_PATTERNS.md)
This unit's functional design is aligned with the mandatory architecture patterns:

- **Section 1 (Authentication & Authorization)**: Tracker API path derives `platform_tenant_id` from authenticated request context, and `service_tenant_id`/`service_user_id` from trusted request headers via shared middleware.
- **Section 2 (SDK Two-Layer Architecture)**: No service-client leakage to agent handlers; Tracker remains backend-only and exposes API contracts consumed via SDK wrappers.
- **Section 3 (Event Choreography)**: NATS handlers consume explicit envelope fields and must trust `event.platform_tenant_id` only when injected by Event Service.
- **Section 4 (Multi-Tenancy)**: Composite namespace enforcement in Tracker queries: `(platform_tenant_id, service_tenant_id, service_user_id)`.
- **Section 5 (State Management)**: Plan/action progress state remains tenant-scoped and user-scoped under the new identity model.
- **Section 6 (Error Handling)**: Event/API paths must fail closed on missing or invalid identity context.
- **Section 7 (Testing)**: Unit + integration tests must cover U1/U2 integration points and composite-key isolation behavior.

---

## Inception Artifacts Loaded
- `inception/requirements/requirements.md`
- `inception/application-design/unit-of-work.md`
- `inception/application-design/unit-of-work-dependency.md`
- `inception/application-design/unit-of-work-story-map.md`
- `inception/application-design/component-methods.md`
- `inception/application-design/components.md`
- `inception/application-design/services.md`
- `inception/plans/execution-plan.md`
- `inception/test-cases/tracker/test-case-index.md`
- `inception/test-cases/tracker/test-specs-narrative.md`
- `inception/test-cases/tracker/test-specs-gherkin.md`
- `inception/test-cases/tracker/test-specs-tabular.md`

---

## Plan Steps
- [x] Step 1 — Analyze unit context and inception traceability for U5
- [x] Step 2 — Create functional design plan and architecture alignment checklist
- [x] Step 3 — Collect and resolve clarifying answers
- [x] Step 4 — Generate `construction/tracker/functional-design/domain-entities.md`
- [x] Step 5 — Generate `construction/tracker/functional-design/business-logic-model.md`
- [x] Step 6 — Generate `construction/tracker/functional-design/business-rules.md`
- [x] Step 7 — Present Functional Design completion for review/approval

---

## Clarifying Questions (Functional Design)
Please answer by filling each `[Answer]:` tag.

## Question 1
For Tracker NATS handlers, what should happen when `event.platform_tenant_id` is absent at runtime?

A) Reject event and log a structured warning (fail closed)

B) Default to `DEFAULT_PLATFORM_TENANT_ID` and continue processing

C) Drop event silently (no DB write)

D) Allow configurable behavior via env var (strict vs default)

E) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 2
Should `service_user_id` remain required on Tracker progress rows after migration?

A) Keep `service_user_id` NOT NULL on both `plan_progress` and `action_progress`

B) Allow `service_user_id` NULL on `plan_progress` only

C) Allow `service_user_id` NULL on both tables

D) Keep current nullability exactly as-is from existing schema (no semantic change)

E) Other (please describe after [Answer]: tag below)

[Answer]: D

## Question 3
How should unique/index constraints be updated for renamed identity columns?

A) Recreate constraints/indexes to include `(platform_tenant_id, service_tenant_id, service_user_id, business_key)`

B) Recreate constraints/indexes with `(platform_tenant_id, service_tenant_id, business_key)` only

C) Keep existing uniqueness strategy and only rename columns

D) Defer uniqueness/index changes to a separate unit

E) Other (please describe after [Answer]: tag below)

[Answer]: E — Use a hybrid key strategy tied to domain identifiers (business keys):
- `plan_progress` unique key: `(platform_tenant_id, service_tenant_id, plan_id)`
- `action_progress` unique key: `(platform_tenant_id, service_tenant_id, action_id)`
- `service_user_id` should be indexed for query performance/filtering, but not forced into uniqueness unless we explicitly support the same `plan_id`/`action_id` repeating across users inside one service tenant.

Rationale:
- Preserves strict namespace isolation at the platform + service-tenant boundary.
- Matches current business identity model where `plan_id` and `action_id` are the primary domain identifiers (business keys).
- Avoids over-constraining writes by making uniqueness user-scoped when that behavior is not required today.
- Keeps migration low-risk while still correcting global uniqueness assumptions from the old schema.

## Question 4
For GDPR deletion in Tracker (`TrackerDataDeletion`), which API exposure is preferred in this unit?

A) Implement service class only (no route exposure)

B) Implement service class + internal admin endpoint

C) Implement service class + public endpoint (authenticated)

D) Defer GDPR deletion entirely to later unit

E) Other (please describe after [Answer]: tag below)

[Answer]: B, keep is consistent as memory service.

## Question 5
For API validation of IDs (`service_tenant_id`, `service_user_id`, `platform_tenant_id`), what is the desired enforcement model?

A) Enforce max length 64 at DTO/API validation layer and DB schema

B) Enforce only at DB schema layer (no API validation)

C) Enforce via shared validation helper in `soorma-service-common` + DB schema

D) Enforce via middleware only

E) Other (please describe after [Answer]: tag below)

[Answer]: Option A for current unit execution, with rationale that shared-helper standardization is deferred to a dedicated follow-up refactor.
