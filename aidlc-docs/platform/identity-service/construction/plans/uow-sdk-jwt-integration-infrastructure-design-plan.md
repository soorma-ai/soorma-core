# Infrastructure Design Plan - uow-sdk-jwt-integration

## Unit Context
- Unit: uow-sdk-jwt-integration
- Inputs reviewed:
  - aidlc-docs/platform/identity-service/construction/uow-sdk-jwt-integration/functional-design/business-logic-model.md
  - aidlc-docs/platform/identity-service/construction/uow-sdk-jwt-integration/functional-design/business-rules.md
  - aidlc-docs/platform/identity-service/construction/uow-sdk-jwt-integration/functional-design/domain-entities.md
  - aidlc-docs/platform/identity-service/construction/uow-sdk-jwt-integration/nfr-design/nfr-design-patterns.md
  - aidlc-docs/platform/identity-service/construction/uow-sdk-jwt-integration/nfr-design/logical-components.md

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
What deployment baseline should this unit assume for identity-service JWKS publication and verifier consumption?

A) Local/self-hosted single-node baseline only

B) Local baseline + provider-neutral cloud-ready reference

C) Single cloud-provider-first reference only

D) Multi-cloud baseline from day one

X) Other (please describe after [Answer]: tag below)

[Answer]: B)

Rationale:
- Aligns with Unit 2 baseline: local/self-hosted portability first, plus cloud-ready provider-neutral design.
- Preserves open-core portability while allowing one concrete provider reference implementation (GCP) in infrastructure artifacts.
- Avoids premature provider lock-in while keeping deployment guidance actionable.

## Question 2
Where should verifier material and discovery cache state be hosted by default for this unit?

A) In-process cache only with bounded TTL

B) In-process cache + relational persistence for key metadata state

C) In-process + shared cache service (e.g., Redis) from day one

D) External managed verifier-discovery cache service only

X) Other (please describe after [Answer]: tag below)

[Answer]: B)

Rationale:
- Aligns with Unit 2 persistence posture: in-process bounded cache for fast-path resolution with relational durability for key/discovery metadata continuity.
- Preserves deterministic fail-closed behavior after bounded cache validity without forcing day-one shared cache complexity.
- Keeps clear scale-up path to shared cache when load evidence justifies it.

## Question 3
What event infrastructure assumption should back key-rotation invalidation propagation?

A) Internal in-process signaling only

B) Existing platform event bus/topic with bounded polling backstop

C) Dedicated new rotation messaging infrastructure in this unit

D) No event propagation; polling-only model

X) Other (please describe after [Answer]: tag below)

[Answer]: B)

Rationale:
- Aligns with Unit 3 NFR pattern for event-triggered invalidation plus bounded polling backstop.
- Reuses existing platform event bus/topic instead of introducing new infrastructure for this unit.
- Preserves rapid convergence on key rotation with resilient fallback if event delivery is delayed.

## Question 4
How should JWKS publication endpoint exposure be mapped at network boundary?

A) Internal-only endpoint not externally reachable

B) Gateway/reverse-proxy published endpoint with controlled external reachability

C) Direct public endpoint on service without gateway boundary

D) Sidecar-only endpoint exposed through mesh controls

X) Other (please describe after [Answer]: tag below)

[Answer]: B)

Rationale:
- Aligns with Unit 2 gateway/reverse-proxy boundary model for externally reachable identity paths.
- Preserves controlled external reachability while avoiding unmanaged direct public service exposure.
- Keeps JWKS publication compatible with existing ingress policy controls.

## Question 5
What key management baseline should infrastructure design assume for Unit 3 compatibility phase?

A) Service-managed signing keys only in local config/DB

B) External KMS-backed key management in production profile + local bootstrap fallback

C) HSM-only baseline for all environments

D) Provider-specific signing service only

X) Other (please describe after [Answer]: tag below)

[Answer]: B)

Rationale:
- Aligns with Unit 2 key-management posture: production KMS-backed keys with bootstrap fallback for local/self-hosted startup.
- Maintains secure production trajectory without blocking developer bootstrap on KMS prerequisites.
- Supports compatibility-phase rollout while preserving migration path to stricter hardened profile controls.

## Question 6
What observability infrastructure baseline should be required for this unit's decision traces and audit paths?

A) Central logs only

B) Logs + metrics

C) Logs + metrics + tracing

D) C + dedicated security-event stream/alarm pipeline in this unit

X) Other (please describe after [Answer]: tag below)

[Answer]: C)

Rationale:
- Aligns directly with approved Unit 3 NFR observability depth (logs + metrics + tracing with correlation propagation).
- Matches Unit 2 baseline and keeps decision-path diagnostics actionable for verifier-source, override, and audit branches.
- Avoids under-instrumentation during compatibility-phase cutover risk.

## Question 7
What deployment safety gate should be required before moving this unit to Code Generation?

A) Unit tests only

B) Unit + integration happy paths

C) B + mandatory negative security matrix pass

D) C + selected throughput profile validation for verifier/discovery paths

X) Other (please describe after [Answer]: tag below)

[Answer]: D)

Rationale:
- Stays aligned with Unit 2 strong deployment safety posture while including Unit 3-specific verifier/discovery performance risk checks.
- Ensures negative security matrix is blocking and validated before rollout expansion.
- Adds selected throughput profile validation to reduce compatibility-phase regressions under realistic load.

## Approval
After filling all answers, reply in chat:
"infrastructure design plan answers provided"
