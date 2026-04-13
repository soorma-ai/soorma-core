# Functional Design Plan - uow-sdk-jwt-integration

## Unit Context
- Unit: uow-sdk-jwt-integration
- Purpose: Upgrade SDK wrappers/clients for JWT-authenticated flows while preserving existing handler signatures and two-layer architecture constraints.
- Dependencies: uow-shared-auth-foundation and uow-identity-core-domain (completed).
- Story coverage:
  - US-4.2 SDK JWT Client Upgrade
  - FR-11 phased rollout compatibility obligations
  - FR-12 wrapper-only access constraints

## Architecture Pattern Alignment
- Section 1 (Authentication model): JWT transport becomes primary while preserving strict tenant/user identity semantics.
- Section 2 (Two-layer SDK): handlers continue using `context.*` wrappers only; no direct low-level service client imports.
- Section 3 (Event choreography): existing response-event and envelope patterns remain unchanged during transport/auth transition.
- Section 4 (Multi-tenancy/RLS): canonical tenant context must derive from validated JWT claims; mismatch handling is fail-closed.
- Section 6 (Error handling): wrapper and client failures must return safe, typed errors.
- Section 7 (Testing): enforce unit + integration + negative security paths for migration safety.

## Execution Checklist
- [x] Step 1 - Analyze unit scope, dependencies, and migration checklist requirements.
- [x] Step 2 - Create functional design planning checklist for this unit.
- [x] Step 3 - Generate clarifying questions for JWT SDK integration business logic and policy behavior.
- [x] Step 4 - Store planning artifact.
- [x] Step 5 - Collect and analyze answers.
- [x] Step 6 - Generate functional design artifacts.
- [x] Step 7 - Present functional design completion review gate.

## Functional Design Clarifying Questions
Please answer each question by filling in the [Answer]: line.

## Question 1
What should be the canonical identity context source for SDK outbound calls in this unit?

A) JWT claims only; legacy tenant/user headers are not sent in this unit

B) JWT claims are canonical, and legacy headers may be sent only as bounded compatibility aliases

C) Legacy headers remain canonical while JWT is optional metadata

X) Other (please describe after [Answer]: tag below)

[Answer]: A)

## Question 2
How should SDK and service layers handle JWT tenant mismatch against compatibility alias values during this unit?

A) Deny always (fail-closed) on any mismatch

B) Warn and continue for compatibility period

C) Configurable per environment (strict in prod, warn in dev)

X) Other (please describe after [Answer]: tag below)

[Answer]: A), although as per Q1 we will only send JWT and no headers, so this is purely from defensive design point of view.

## Question 3
What caller-auth mechanism should SDK-integrated token issuance use during this compatibility phase?

A) Client credentials grant

B) Signed client assertion JWT

C) Temporary bootstrap admin key path only

D) Hybrid: temporary bootstrap path plus target production mechanism

X) Other (please describe after [Answer]: tag below)

[Answer]: C)

Rationale:
- This compatibility-phase unit needs a bounded bootstrap path for caller authentication before full production caller-auth rollout is completed.
- Admin key based caller-auth keeps issuance control explicit and auditable while avoiding immediate coupling to unfinished auth flows.
- The path remains temporary and scoped for later hardening/cutover work.

Clarification:
- The admin key authenticates and authorizes the caller of the token-issuance API.
- The admin key is not the JWT signing key.
- Issued JWTs are signed by identity service asymmetric signing keys.
- Token issuance still enforces tenant binding, scope checks, and fail-closed denial on policy violations.

## Question 4
What authorization policy should govern token issuance requests initiated through SDK paths?

A) Self-issue only (`caller_principal_id == requested_principal_id`)

B) Self-issue plus scoped admin override with explicit policy checks and auditing

C) Any authenticated principal in same tenant can issue for others

X) Other (please describe after [Answer]: tag below)

[Answer]: B)

Clarification:
- Default authorization remains self-issue (`caller_principal_id == requested_principal_id`).
- Admin override is allowed only for explicitly scoped/admin-authorized callers under tenant-bound policy checks.
- Every override path must be auditable with actor, target principal, reason, and correlation context.
- Any policy miss or tenant-boundary violation fails closed.

## Question 5
For asymmetric signing rollout in this unit, what verifier distribution model should be functionally designed?

A) Static public key distribution only

B) JWKS endpoint with cache and key-rotation semantics

C) Both static key fallback and JWKS with deterministic precedence

X) Other (please describe after [Answer]: tag below)

[Answer]: C)

## Question 6
How should wrapper API compatibility be enforced while adding JWT support?

A) Preserve all existing wrapper signatures exactly; inject JWT behavior internally only

B) Introduce new wrapper methods and deprecate old signatures immediately

C) Add optional parameters on existing wrappers for migration controls

X) Other (please describe after [Answer]: tag below)

[Answer]: A)

Rationale:
- This unit is explicitly compatibility-focused (FR-11), so preserving existing wrapper signatures avoids downstream churn in handlers, examples, and tests.
- JWT transport/auth behavior can be introduced inside wrapper internals without changing caller contracts.
- This keeps migration risk low and supports incremental mergeability before later cleanup/cutover work.

## Question 7
What should the functional behavior be for `soorma dev` tenant bootstrap CLI in this unit?

A) One-shot create only; error if tenant already exists

B) Idempotent bootstrap; create if absent, verify/reuse if present

C) Prompt-driven interactive flow with manual confirmation for every operation

X) Other (please describe after [Answer]: tag below)

[Answer]: B)

Safety callout:
- Use strict idempotency semantics: create if absent, verify if present, and fail closed on protected drift.
- Return explicit operation outcome (`CREATED`, `REUSED`, `FAILED_DRIFT`) so reuse is never silent.
- Preserve immutable identity/trust fields during reuse; changes to those fields require explicit admin reconcile path.
- Emit structured audit events for create/reuse/drift decisions with before/after context.

## Question 8
How should SDK error contracts be represented for JWT/auth failures in this unit?

A) Raise typed SDK exceptions with stable categories and safe messages

B) Return raw HTTP errors to callers

C) Return generic runtime exceptions only

X) Other (please describe after [Answer]: tag below)

[Answer]: A)

## Question 9
What test matrix level should be treated as mandatory for this unit's functional design?

A) Wrapper unit tests only

B) Wrapper unit tests + SDK to service integration happy paths

C) B + negative security matrix (invalid JWT, unknown `kid`, tenant mismatch, unauthorized issue-for-other)

X) Other (please describe after [Answer]: tag below)

[Answer]: C)

## Approval
After completing all answers, reply in chat with:
"functional design plan answers provided"