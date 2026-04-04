# NFR Requirements Plan - uow-identity-core-domain

## Unit Context
- Unit: uow-identity-core-domain
- Scope: identity core domain APIs for onboarding, principal lifecycle, delegated trust registration, issuance decisions, mapping/binding policy enforcement, and audit events.
- Inputs reviewed:
  - aidlc-docs/platform/identity-service/construction/uow-identity-core-domain/functional-design/business-logic-model.md
  - aidlc-docs/platform/identity-service/construction/uow-identity-core-domain/functional-design/business-rules.md
  - aidlc-docs/platform/identity-service/construction/uow-identity-core-domain/functional-design/domain-entities.md

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
What p95 latency target should identity service API operations meet for standard successful paths (excluding external gateway/network latency)?

A) <= 20 ms

B) <= 50 ms

C) <= 100 ms

D) Best-effort only in this unit

X) Other (please describe after [Answer]: tag below)

[Answer]: D)

## Question 2
What baseline throughput target should be used for NFR sizing per identity-service instance?

A) 100 RPS sustained

B) 300 RPS sustained

C) 500 RPS sustained

D) Tiered profile (low/medium/high)

X) Other (please describe after [Answer]: tag below)

[Answer]: D) use same profiles as defined in uow-shared-auth-foundation

## Question 3
What availability expectation should be documented for identity core operations?

A) Match service-wide target only (no separate identity NFR)

B) 99.9% success for valid requests

C) 99.99% success for valid requests

D) Not measured in this unit

X) Other (please describe after [Answer]: tag below)

[Answer]: A)

## Question 4
If delegated issuer metadata or mapping-policy backing data is temporarily unavailable, what resilience behavior is required?

A) Fail closed for delegated flows; allow platform-principal issuance paths with local-valid checks

B) Fail closed for all issuance/authz operations

C) Use bounded last-known-good cache for delegated policy, then fail closed

D) Grace mode with warning logs only

X) Other (please describe after [Answer]: tag below)

[Answer]: C) use same cache TTL strategy as defined in uow-shared-auth-foundation

## Question 5
What key-rotation propagation requirement should apply for delegated issuer trust material changes?

A) Effective immediately for all new validations/issuance checks

B) Effective within 1 minute

C) Effective within 5 minutes

D) Best-effort with no explicit SLO

X) Other (please describe after [Answer]: tag below)

[Answer]: A)

## Question 6
How strict should observability requirements be for this unit?

A) Structured logs only

B) Logs + metrics (latency, error/deny counts, collision counters)

C) Logs + metrics + distributed tracing with correlation propagation

D) Minimal telemetry in this unit

X) Other (please describe after [Answer]: tag below)

[Answer]: C)

## Question 7
Which audit durability requirement should be enforced for this unit?

A) Best-effort for all audit writes

B) Fail-closed for critical mutations only; best-effort for low-risk updates

C) Fail-closed for all mutation and issuance decisions

D) Defer durability policy to later unit

X) Other (please describe after [Answer]: tag below)

[Answer]: B) keep consistent with audit durability defined in function design for this unit

## Question 8
What rollout readiness gate should be required before broad delegated issuance enablement?

A) Unit and integration tests pass

B) A + negative security regression matrix pass

C) B + load validation at selected throughput profile

D) B + staged canary-style validation in integration environment

X) Other (please describe after [Answer]: tag below)

[Answer]: B)

## Question 9
What security hardening depth should be captured now for token misuse and replay protection?

A) Baseline only (typed errors, fail-closed, safe logging)

B) A + replay-protection hooks and nonce/jti validation controls

C) B + anomaly thresholds and alert recommendations

D) Defer to cutover-hardening unit

X) Other (please describe after [Answer]: tag below)

[Answer]: X) use same strategy as defined in uow-shared-auth-foundation

## Approval
After filling all answers, reply in chat:
"nfr requirements plan answers provided"
