# NFR Design Plan - uow-shared-auth-foundation

## Unit Context
- Unit: uow-shared-auth-foundation
- Inputs reviewed:
  - aidlc-docs/platform/identity-service/construction/uow-shared-auth-foundation/nfr-requirements/nfr-requirements.md
  - aidlc-docs/platform/identity-service/construction/uow-shared-auth-foundation/nfr-requirements/tech-stack-decisions.md

## Execution Checklist
- [x] Step 1 - Analyze NFR requirements
- [x] Step 2 - Draft NFR design plan and question set
- [x] Step 3 - Store this NFR design plan file
- [x] Step 4 - Collect and validate all answers
- [x] Step 5 - Generate NFR design artifacts
- [x] Step 6 - Present NFR Design completion gate

## NFR Design Clarifying Questions
Please answer each question by filling the [Answer]: field.

## Question 1
For trust-policy source resilience, which design pattern should be the default composition in this unit?

A) Cache-aside with bounded TTL and strict fail-closed post-expiry

B) Read-through cache with policy source adapter fallback

C) Two-level cache (in-memory + shared) with bounded staleness guard

D) Direct source call only; no caching

X) Other (please describe after [Answer]: tag below)

[Answer]: A)

## Question 2
For observability propagation, what is the minimum tracing boundary in NFR design?

A) Dependency entry/exit spans only

B) A + trust-policy evaluation sub-span

C) B + delegated-claim validation sub-span

D) C + per-decision structured event span correlation

X) Other (please describe after [Answer]: tag below)

[Answer]: D)

## Question 3
For profile-based performance validation support, what logical componenting should design include?

A) Test-only harness docs; no runtime components

B) Metrics tagging schema by load tier only

C) B + policy-driven guardrail thresholds object

D) C + runtime adaptive behavior by tier

X) Other (please describe after [Answer]: tag below)

[Answer]: C) B + policy-driven guardrail thresholds object.

Rationale:
- Preserves open-core portability by avoiding runtime adaptive behavior assumptions.
- Adds explicit, testable guardrail thresholds for latency/error/resource dimensions across load tiers.
- Keeps runtime complexity controlled while improving repeatability of performance acceptance decisions.

## Question 4
Given approved compatibility override (no constraints), what refactor safety pattern should be mandatory in design?

A) Big-bang refactor with final integration validation only

B) Incremental slices with contract tests between slices

C) B + service-wide regression matrix checkpoint per slice

D) C + temporary rollback branch strategy documented

X) Other (please describe after [Answer]: tag below)

[Answer]: c)

## Question 5
Which security pattern depth should be explicitly modeled for issuer pinning and replay resistance?

A) Issuer allowlist checks only

B) A + nonce/jti replay-check hook interface

C) B + bounded replay store abstraction and expiry policy

D) C + threat-signal counters for anomaly hooks

X) Other (please describe after [Answer]: tag below)

[Answer]: C) B + bounded replay store abstraction and expiry policy.

Rationale:
- Implements practical replay resistance beyond interface-level hooks.
- Keeps security depth aligned to approved NFR hardening scope without forcing full anomaly pipeline complexity.
- Provides explicit, testable design contracts for replay-state lifecycle and expiry behavior.

## Question 6
What failure-mode design pattern should govern trust-policy hook errors?

A) Uniform deny with reason code mapping

B) A + classified error taxonomy (source unavailable, invalid policy, timeout)

C) B + policy-driven retry budget before deny

D) Service-specific fallback behavior

X) Other (please describe after [Answer]: tag below)

[Answer]: B)

## Question 7
What logical component split should be used in NFR design artifacts for this unit?

A) Single auth dependency component only

B) Auth validator + trust evaluator components

C) B + observability adapter component

D) C + policy-source resilience component

X) Other (please describe after [Answer]: tag below)

[Answer]: D) C + policy-source resilience component.

Rationale:
- Aligns with approved resilience pattern (cache-aside with bounded TTL and fail-closed post-expiry).
- Aligns with selected observability depth by keeping observability concerns isolated from core auth logic.
- Improves maintainability and testability by separating validator, trust evaluator, observability adapter, and resilience concerns into explicit components.

## Approval
After filling all answers, reply in chat:
"nfr design plan answers provided"
