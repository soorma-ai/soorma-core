# Unit-1 NFR Requirements Plan

## Unit Context
- Unit: U1 - Shared Identity Dependency (soorma-service-common)
- Scope: shared dependency design and contract quality requirements
- Inputs reviewed:
  - construction/unit-1/functional-design/business-logic-model.md
  - construction/unit-1/functional-design/business-rules.md
  - construction/unit-1/functional-design/domain-entities.md

## NFR Assessment Checklist
- [x] Analyze Unit-1 functional design artifacts
- [x] Identify NFR categories applicable to shared dependency work
- [x] Prepare NFR clarification questions with [Answer] tags
- [x] Resolve all answers and ambiguities
- [x] Generate nfr-requirements.md
- [x] Generate tech-stack-decisions.md
- [x] Perform security-baseline compliance check
- [x] Present NFR Requirements completion for approval

## Clarifying Questions
Please answer each question by filling the letter after [Answer]:.

## Question 1
For request validation performance, what is the acceptable overhead target for `require_user_context` per request in normal conditions?

A) Best effort only; no explicit numeric target

B) Less than 1 ms added processing time per request

C) Less than 5 ms added processing time per request

X) Other (please describe after [Answer]: tag below)

[Answer]: A is enough

## Question 2
How strict should failure-message consistency be across services adopting this dependency?

Note: this is about default messages defined by the shared library contract, not passing custom error text as per-route arguments.

A) Shared constants/messages enforced centrally in soorma-service-common

B) Common semantic guidance only; service-specific message wording allowed

C) Keep messages local per service for flexibility

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 3
For security hardening of validation errors, which logging policy should apply when identity context is missing?

A) Log only generic warning without tenant/user values

B) Log warning with platform tenant only, never service tenant/user

C) No application log entry for expected 400 validation failures

X) Other (please describe after [Answer]: tag below)

[Answer]: B for now.
Rationale:
- In multi-tenant operations, `platform_tenant_id` is useful as a safe support filter key.
- Do not log service-tenant/user identifiers in these validation warnings.
- Tenant-facing troubleshooting strategy (self-service exposure model, redaction, and scoped query APIs) should be designed later as a dedicated cross-service effort.

## Question 4
For maintainability and rollout safety, what test bar should Unit-1 enforce before moving to code generation?

A) Unit tests in shared library only (validation behavior + message checks)

B) Unit tests + one integration-style import/use test from memory service

C) Unit tests + compatibility matrix across all current service consumers

X) Other (please describe after [Answer]: tag below)

[Answer]: A) unit tests in shared lib are enough

## Question 5
What adoption strategy should be recommended for downstream services in this initiative sequence?

A) Memory service first (Unit-2), then reuse pattern documented for others later

B) Update memory and tracker in this initiative to keep parity

C) Update all current consumers immediately in this initiative

X) Other (please describe after [Answer]: tag below)

[Answer]: A) we'll focus on memory service only. not sure if this is applicable to tracker service right now.

## Notes
- Questions are scoped to NFR characteristics for Unit-1 and immediate downstream adoption impact.
- Code changes remain blocked until NFR Requirements stage is completed and approved.
