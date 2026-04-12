# NFR Design Patterns - uow-sdk-jwt-integration

## Purpose
Translate approved Unit 3 NFR design answers into concrete patterns for verifier precedence, cache/rotation resilience, deterministic bootstrap safety, observability, audit durability, and rollout gating.

## Pattern ND-1: Verifier Precedence and Fail-Closed Resolution
- Decision source: Q1 = A.
- Pattern: strict precedence chain.
- Resolution order:
  1. JWKS/discovery primary verifier material
  2. bounded static-key fallback (explicitly controlled)
  3. fail closed if trust cannot be established
- Constraint:
  - no dynamic source scoring
  - no environment-dependent precedence drift

## Pattern ND-2: JWKS/Discovery Cache Lifecycle
- Decision source: Q2 = B.
- Pattern: bounded TTL + jittered proactive background refresh + hard-expiry fail-closed.
- Behavior:
  - proactive refresh starts before expiry with jitter to avoid synchronized refresh storms
  - cache remains authoritative only within bounded validity
  - on hard expiry without refreshed trust material: deny verification-dependent paths fail closed

## Pattern ND-3: Key Rotation Propagation
- Decision source: Q3 = B.
- Pattern: event-triggered invalidation with bounded polling backstop.
- Behavior:
  - invalidation signal drives fast convergence after key rotation
  - bounded polling ensures convergence if signal delivery is delayed
  - freshness and propagation timing remain measurable against <=5 minute objective

## Pattern ND-4: Deterministic Bootstrap State Safety
- Decision source: Q4 = C.
- Pattern: dedicated bootstrap state evaluator + protected-config drift classifier + explicit fail-closed guard.
- Required outcomes:
  - CREATED
  - REUSED
  - FAILED_DRIFT
- Constraint:
  - protected drift cannot be auto-corrected silently

## Pattern ND-5: Minimum Actionable Trace Boundary
- Decision source: Q5 = C.
- Pattern: verification source/fallback decision tracing plus issuance override and audit-write decision tracing.
- Required boundary:
  - request wrapper entry/exit
  - verifier source selection and fallback branch
  - issuance override decision branch
  - audit-write outcome branch
- Note:
  - per-claim span explosion is out of minimum baseline for this unit

## Pattern ND-6: Audit Durability Split
- Decision source: Q6 = B.
- Pattern: critical-sync plus non-critical-async persistence split.
- Critical path (sync, durability required):
  - override approvals and high-risk security decisions
- Non-critical path (async, monitored):
  - informational and low-risk telemetry events

## Pattern ND-7: Rollout Gate Enforcement Pattern
- Decision source: Q7 = C.
- Pattern: integration baseline plus mandatory negative security matrix as blocking gate.
- Gate cannot pass unless matrix scenarios are green:
  - invalid signature
  - unknown kid
  - tenant mismatch
  - unauthorized issue-for-other attempt

## Security Baseline Mapping
- SECURITY-03: structured logs, metrics, and tracing boundaries are explicit.
- SECURITY-08: verifier precedence and fail-closed authorization boundaries are explicit.
- SECURITY-15: fail-closed handling is defined across trust and bootstrap drift paths.

## Traceability
- NFR source:
  - aidlc-docs/platform/identity-service/construction/uow-sdk-jwt-integration/nfr-requirements/nfr-requirements.md
  - aidlc-docs/platform/identity-service/construction/uow-sdk-jwt-integration/nfr-requirements/tech-stack-decisions.md
- NFR design answers source:
  - aidlc-docs/platform/identity-service/construction/plans/uow-sdk-jwt-integration-nfr-design-plan.md
