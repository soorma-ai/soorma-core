# NFR Requirements Plan - uow-cutover-hardening

## Unit Context
- Unit: uow-cutover-hardening
- Scope: Final JWT-only cutover hardening for secured ingress, issuance authorization and override policy controls, canonical tenant contract convergence, RS256 plus JWKS verification posture, rollback runbook readiness, and delegated issuer OIDC/JWKS finalization.
- Inputs reviewed:
  - aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/functional-design/business-logic-model.md
  - aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/functional-design/business-rules.md
  - aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/functional-design/domain-entities.md
  - aidlc-docs/platform/identity-service/construction/plans/uow-cutover-hardening-migration-checklist.md

## Execution Checklist
- [x] Step 1 - Analyze functional design artifacts and hard-cutover constraints
- [x] Step 2 - Draft NFR assessment plan and question set
- [x] Step 3 - Store this NFR requirements plan file
- [x] Step 4 - Collect and validate all answers
- [x] Step 5 - Generate NFR requirements artifacts
- [x] Step 6 - Present NFR Requirements completion gate

## NFR Clarifying Questions
Please answer each question by filling the [Answer]: field.

Prefill note:
- Q1 through Q5 are prefilled from the approved uow-sdk-jwt-integration NFR baseline where there is direct mapping.
- Q6 through Q9 are intentionally left for user confirmation due policy/scope sensitivity for cutover-hardening.

## Question 1
What p95 latency target should be enforced for secured JWT-authenticated request paths after cutover (excluding public health/discovery endpoints)?

A) <= 50 ms

B) <= 100 ms

C) <= 150 ms

D) Best effort only in this unit

X) Other (please describe after [Answer]: tag below)

[Answer]: B)

## Question 2
What throughput baseline should be used for NFR sizing and validation of cutover paths?

A) 100 RPS sustained

B) 500 RPS sustained

C) 1000 RPS sustained

D) Tiered profile (100/500/1000 sustained + bounded burst window)

X) Other (please describe after [Answer]: tag below)

[Answer]: D)

## Question 3
What availability policy should apply when JWKS/OIDC retrieval is temporarily unavailable?

A) Fail closed immediately for all verification paths

B) Use bounded last-known-good cache, then fail closed at cache expiry

C) Allow warning-mode grace behavior before denial

D) No explicit policy in this unit

X) Other (please describe after [Answer]: tag below)

[Answer]: B)

## Question 4
What key rotation propagation objective should be required for new signing keys (`kid`) across consumers?

A) Immediate (no explicit objective)

B) <= 1 minute

C) <= 5 minutes

D) Best effort only

X) Other (please describe after [Answer]: tag below)

[Answer]: C)

## Question 5
What observability depth is required for cutover auth decisions (legacy denial, override decisions, key resolution outcomes)?

A) Structured logs only

B) Logs + metrics (latency, deny counts, unknown kid counts)

C) Logs + metrics + tracing with correlation propagation

D) Minimal telemetry in this unit

X) Other (please describe after [Answer]: tag below)

[Answer]: C)

## Question 6
What alerting expectation should be set for security-significant decision patterns?

A) No alerts in this unit

B) Alert on repeated legacy/header denial spikes only

C) Alert on denial spikes plus admin-override anomaly patterns and unknown kid/signature failure spikes

D) Document recommendations only, defer alert wiring

X) Other (please describe after [Answer]: tag below)

[Answer]: C)

Clarification note:
- Selecting B or C defines alerting requirements, not a mandatory new vendor/tool dependency.
- Alert implementation can use existing observability tooling already present in soorma-core environments.
- If alert wiring is not available in this unit, choose D and carry explicit alert recommendations forward.

## Question 7
What reliability requirement should apply to rollback readiness for hard cutover?

A) Release/deployment rollback runbook with deterministic entry criteria, execution steps, and post-rollback verification checks

B) Code revert guidance only

C) Best effort operational notes only

D) Defer rollback readiness to Build and Test stage only

X) Other (please describe after [Answer]: tag below)

[Answer]: A)

## Question 8
What local development bootstrap expectation should apply under RS256 hard-cutover policy?

A) soorma dev defaults to asymmetric bootstrap automation (generate/seed keypair + JWKS wiring), no HS256 default path

B) Keep HS256 local default for convenience

C) Allow either mode by default with no policy preference

D) Defer local bootstrap policy to a future unit

X) Other (please describe after [Answer]: tag below)

[Answer]: A)

## Question 9
How should delegated issuer OIDC/JWKS finalization be treated in NFR scope for this unit?

A) In-scope now with bounded implementation and full NFR controls

B) Defer to future work with explicit scope re-baselining

C) Partial implementation now, partial deferral

D) Runtime-selectable behavior without strict policy constraints

X) Other (please describe after [Answer]: tag below)

[Answer]: A)

## Approval
After filling all answers, reply in chat:
"nfr requirements plan answers provided"