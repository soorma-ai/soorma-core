# NFR Design Plan - uow-cutover-hardening

## Unit Context
- Unit: uow-cutover-hardening
- Inputs reviewed:
  - aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/nfr-requirements/nfr-requirements.md
  - aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/nfr-requirements/tech-stack-decisions.md
  - aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/functional-design/business-logic-model.md
  - aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/functional-design/business-rules.md

## Execution Checklist
- [x] Step 1 - Analyze NFR requirements and hard-cutover constraints
- [x] Step 2 - Draft NFR design plan and question set
- [x] Step 3 - Store this NFR design plan file
- [x] Step 4 - Collect and validate all answers
- [x] Step 5 - Generate NFR design artifacts
- [x] Step 6 - Present NFR Design completion gate

## NFR Design Clarifying Questions
Please answer each question by filling the [Answer]: field.

## Question 1
For verifier source behavior under hard cutover, what explicit design pattern should be modeled?

A) Strict JWKS/public-key resolution with bounded cache and deterministic fail-closed behavior after cache expiry

B) JWKS primary with permissive dynamic fallback to any available verifier source

C) Static key primary and JWKS secondary

D) Environment-specific behavior with no fixed precedence

X) Other (please describe after [Answer]: tag below)

[Answer]: A)

## Question 2
For unknown kid and invalid signature handling, what design-level policy should be enforced?

A) Immediate fail-closed with typed reason codes and structured telemetry

B) Retry verification using alternate keys before deny

C) Warning-only in non-production paths

D) Deferred enforcement to Build and Test

X) Other (please describe after [Answer]: tag below)

[Answer]: A)

## Question 3
For key rotation propagation objective (<=5 minutes), what refresh model should be explicit in design?

A) Fixed polling interval only

B) Event-triggered invalidation plus bounded polling backstop

C) Manual reload operations only

D) Opportunistic refresh on verification miss only

X) Other (please describe after [Answer]: tag below)

[Answer]: B)

## Question 4
For alerting requirements (denial spikes, override anomalies, unknown kid/signature failures), what implementation expectation should design encode?

A) Define canonical alert signal contracts and thresholds now; tool-specific wiring can use existing stack

B) Define signals only, no threshold guidance

C) Defer all alert details to future unit

D) Add mandatory new monitoring vendor dependency

X) Other (please describe after [Answer]: tag below)

[Answer]: A)

## Question 5
For rollback reliability under hard cutover, what NFR design artifact boundary should be mandatory?

A) Deterministic release/deployment rollback runbook with entry criteria, execution steps, and post-rollback verification matrix

B) Code revert guidance only

C) Best-effort operator notes only

D) No rollback design in this unit

X) Other (please describe after [Answer]: tag below)

[Answer]: A)

## Question 6
For local development bootstrap alignment, what design contract should be explicit?

A) `soorma dev` asymmetric bootstrap default with RS256 keypair/JWKS automation and explicit non-default HS256 test-mode path

B) HS256 default local path retained permanently

C) Either mode default without policy preference

D) Defer local bootstrap design to a later unit

X) Other (please describe after [Answer]: tag below)

[Answer]: A)

## Question 7
For delegated issuer OIDC/JWKS finalization in this unit, what design scope guard should be enforced?

A) Bounded implementation limited to trust metadata validation, key retrieval/cache/rotation handling, and policy-gated delegated claim acceptance

B) Expand scope to include new delegated product surface in this unit

C) Defer all delegated issuer finalization to future work

D) Runtime-selectable relaxed trust policy without strict constraints

X) Other (please describe after [Answer]: tag below)

[Answer]: A)

## Approval
After filling all answers, reply in chat:
"nfr design plan answers provided"