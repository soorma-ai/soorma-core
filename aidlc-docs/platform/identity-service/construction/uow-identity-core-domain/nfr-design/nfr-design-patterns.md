# NFR Design Patterns - uow-identity-core-domain

## Purpose
Translate approved NFR requirements into concrete design patterns for resilience, key-rotation propagation, observability, durability, rollout safety, and security hardening.

## Pattern ND-1: Delegated Policy Resilience (Inherited Strategy)
- Decision source: Q1 uses shared-auth-foundation strategy.
- Pattern: cache-aside with bounded TTL and strict fail-closed post-expiry.
- Behavior:
  - During backing-source outage and valid cache window: serve last-known-good policy.
  - After TTL expiry: deny delegated trust-dependent operations fail-closed.

## Pattern ND-2: Key-Rotation Propagation
- Decision source: Q2 = C.
- Pattern: hybrid atomic pointer swap + event invalidation signal.
- Behavior:
  - Local validation path switches to new keyset via atomic pointer swap.
  - Distributed consumers converge rapidly via invalidation event.
- NFR alignment:
  - Supports immediate-effect requirement for new validations/issuance checks.

## Pattern ND-3: Tracing and Observability Boundary (Inherited Depth)
- Decision source: Q3 uses shared-auth-foundation observability strategy.
- Effective boundary: per-decision structured event span correlation.
- Required tracing points:
  - request entry/exit
  - trust evaluation
  - mapping/binding evaluation
  - collision and audit decision paths

## Pattern ND-4: Audit Durability Split
- Decision source: Q4 = B.
- Pattern: dual-path writer model.
- Components:
  - Critical transactional writer (fail-closed for critical mutations)
  - Best-effort async writer (low-risk updates)
- Benefits:
  - Preserves mutation safety for high-risk trust/lifecycle operations.
  - Avoids excessive operational friction for low-risk event writes.

## Pattern ND-5: Collision Governance Pattern
- Decision source: Q5 = C.
- Pattern: dedicated collision policy evaluator + override approval gateway.
- Responsibilities:
  - Evaluator enforces deterministic rules and default rejection.
  - Override gateway controls explicit remap approval workflow.
- Constraint:
  - No silent canonical remap path.

## Pattern ND-6: Typed Error Contract Pattern
- Decision source: Q6 = C.
- Pattern: tiered taxonomy + stable public error catalog with versioned compatibility guarantees.
- Error domains:
  - authn, authz, trust, mapping, lifecycle, system
- Outcome:
  - Stable consumer handling across incremental rollout phases.

## Pattern ND-7: Rollout Readiness Gate
- Decision source: Q7 = B.
- Pattern: unit+integration baseline plus mandatory negative security matrix.
- Required matrix categories:
  - unauthorized issuance deny
  - issuer mismatch/trust deny
  - mapping collision reject and controlled override
  - typed error/HTTP mapping consistency

## Pattern ND-8: NFR Componentization Pattern
- Decision source: Q8 = D.
- Component split:
  - Issuance policy engine
  - Trust evaluator
  - Telemetry adapter
  - Mapping/binding collision evaluator
  - Resilience manager (cache/TTL/invalidation)
  - Replay-protection coordinator

## Security Baseline Mapping
- SECURITY-03: structured logging/tracing and sensitive-data-safe telemetry
- SECURITY-08: enforced server-side authorization and policy gates
- SECURITY-15: fail-closed handling and safe exception envelopes

## Traceability
- NFR sources:
  - aidlc-docs/platform/identity-service/construction/uow-identity-core-domain/nfr-requirements/nfr-requirements.md
  - aidlc-docs/platform/identity-service/construction/uow-identity-core-domain/nfr-requirements/tech-stack-decisions.md
- Functional design source:
  - aidlc-docs/platform/identity-service/construction/uow-identity-core-domain/functional-design/business-rules.md
