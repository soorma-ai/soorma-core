# NFR Requirements Plan - uow-shared-auth-foundation

## Unit Context
- Unit: uow-shared-auth-foundation
- Scope: shared auth dependency behavior for coexistence mode, trust gating, telemetry, and deterministic rollout behavior.
- Inputs reviewed:
  - aidlc-docs/platform/identity-service/construction/uow-shared-auth-foundation/functional-design/business-logic-model.md
  - aidlc-docs/platform/identity-service/construction/uow-shared-auth-foundation/functional-design/business-rules.md
  - aidlc-docs/platform/identity-service/construction/uow-shared-auth-foundation/functional-design/domain-entities.md

## Execution Checklist
- [x] Step 1 - Analyze functional design artifacts
- [x] Step 2 - Draft NFR assessment plan and question set
- [x] Step 3 - Store this NFR requirements plan file
- [x] Step 4 - Collect and validate all answers
- [x] Step 5 - Generate NFR requirements artifacts
- [x] Step 6 - Present NFR Requirements completion gate

## NFR Clarifying Questions
Please answer each question by filling the [Answer]: field.

## Question 1
What latency SLO should be targeted for auth dependency processing overhead (excluding downstream business logic) at p95?

A) <= 5 ms

B) <= 10 ms

C) <= 20 ms

D) Best effort only for this unit

X) Other (please describe after [Answer]: tag below)

[Answer]: D)

## Question 2
What throughput assumption should size this unit's baseline performance validation?

A) Up to 100 RPS per service instance

B) Up to 500 RPS per service instance

C) Up to 1000 RPS per service instance

D) Define profile-based tiers and validate each

X) Other (please describe after [Answer]: tag below)

[Answer]: D) Define profile-based tiers and validate each.

Recommended tiers (per service instance):
- Tier 1 (Low): 100 RPS steady
- Tier 2 (Medium): 500 RPS steady
- Tier 3 (High): 1000 RPS steady
- Optional Burst Tier: 1500 RPS for short burst window

Validation model:
- Execute dedicated performance acceptance runs per tier (not unit tests).
- For each tier, run sustained load window and verify p95 auth-overhead latency, error rate, and resource stability.
- Include negative-path assertions under load (invalid JWT, expired JWT, trust-policy deny) to confirm deterministic fail-closed behavior.

Rationale:
- Single-point throughput targets can hide scaling cliff behavior.
- Tiered validation gives better rollout confidence for coexistence and later header-removal cutover.
- Matches this initiative's requirement for full practical coverage across critical auth paths.

## Question 3
What availability expectation applies to auth dependency behavior?

A) Match service availability target; no independent SLO for dependency layer

B) Dependency layer must sustain 99.9% success for valid requests

C) Dependency layer must sustain 99.99% success for valid requests

D) Not measured in this unit

X) Other (please describe after [Answer]: tag below)

[Answer]: A)

## Question 4
What resilience strategy is required when trust-policy backing data (for example issuer policy source) is temporarily unavailable?

A) Fail closed for all delegated flows; allow only non-delegated flows with valid local checks

B) Fail closed for all requests

C) Cached last-known-good policy for bounded TTL, then fail closed

D) Grace mode with warnings

X) Other (please describe after [Answer]: tag below)

[Answer]: C)

## Question 5
How strict should observability requirements be for this unit?

A) Structured logs only

B) Logs + metrics (latency, deny counts, provenance counts)

C) Logs + metrics + traces with correlation propagation

D) Minimal telemetry in this unit

X) Other (please describe after [Answer]: tag below)

[Answer]: C)

## Question 6
What data handling requirement applies to sensitive auth data in logs and telemetry?

A) Never log tokens; log only high-level reason codes

B) A + redact sensitive claim fields beyond tenant/user IDs

C) B + enforce structured log schema validation in CI

D) Service-defined logging discretion

X) Other (please describe after [Answer]: tag below)

[Answer]: C)

## Question 7
Which rollout verification standard is required before header-auth removal phase can begin?

A) Unit and integration tests pass

B) A + coexistence regression matrix pass

C) B + synthetic production-like load validation

D) B + staged canary validation in integration environment

X) Other (please describe after [Answer]: tag below)

[Answer]: B) A + coexistence regression matrix pass.

Rationale and details:
- This is the strongest portable baseline for an open-core project without assuming canary infrastructure.
- It avoids hard-coding deployment/runtime performance assumptions as global mandatory cutover gates.
- Coexistence regression matrix is mandatory before header-auth removal and must cover at minimum:
  - JWT-present authoritative path
  - Header-only coexistence path (where still supported)
  - Invalid JWT fail-fast behavior (no header fallback)
  - 401 vs 403 semantics
  - Delegated trust-allow and trust-deny scenarios

Extension guidance:
- Synthetic load validation and canary-style validation remain recommended profile-specific extensions when adopters define reference runtime/deployment profiles.

## Question 8
What compatibility requirement should be enforced for existing consuming services during this unit?

A) Zero route signature/DI call-site changes

B) Allow additive optional parameters only

C) Permit refactors if backward wrappers provided

D) No compatibility constraints

X) Other (please describe after [Answer]: tag below)

[Answer]: D) No compatibility constraints.

Rationale and details:
- Pre-release open-core phase with all impacted soorma-core services in scope for coordinated updates.
- No external stable-contract dependency is assumed for these internal integration paths at this stage.
- Prefer direct refactor over temporary compatibility adapters/wrappers to reduce complexity.
- Risk control: enforce strong regression matrix across all impacted services before progressing to header-auth removal.

## Question 9
What security hardening depth should this unit commit to now?

A) Baseline only (401/403 semantics, fail-closed, safe logs)

B) A + issuer pinning policy checks and replay protection hooks

C) B + anomaly detection counters and alert thresholds defined

D) Defer hardening to later unit

X) Other (please describe after [Answer]: tag below)

[Answer]: B)

## Question 10
What test coverage target should be documented as NFR for this unit?

A) Risk-based coverage without numeric target

B) >= 80% line coverage for dependency module

C) >= 90% line coverage + branch coverage on critical auth paths

D) Full practical coverage on all critical auth branches with explicit deny-path tests

X) Other (please describe after [Answer]: tag below)

[Answer]: D)

## Approval
After filling all answers, reply in chat:
"nfr requirements plan answers provided"
