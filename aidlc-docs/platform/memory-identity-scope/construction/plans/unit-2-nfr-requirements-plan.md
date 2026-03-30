# Unit-2 NFR Requirements Plan

## Unit Context
- Unit: U2 - Memory Runtime Alignment (API + Services + CRUD)
- Scope: user-scoped runtime enforcement, full-identity predicate propagation, and admin boundary policy hardening
- Inputs reviewed:
  - construction/unit-2/functional-design/business-logic-model.md
  - construction/unit-2/functional-design/business-rules.md
  - construction/unit-2/functional-design/domain-entities.md

## NFR Assessment Checklist
- [x] Analyze Unit-2 functional design artifacts
- [x] Identify NFR categories applicable to runtime alignment and access control boundaries
- [x] Prepare NFR clarification questions with [Answer] tags
- [x] Resolve all answers and ambiguities
- [x] Generate nfr-requirements.md
- [x] Generate tech-stack-decisions.md
- [x] Perform security-baseline compliance check
- [x] Present NFR Requirements completion for approval

## Clarifying Questions
Please answer each question by filling the letter after [Answer]:.

## Question 1
For request-path performance in Unit-2, what additional latency budget is acceptable for router-level `require_user_context` plus full-identity propagation checks on user-scoped endpoints?

A) Best effort only; no explicit numeric target

B) P95 overhead less than 2 ms per request

C) P95 overhead less than 5 ms per request

X) Other (please describe after [Answer]: tag below)

[Answer]: a)

## Question 2
For admin route hardening, what minimum authorization requirement should be documented for this initiative phase?

A) Explicit server-side admin role/permission guard on every admin endpoint (required now)

B) Endpoint-level TODO markers now; full guard implementation deferred to unit-3

C) Network-level controls only for now; in-app admin checks deferred

X) Other (please describe after [Answer]: tag below)

[Answer]: a)

## Question 3
For identity-validation failures (HTTP 400) on user-scoped routes, what logging policy should apply?

A) Log generic warning with no identity values

B) Log warning with platform tenant only; never log service tenant/user

C) Do not log expected validation failures

X) Other (please describe after [Answer]: tag below)

[Answer]: b)

## Question 4
For reliability expectations, how should the service behave if identity dimensions are missing in downstream service/CRUD calls despite route-level guards?

A) Fail closed with explicit validation exception at service boundary

B) Best-effort fallback to platform-tenant-only filtering

C) Allow operation and rely on DB constraints to reject unsafe writes

X) Other (please describe after [Answer]: tag below)

[Answer]: a)

## Question 5
For maintainability and rollout confidence, which test bar should Unit-2 NFR guidance require before moving to NFR Design?

A) Behavior scenarios only in design artifacts

B) Behavior scenarios plus explicit test module mapping and minimum scenario list for API/service/CRUD layers

C) Full test case authoring in this stage

X) Other (please describe after [Answer]: tag below)

[Answer]: b)

## Notes
- Questions focus on non-functional quality attributes for runtime identity alignment (performance, security, reliability, and maintainability).
- Code changes remain blocked until NFR Requirements stage artifacts are generated and approved.
