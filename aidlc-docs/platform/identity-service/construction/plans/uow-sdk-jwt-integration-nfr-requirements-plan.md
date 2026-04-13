# NFR Requirements Plan - uow-sdk-jwt-integration

## Unit Context
- Unit: uow-sdk-jwt-integration
- Scope: JWT-first SDK/wrapper integration, compatibility-phase asymmetric signing and verifier distribution, tenant-id canonicalization, issuance caller-auth policy, and idempotent local bootstrap behavior.
- Inputs reviewed:
  - aidlc-docs/platform/identity-service/construction/uow-sdk-jwt-integration/functional-design/business-logic-model.md
  - aidlc-docs/platform/identity-service/construction/uow-sdk-jwt-integration/functional-design/business-rules.md
  - aidlc-docs/platform/identity-service/construction/uow-sdk-jwt-integration/functional-design/domain-entities.md
  - aidlc-docs/platform/identity-service/construction/plans/uow-sdk-jwt-integration-migration-checklist.md

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
What p95 latency target should be used for SDK-authenticated identity flows (token issuance request path and key-discovery retrieval under normal load)?

A) <= 25 ms

B) <= 50 ms

C) <= 100 ms

D) Best effort only in this unit

X) Other (please describe after [Answer]: tag below)

[Answer]: C)

Rationale:
- 100 ms p95 is a realistic compatibility-phase target that keeps latency bounded without forcing premature over-optimization during the migration unit.
- It still requires explicit engineering controls (cache strategy, timeout budgets, and instrumentation) and provides a measurable gate for regression checks.
- This target balances delivery speed and reliability before stricter hardening/cutover enforcement in later stages.

## Question 2
What sustained throughput profile should be the baseline for this unit's NFR sizing?

A) 100 RPS sustained

B) 300 RPS sustained

C) 500 RPS sustained

D) Tiered profile aligned to prior unit baseline

X) Other (please describe after [Answer]: tag below)

[Answer]: D)

## Question 3
What availability behavior is required when JWKS/discovery endpoints are temporarily unavailable?

A) Fail closed immediately for JWT verification paths

B) Use bounded last-known-good key cache, then fail closed at cache expiry

C) Allow grace mode with warning logs

D) No explicit policy in this unit

X) Other (please describe after [Answer]: tag below)

[Answer]: B)

## Question 4
What key rotation propagation objective should be required for new signing keys (`kid`) across consumers?

A) Immediate for all new verifications

B) <= 1 minute

C) <= 5 minutes

D) Best effort with no explicit SLO

X) Other (please describe after [Answer]: tag below)

[Answer]: C)

## Question 5
Which verifier distribution mode should be considered mandatory for production-ready compatibility behavior in this unit?

A) Static public key only

B) JWKS only

C) JWKS primary with deterministic static-key fallback

D) Static key primary with optional JWKS

X) Other (please describe after [Answer]: tag below)

[Answer]: C)

Rationale:
- For Unit 3 compatibility phase, JWKS should be the primary verifier source while deterministic static fallback reduces rollout fragility during discovery outages or partial environment drift.
- This aligns with fail-closed safety plus bounded resilience (with explicit precedence and cache controls) rather than silent downgrade behavior.
- It preserves a clean migration path to stricter JWKS-only enforcement in later hardening/cutover stages.

## Question 6
How strict should observability requirements be for JWT compatibility and issuance policy decisions?

A) Structured logs only

B) Logs + metrics (latency, deny counts, mismatch counts)

C) Logs + metrics + tracing with correlation propagation

D) Minimal telemetry in this unit

X) Other (please describe after [Answer]: tag below)

[Answer]: C)

## Question 7
What reliability requirement should apply to `soorma dev` idempotent bootstrap outcomes?

A) Return simple success/failure only

B) Return deterministic outcome codes (`CREATED`, `REUSED`, `FAILED_DRIFT`) and fail closed on protected drift

C) Interactive retries before failure

D) Defer strict behavior to later units

X) Other (please describe after [Answer]: tag below)

[Answer]: B)

## Question 8
What security hardening depth should be required now for issuance caller-auth and override flows?

A) Baseline only (fail-closed + typed errors)

B) A + explicit audit durability requirements for override decisions

C) B + anomaly alert recommendations and threshold guidance

D) Defer to unit 4 hardening

X) Other (please describe after [Answer]: tag below)

[Answer]: C)

## Question 9
What rollout readiness gate is required before enabling broad JWT compatibility behavior in shared services?

A) Unit tests pass

B) Unit + integration happy paths pass

C) B + negative security matrix pass (invalid signature, unknown `kid`, tenant mismatch, unauthorized issue-for-other)

D) C + load validation at selected throughput profile

X) Other (please describe after [Answer]: tag below)

[Answer]: C)

## Approval
After filling all answers, reply in chat:
"nfr requirements plan answers provided"
