# Functional Design Plan - uow-shared-auth-foundation

## Unit Context
- Unit: `uow-shared-auth-foundation`
- Purpose: Establish JWT-capable shared dependency layer while preserving existing DI/router call sites.
- Primary targets: `libs/soorma-service-common` shared auth dependencies and compatibility adapter behavior.
- Key traceability: FR-11, FR-12, US-4.1, US-3.1, US-3.2.

## Architecture Pattern Alignment
- Section 1: authentication and two-tier tenancy context propagation.
- Section 2: two-layer SDK compatibility and wrapper-first contracts.
- Section 3: event service trust boundary and explicit response behavior.
- Section 4: tenant/user isolation and fail-closed access semantics.
- Section 6: explicit error handling with safe defaults.
- Section 7: unit/integration testability.

## Execution Checklist
- [x] Step 1 - Analyze unit context and predecessor artifacts
- [x] Step 2 - Draft functional design planning checklist
- [x] Step 3 - Generate clarifying questions for business logic and domain constraints
- [x] Step 4 - Store this plan file
- [x] Step 5 - Review completed answers and resolve ambiguities
- [x] Step 6 - Generate functional design artifacts
- [x] Step 7 - Present functional design completion gate

## Functional-Design Clarifying Questions
Please answer every question by filling the `[Answer]:` field.

## Question 1
For the coexistence period in shared dependencies, what should be the exact auth precedence when both JWT and legacy headers are present?

A) JWT always wins, headers ignored

B) Validate both and require identity parity; reject on mismatch

C) Prefer JWT, but fallback to headers if JWT invalid/missing

D) Config-driven precedence (mode switch per environment)

X) Other (please describe after [Answer]: tag below)

[Answer]: A) whenver there is JWT in a request, ignore headers. fail fast if invalid JWT when present.

## Question 2
What is the required fail-closed behavior for malformed/expired JWTs during coexistence?

A) Reject request immediately, no header fallback

B) Allow header fallback only for explicitly allowlisted internal routes

C) Allow header fallback for all current routes until cutover

D) Configurable fallback by service

X) Other (please describe after [Answer]: tag below)

[Answer]: A)

## Question 3
How should platform tenant mapping be resolved in this unit when JWT carries tenant claims that differ from `X-Tenant-ID`?

A) JWT claim is authoritative

B) Header is authoritative during coexistence

C) Must match exactly; reject on mismatch

D) Service-specific policy mapping

X) Other (please describe after [Answer]: tag below)

[Answer]: A) whenever JWT claim is present, it's authoritative.

## Question 4
What is the canonical internal auth context object shape to standardize across services in this unit?

A) `{platform_tenant_id, principal_id, principal_type, roles}` only

B) A + optional `{service_tenant_id, service_user_id}`

C) B + request metadata (`correlation_id`, `source`)

D) C + policy decision fields (`delegated_allowed`, `reasons`)

X) Other (please describe after [Answer]: tag below)

[Answer]: X) Canonical shape should be tuple-first for current ingress patterns: `{platform_tenant_id, service_tenant_id, service_user_id}` as the primary access context. Principal fields should be present when applicable (`principal_id`, `principal_type`, `roles`) for platform-tenant developer/admin workflows and delegated JWT scenarios; otherwise principal can remain optional. Keep request metadata and policy-decision fields as optional extension fields.

## Question 5
Which routes in existing services should be treated as public/no-auth exceptions in shared dependency logic?

A) None

B) Health and readiness endpoints only

C) Health/readiness + selected metadata endpoints

D) Keep existing per-service behavior; do not centralize exceptions yet

X) Other (please describe after [Answer]: tag below)

[Answer]: D) Keep existing per-service behavior; do not centralize route-level authn/authz exceptions in shared logic. Shared dependency should provide reusable auth context parsing/validation primitives and default helpers only, while each service remains authoritative for route policy and public endpoint declarations.

## Question 6
For delegated optional claims (`service_tenant_id`, `service_user_id`), what should this unit enforce at dependency level?

