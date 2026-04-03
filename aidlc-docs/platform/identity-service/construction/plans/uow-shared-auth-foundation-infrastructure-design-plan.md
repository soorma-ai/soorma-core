# Infrastructure Design Plan - uow-shared-auth-foundation

## Unit Context
- Unit: uow-shared-auth-foundation
- Inputs reviewed:
  - aidlc-docs/platform/identity-service/construction/uow-shared-auth-foundation/functional-design/business-logic-model.md
  - aidlc-docs/platform/identity-service/construction/uow-shared-auth-foundation/functional-design/business-rules.md
  - aidlc-docs/platform/identity-service/construction/uow-shared-auth-foundation/nfr-design/nfr-design-patterns.md
  - aidlc-docs/platform/identity-service/construction/uow-shared-auth-foundation/nfr-design/logical-components.md

## Execution Checklist
- [x] Step 1 - Analyze design artifacts and infrastructure implications
- [x] Step 2 - Draft infrastructure design plan and question set
- [x] Step 3 - Store this infrastructure design plan file
- [ ] Step 4 - Collect and validate all answers
- [ ] Step 5 - Generate infrastructure design artifacts
- [ ] Step 6 - Present Infrastructure Design completion gate

## Infrastructure Design Clarifying Questions
Please answer each question by filling the [Answer]: field.

## Question 1
What deployment model should be treated as the primary reference for this open-core unit?

A) Local/self-hosted single-node baseline

B) Local baseline + cloud-ready reference (provider-neutral)

C) Managed cloud-first reference (single provider)

D) Multi-cloud baseline from day one

X) Other (please describe after [Answer]: tag below)

[Answer]: B) Local baseline + cloud-ready reference (provider-neutral).

Rationale:
- Preserves interoperability and portability without committing to multi-cloud operational complexity too early.
- Avoids overengineering in pre-adoption phase while still keeping cloud mapping straightforward later.
- Supports open-core adopters with varied deployment targets through provider-neutral design plus optional provider mapping appendix.

## Question 2
Where should trust-policy and replay-state persistence be mapped by default in infrastructure design?

A) In-process memory only (ephemeral)

B) In-memory + relational DB persistence

C) In-memory + shared cache + relational DB source of truth

D) External policy service + dedicated replay datastore

X) Other (please describe after [Answer]: tag below)

[Answer]: B) In-memory + relational DB persistence.

Rationale:
- Provides durable source of truth for trust-policy and replay-state while keeping baseline infrastructure simple.
- Supports correctness across restarts and multi-instance operation without introducing immediate shared-cache complexity.
- Leaves clear evolution path to option C (shared cache + DB) as a future enhancement when scale/latency evidence justifies it.

## Question 3
What should be the default compute/runtime mapping for services consuming this auth dependency?

A) Single process per service without sidecars

B) Containerized services with standard app runtime only

C) Containerized services + optional sidecar for observability/export

D) Serverless runtime baseline

X) Other (please describe after [Answer]: tag below)

[Answer]: X) Container-serverless baseline now (for example Cloud Run / ECS-style container services), with option to migrate to Kubernetes later if scale/operational needs justify it.

Rationale:
- Aligns with pre-release open-core simplicity and fast iteration.
- Keeps runtime model container-centric and portable across providers.
- Avoids premature Kubernetes operational overhead while preserving migration path.

## Question 4
How should observability infrastructure be mapped for trace/log/metric correlation?

A) Local logging only

B) Central logs + metrics, optional tracing

C) Central logs + metrics + tracing (recommended baseline)

D) C + security event stream for anomaly processing

X) Other (please describe after [Answer]: tag below)

[Answer]:

## Question 5
What networking boundary pattern should be assumed for auth-sensitive service ingress?

A) Direct internal service ingress only

B) Service ingress behind shared gateway/reverse proxy

C) B + mTLS for service-to-service traffic where supported

D) Public ingress allowed for all service endpoints

X) Other (please describe after [Answer]: tag below)

[Answer]:

## Question 6
For open-core portability, how should infrastructure assumptions be documented?

A) Strictly provider-neutral with optional provider mappings appendix

B) Provider-specific examples only

C) Separate documents per provider

D) Minimal infra documentation at this stage

X) Other (please describe after [Answer]: tag below)

[Answer]:

## Question 7
Given approved compatibility override and direct refactor strategy, what deployment safety gate should be required before advancing to Code Generation?

A) Single full-system integration test run

B) Per-slice deployment simulation + regression checkpoint

C) B + rollback playbook validation

D) B + C + environment smoke checks for each impacted service

X) Other (please describe after [Answer]: tag below)

[Answer]:

## Approval
After filling all answers, reply in chat:
"infrastructure design plan answers provided"
