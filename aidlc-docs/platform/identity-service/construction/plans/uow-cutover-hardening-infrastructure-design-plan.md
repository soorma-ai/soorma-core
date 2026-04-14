# Infrastructure Design Plan - uow-cutover-hardening

## Unit Context
- Unit: uow-cutover-hardening
- Inputs reviewed:
  - aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/functional-design/business-logic-model.md
  - aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/functional-design/business-rules.md
  - aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/nfr-design/nfr-design-patterns.md
  - aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/nfr-design/logical-components.md
  - aidlc-docs/platform/identity-service/construction/plans/uow-cutover-hardening-migration-checklist.md

## Execution Checklist
- [x] Step 1 - Analyze functional and NFR design artifacts for infrastructure mapping needs
- [x] Step 2 - Draft infrastructure design plan and question set
- [x] Step 3 - Store this infrastructure design plan file
- [ ] Step 4 - Collect and validate all answers
- [ ] Step 5 - Generate infrastructure design artifacts
- [ ] Step 6 - Present Infrastructure Design completion gate

## Infrastructure Design Clarifying Questions
Please answer each question by filling the [Answer]: field.

## Question 1
Which deployment rollout strategy should be the default for hard-cutover releases of identity-service?

A) Canary with staged traffic shift and automated rollback triggers

B) Blue/green full-environment switch with manual cutover checkpoint

C) Rolling update with fixed batch sizes and manual rollback only

D) Single-step in-place deployment for all environments

X) Other (please describe after [Answer]: tag below)

[Answer]:

## Question 2
For JWKS/key material resilience, where should the last-known-good verifier cache live in production?

A) In-process memory cache per service instance with bounded TTL and deterministic expiry handling

B) Shared distributed cache service (for example Redis) as primary verifier cache

C) Database-backed cache table with read-through behavior

D) Filesystem-based local cache persisted across restarts

X) Other (please describe after [Answer]: tag below)

[Answer]:

## Question 3
For key rotation propagation (<=5 minutes objective), which invalidation transport should infrastructure assume?

A) Existing event bus topic-based invalidation plus periodic polling backstop

B) Polling-only refresh with no event-driven invalidation

C) Manual operator-triggered refresh only

D) External webhook callbacks as primary invalidation source

X) Other (please describe after [Answer]: tag below)

[Answer]:

## Question 4
For delegated issuer OIDC/JWKS trust retrieval, what network boundary policy should be modeled?

A) Explicit issuer allowlist and egress restriction policy per environment

B) Broad outbound internet access with application-level issuer filtering only

C) Environment-specific ad hoc outbound rules without centralized policy

D) No outbound retrieval in runtime; keys are manually synced offline

X) Other (please describe after [Answer]: tag below)

[Answer]:

## Question 5
For security telemetry and alerting signals in this unit, what infrastructure sink should be the baseline?

A) Existing centralized logs/metrics/tracing stack with defined alert contracts and thresholds

B) Logs only for this unit, defer metrics/tracing to later work

C) Standalone new monitoring vendor introduced only for identity cutover signals

D) Local service logs only, no centralized sink

X) Other (please describe after [Answer]: tag below)

[Answer]:

## Question 6
For rollback readiness, where should the deterministic rollback runbook execution controls be anchored?

A) CI/CD pipeline stage gates with pre-cutover and post-rollback verification steps

B) Manual wiki procedure outside deployment tooling

C) Runtime admin endpoint-driven rollback controls

D) On-call operator discretion only with no formalized gate

X) Other (please describe after [Answer]: tag below)

[Answer]:

## Question 7
For local `soorma dev` asymmetric bootstrap, what infrastructure artifact boundary should be explicit?

A) Automated ephemeral keypair and JWKS bootstrap artifacts generated per local environment instance

B) Shared long-lived local key material checked into repository

C) Manual key setup by each developer with no automated artifact generation

D) Continue HS256 default locally and defer asymmetric bootstrap

X) Other (please describe after [Answer]: tag below)

[Answer]:

## Approval
After filling all answers, reply in chat:
"infrastructure design plan answers provided"