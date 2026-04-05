# Infrastructure Design Plan - uow-identity-core-domain

## Unit Context
- Unit: uow-identity-core-domain
- Inputs reviewed:
  - aidlc-docs/platform/identity-service/construction/uow-identity-core-domain/functional-design/business-logic-model.md
  - aidlc-docs/platform/identity-service/construction/uow-identity-core-domain/functional-design/business-rules.md
  - aidlc-docs/platform/identity-service/construction/uow-identity-core-domain/nfr-design/nfr-design-patterns.md
  - aidlc-docs/platform/identity-service/construction/uow-identity-core-domain/nfr-design/logical-components.md

## Execution Checklist
- [x] Step 1 - Analyze design artifacts and infrastructure implications
- [x] Step 2 - Draft infrastructure design plan and question set
- [x] Step 3 - Store this infrastructure design plan file
- [x] Step 4 - Collect and validate all answers
- [x] Step 5 - Generate infrastructure design artifacts
- [x] Step 6 - Present Infrastructure Design completion gate

## Infrastructure Design Clarifying Questions
Please answer each question by filling the [Answer]: field.

## Question 1
What deployment model should be treated as primary baseline for this unit?

A) Local/self-hosted single-node baseline only

B) Local baseline + cloud-ready provider-neutral reference

C) Single cloud-provider-first reference

D) Multi-cloud baseline from day one

X) Other (please describe after [Answer]: tag below)

[Answer]: B)

Rationale:
- Aligns with approved shared-auth-foundation baseline for open-core portability.
- Keeps local/self-hosted bootstrap simple while preserving cloud-ready mapping.

## Question 2
Where should identity-core persistence (tenant domain, principals, issuer trust metadata, mapping bindings) be mapped by default?

A) Single relational database as source of truth

B) Relational DB + shared cache for read acceleration

C) Split data stores (relational + document)

D) External managed identity datastore only

X) Other (please describe after [Answer]: tag below)

[Answer]: A)

Rationale:
- Identity-core entities use relational DB as source of truth for consistency and transactional integrity.
- Shared-cache acceleration remains optional and can be added later when load evidence justifies it.

## Question 3
What key and signing-material management baseline should infrastructure design assume?

A) Service-managed keys in DB/config only

B) External KMS-backed key management with rotation integration

C) B + HSM-backed protection where available

D) Provider-specific signing service only

X) Other (please describe after [Answer]: tag below)

[Answer]: X) Production profile uses external KMS-backed key management with rotation integration; local/self-hosted bootstrap may use service-managed keys until KMS is configured.

Rationale:
- Preserves secure production posture while avoiding hard bootstrap dependency for open-core adopters.
- Stays consistent with prior provider-neutral/bootstrap-first decisions.

## Question 4
What ingress/network boundary should be assumed for identity-core APIs?

A) Internal-only service ingress

B) Shared gateway/reverse-proxy boundary for externally reachable paths

C) B + mTLS for service-to-service traffic where supported

D) Direct public ingress on service endpoints

X) Other (please describe after [Answer]: tag below)

[Answer]: C)

Rationale:
- Matches shared-auth-foundation networking decision: gateway boundary for external reachability plus mTLS where supported.

## Question 5
How should replay-protection and delegated-policy cache infrastructure be mapped?

A) In-process cache only

B) Shared cache service with bounded TTL policies

C) B + durable fallback store for resilience

D) External dedicated anti-replay service

X) Other (please describe after [Answer]: tag below)

[Answer]: X) Baseline uses in-process cache with bounded TTL plus relational DB durability for replay/policy state; shared cache is an optional scale-up enhancement.

Rationale:
- Aligns to shared-auth-foundation persistence baseline while preserving NFR fail-closed behavior.

## Question 6
What observability infrastructure baseline should be required?

A) Central logs only

B) Logs + metrics

C) Logs + metrics + tracing

D) C + security event stream/alarm pipeline

X) Other (please describe after [Answer]: tag below)

[Answer]: C)

## Question 7
What deployment safety gate should be required before moving to Code Generation for this unit?

A) Single integration test run

B) Per-slice deployment simulation + regression checkpoint

C) B + rollback playbook validation

D) C + environment smoke checks for each impacted identity path

X) Other (please describe after [Answer]: tag below)

[Answer]: D)

## Approval
After filling all answers, reply in chat:
"infrastructure design plan answers provided"
