# Unit-1 Functional Design Plan

## Unit Context
- Unit: U1 - Shared Identity Dependency (soorma-service-common)
- Goal: Implement reusable `require_user_context` dependency that enforces presence of both `service_tenant_id` and `service_user_id`.
- Primary requirements: FR-2, FR-3 (foundation), NFR-1, NFR-5.
- Upstream dependencies: none.
- Downstream consumers: Unit-2 memory routers and services.

## Functional Design Checklist
- [x] Read Unit-1 definition from inception artifacts
- [x] Read requirements-to-unit mapping and application design artifacts
- [x] Confirm boundaries: shared dependency only, no memory-specific business logic leakage
- [x] Create functional design questions with [Answer] tags
- [x] Resolve all question answers and ambiguities
- [x] Generate `business-logic-model.md`
- [x] Generate `business-rules.md`
- [x] Generate `domain-entities.md`
- [x] Perform security compliance review for generated artifacts
- [x] Present functional design completion for approval

## Clarifying Questions
Please answer each question by filling the letter after `[Answer]:`.

### Question 1: Dependency signature and return contract
How should `require_user_context` expose validated context for downstream handlers?

A) Return the existing context object unchanged when valid; raise 400 on failure

B) Return a reduced dict with only required identity fields; raise 400 on failure

C) Return a typed result object with explicit fields and helper methods

X) Other (please describe after [Answer]: tag below)

[Answer]: A, we'll re-use same tenant context object, just additional check.

### Question 2: Generic error response phrasing
Which generic response style should be used for missing identity context?

A) Single generic message for either missing field: "Missing required user identity context"

B) Two generic messages (one per missing dimension), both still transport-agnostic

C) Structured generic payload with code + message (still no header details)

X) Other (please describe after [Answer]: tag below)

[Answer]: B. from devex point of view better to have message for each.

### Question 3: Shared package export surface
Where should the new dependency be exported for downstream service imports?

A) Export from the current top-level public module used by services today

B) Export from a dedicated identity submodule and re-export at top level

C) Keep internal for now and import by deep path from memory service

X) Other (please describe after [Answer]: tag below)

[Answer]: A) with rationale:
- Keep export consistent with today’s top-level import surface.
- Avoid import churn in downstream services.
- Preserve backward compatibility and reduce migration risk.

### Question 4: Backward compatibility strategy
How should existing `require_user_id` usage be handled during transition?

A) Keep `require_user_id` and add `require_user_context` side-by-side (preferred for low-risk rollout)

B) Replace `require_user_id` immediately and update all current call sites in this initiative

C) Keep `require_user_id` as alias/delegator to `require_user_context`

X) Other (please describe after [Answer]: tag below)

[Answer]: B. backward compatibility is not a concern, replace whatever exists in repo today.

### Question 5: Extensibility approach for future authorization
What extensibility pattern should be built into Unit-1 design?

A) Keep dependency minimal now; define clear extension seam in doc only

B) Add optional parameters now for future role checks (unused in Unit-1)

C) Create composable dependency chain pattern (`require_identity`, `require_role`, etc.)

X) Other (please describe after [Answer]: tag below)

[Answer]: C. composable chain is better long-term.
Rationale:
- Keeps identity validation and authorization concerns modular (`require_identity`, `require_role`, etc.).
- Lets Unit-2+ adopt stricter checks without rewriting Unit-1 foundations.
- Improves reuse across services while preserving single-responsibility dependencies.

### Question 6: Unit-1 test scope depth
What should Unit-1 shared-library tests include in this stage?

A) Happy path + missing tenant + missing user (minimal contract coverage)

B) A + empty-string variants + whitespace-only variants + message assertions

C) A + B + explicit compatibility checks for old dependency behavior

X) Other (please describe after [Answer]: tag below)

[Answer]: B is enough. don't need compatibility with old behavior.

## Notes
- This plan is limited to Functional Design for Unit-1.
- Code changes will be executed only after design completion, review, and approval gates.
