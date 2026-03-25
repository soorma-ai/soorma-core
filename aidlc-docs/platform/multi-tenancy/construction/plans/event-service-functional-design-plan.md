# Functional Design Plan — U7: services/event-service
## Initiative: Multi-Tenancy Model Implementation
**Created**: 2026-03-25T02:57:02Z

---

## Unit Context
- **Unit**: U7 — `services/event-service`
- **Wave**: 3 (parallel with U4, U5)
- **Change Type**: Minor
- **Depends On**: U1 (`libs/soorma-common`), U2 (`libs/soorma-service-common`) — both COMPLETE
- **Construction Stages**: Functional Design, NFR Requirements, NFR Design, Code Generation (Infrastructure Design skipped per unit spec)

---

## Architecture Alignment (docs/ARCHITECTURE_PATTERNS.md)
This unit's functional design is aligned with the mandatory architecture patterns:

- **Section 1 (Authentication & Authorization)**: Event Service must source `platform_tenant_id` from authenticated `X-Tenant-ID` request context via middleware and never trust payload-supplied platform tenant identity.
- **Section 2 (SDK Two-Layer Architecture)**: Event Service remains an internal backend trust boundary and does not expose low-level service client details to agent handlers.
- **Section 3 (Event Choreography)**: Event envelope integrity is preserved by explicit server-side enrichment at publish time before NATS delivery.
- **Section 4 (Multi-Tenancy)**: Platform tenant identity is injected centrally in Event Service to prevent cross-tenant spoofing and to support downstream tenant isolation.
- **Section 5 (State Management)**: Published event context must preserve service tenant/user identifiers while adding authoritative platform tenant identity.
- **Section 6 (Error Handling)**: Publish path must fail closed for malformed requests and identity extraction failures.
- **Section 7 (Testing)**: Unit and integration tests must verify overwrite behavior, middleware extraction, and passthrough correctness.

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
- `inception/test-cases/event-service/test-case-index.md`
- `inception/test-cases/event-service/test-specs-narrative.md`
- `inception/test-cases/event-service/test-specs-gherkin.md`
- `inception/test-cases/event-service/test-specs-tabular.md`

---

## Plan Steps
- [x] Step 1 — Analyze unit context and inception traceability for U7
- [x] Step 2 — Create functional design plan and architecture alignment checklist
- [x] Step 3 — Collect and resolve clarifying answers
- [x] Step 4 — Generate `construction/event-service/functional-design/domain-entities.md`
- [x] Step 5 — Generate `construction/event-service/functional-design/business-logic-model.md`
- [x] Step 6 — Generate `construction/event-service/functional-design/business-rules.md`
- [x] Step 7 — Present Functional Design completion for review/approval

---

## Clarifying Questions (Functional Design)
Please answer by filling each `[Answer]:` tag.

## Question 1
For Event Service behavior when `X-Tenant-ID` is absent, which policy should U7 enforce in Functional Design?

A) Keep fallback to `DEFAULT_PLATFORM_TENANT_ID` for publish requests (current test case baseline TC-ES-004)

B) Reject request as unauthorized/invalid and do not publish event

C) Allow fallback only in local/dev mode via explicit configuration flag

X) Other (please describe after [Answer]: tag below)

[Answer]: For now we'll use option A (event service overwrite / santize to `DEFAULT_PLATFORM_TENANT_ID`), in future we'll revisit this when identity service is implemented and we have service to service authentication implemented for tenant's agents

## Question 2
For anti-spoofing, how should overwrite behavior be specified when SDK supplies `event.platform_tenant_id`?

A) Always overwrite unconditionally from authenticated request context and never log original value

B) Always overwrite and log a structured warning when payload value differs

C) Overwrite only when payload value is null/empty

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 3
What should be the route signature and naming convention for the publish endpoint in U7?

A) `publish_event(publish_request: PublishRequest, http_request: Request)`

B) `publish_event(request: Request, payload: PublishRequest)`

C) Keep existing signature and extract request context through dependency injection helper only

X) Other (please describe after [Answer]: tag below)

[Answer]: C — Keep existing publish endpoint shape and resolve platform_tenant_id via dependency injection helper. Reasoning: this future-proofs the route by keeping endpoint logic decoupled from the identity source; today identity may come from X-Tenant-ID, but later may come from service-to-service authentication (API key or JWT) without forcing endpoint signature/body handling changes.

## Question 4
How strict should ID-length validation be for header-derived `platform_tenant_id` in Event Service?

A) Enforce `<= 64` at API boundary in middleware/route and reject over-limit values

B) Do not enforce in Event Service; rely on downstream persistence layers

C) Warn and truncate values >64 before publish

X) Other (please describe after [Answer]: tag below)

[Answer]: A, assuming this is how other services are also doing.

## Question 5
For service tenant/user passthrough fields in `EventEnvelope`, what is the expected behavior in U7?

A) Pass through `tenant_id` and `user_id` exactly as provided by SDK without mutation

B) Normalize empty strings to `None` before publish

C) Validate and reject if either field is missing

X) Other (please describe after [Answer]: tag below)

[Answer]: X — Event Service is the trust boundary for event metadata sanitization. It must sanitize tenant_id and user_id centrally before publish (trim whitespace, normalize empty to None, enforce max length when present, no mutation of semantic values). platform_tenant_id is always injected/overwritten from authenticated context. `tenant_id` and `user_id` are both required for all events; automation/system-originated events must use an explicit service tenant plus machine/service actor identity so every event remains fully scoped and attributable.