A) Presence allowed but not validated in this unit

B) Structural validation only; trust decisions deferred

C) Structural validation + trust-policy hook contract required

D) Full trust validation in shared dependency layer

X) Other (please describe after [Answer]: tag below)

[Answer]: C) Structural validation + trust-policy hook contract required.

Definitions and rationale:
- Shared dependency responsibilities in this unit:
	- Validate JWT cryptographic and base claims (`iss`, `aud`, `exp`, signature).
	- Validate delegated claim structure (`service_tenant_id`, `service_user_id`) and normalize canonical auth context.
	- Invoke a trust-policy hook before accepting delegated context for route execution.
- Trust-policy hook contract (conceptual):
	- Input: normalized auth context (`platform_tenant_id`, optional delegated tuple, issuer, principal fields, flow type) + route policy (allow delegated yes/no, allowed issuers/flows/roles).
	- Output: trust decision `{allowed: bool, provenance: trusted_internal|trusted_delegated|denied, reason}`.
- Enforcement model:
	- Fail closed if trust decision is denied.
	- Continue with normalized context and provenance marker if allowed.
	- Service remains authoritative for endpoint-level authorization logic; shared layer provides trust gating and normalized inputs only.
- Why this is needed even when tuple values match header-based flows:
	- Equal claim values do not guarantee equal trust provenance.
	- Hook prevents privilege confusion between internal trusted-agent assertions and delegated external issuer assertions.

## Question 7
How should error response semantics be standardized for auth failures in this unit?

A) Single 401 for all auth failures

B) 401 for authentication failures, 403 for authorization/policy denial

C) Service-defined status codes but unified error envelope

D) Keep current behavior unchanged; log-only normalization

X) Other (please describe after [Answer]: tag below)

[Answer]: B)

## Question 8
What minimum audit/telemetry fields must be emitted by shared auth dependency for each decision?

A) timestamp, route, status, reason

B) A + platform_tenant_id, principal_id

C) B + principal_type, roles, correlation_id

D) C + delegated claim presence and policy hook outcome

X) Other (please describe after [Answer]: tag below)

[Answer]: D)

## Question 9
How should this unit expose compatibility controls for phased rollout?

A) Environment variable flags only

B) Central config object in `soorma-service-common`

C) B + per-service override option

D) Runtime feature flag provider integration

X) Other (please describe after [Answer]: tag below)

[Answer]: X) No runtime feature flag or environment flag is required for auth-path selection in this rollout.

Rationale:
- Rollout is phase-by-phase through code evolution, not runtime toggling:
	1) dual-path implementation with JWT authoritative when present,
	2) SDK updates to send JWT,
	3) remove header-auth code.
- Runtime flags add operational and testing complexity without clear value for this unit.
- Deterministic behavior reduces configuration drift risk across services and environments.

Allowed narrow use:
- Non-authoritative observability controls are acceptable (for example, extra debug metrics/log verbosity), but must not change auth allow/deny decisions.

## Question 10
What testability contract should functional design lock in for this unit?

A) Unit tests for parser/validator logic only

B) A + service-level dependency integration tests

C) B + cross-service regression matrix for coexistence behavior

D) C + failure injection scenarios (invalid claims, mismatch, expired token)

X) Other (please describe after [Answer]: tag below)

[Answer]: D) plus full coverage expectation for this unit.

Coverage interpretation for this initiative:
- Unit tests: comprehensive coverage for parser, claim validation, normalization, trust-hook invocation, precedence, and fail-closed branches.
- Service-level integration tests: all relevant auth entry paths across consuming services.
- Cross-service coexistence regression: JWT-present authoritative behavior, legacy-header coexistence behavior, and mismatch/error paths.
- Failure-injection tests: invalid signature, expired token, malformed claims, issuer mismatch, delegated trust denial, and policy-denied route cases.

## Approval
After answering all questions, confirm in chat:
"functional design plan answers provided"
