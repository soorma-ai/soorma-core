# Logical Components - uow-sdk-jwt-integration NFR Design

## Overview
This artifact defines the logical component split needed to realize approved Unit 3 NFR design patterns.

## Component LC-1: VerifierSourceResolver
- Purpose: enforce deterministic verifier precedence.
- Responsibilities:
  - apply source order (JWKS first, bounded static fallback second)
  - emit explicit source-selection reason codes
  - return fail-closed decision when trust source resolution fails

## Component LC-2: DiscoveryCacheManager
- Purpose: manage JWKS/discovery cache lifecycle.
- Responsibilities:
  - TTL enforcement and staleness boundaries
  - jittered proactive refresh scheduling
  - hard-expiry transition to fail-closed state

## Component LC-3: RotationInvalidationCoordinator
- Purpose: coordinate key rotation propagation.
- Responsibilities:
  - consume/handle invalidation events from rotation actions
  - trigger immediate refresh on invalidation
  - run bounded polling backstop for convergence safety

## Component LC-4: BootstrapStateEvaluator
- Purpose: provide deterministic bootstrap state contract.
- Responsibilities:
  - evaluate bootstrap input and existing state
  - return typed outcomes (CREATED, REUSED, FAILED_DRIFT)
  - delegate protected drift checks to classifier

## Component LC-5: ProtectedDriftClassifier
- Purpose: classify protected configuration drift severity.
- Responsibilities:
  - detect protected drift conditions
  - mark drift as blocking/non-blocking per policy
  - enforce fail-closed for protected drift classes

## Component LC-6: DecisionTraceAdapter
- Purpose: enforce minimum actionable tracing boundary.
- Responsibilities:
  - create spans for source selection and fallback branches
  - create spans for issuance override decision path
  - create spans for audit-write outcomes and correlated decision IDs

## Component LC-7: CriticalAuditWriter
- Purpose: synchronous durable persistence for security-critical decisions.
- Coverage:
  - override approvals/denials
  - high-risk issuance and trust decisions
- Failure mode:
  - persistence failure on critical event blocks operation fail-closed

## Component LC-8: AsyncAuditWriter
- Purpose: asynchronous persistence for non-critical audit and telemetry events.
- Coverage:
  - informational state transitions
  - low-risk operational telemetry events
- Failure mode:
  - does not open security path; emits monitoring signal for retry/ops handling

## Component LC-9: RolloutSecurityGate
- Purpose: enforce release-blocking negative security matrix prior to broad compatibility enablement.
- Responsibilities:
  - validate unit+integration baseline completion
  - validate required negative matrix scenarios
  - return pass/fail gate status used by release progression decisions

## High-Level Flow
1. VerifierSourceResolver receives request verification context.
2. DiscoveryCacheManager provides fresh verifier material or explicit stale/expired state.
3. RotationInvalidationCoordinator accelerates convergence after rotation and backstops with bounded polling.
4. BootstrapStateEvaluator + ProtectedDriftClassifier govern local bootstrap determinism.
5. DecisionTraceAdapter emits correlated trace spans at required decision boundaries.
6. Critical events persist via CriticalAuditWriter; non-critical events via AsyncAuditWriter.
7. RolloutSecurityGate enforces required negative security matrix before rollout expansion.

## Failure Defaults
- Trust material unresolved: fail closed.
- Cache hard-expired and no refresh: fail closed.
- Protected drift detected: fail closed with FAILED_DRIFT outcome.
- Critical audit persistence failure: fail closed for the guarded operation.

## Traceability
- Pattern source:
  - aidlc-docs/platform/identity-service/construction/uow-sdk-jwt-integration/nfr-design/nfr-design-patterns.md
- Requirement sources:
  - aidlc-docs/platform/identity-service/construction/uow-sdk-jwt-integration/nfr-requirements/nfr-requirements.md
  - aidlc-docs/platform/identity-service/construction/uow-sdk-jwt-integration/nfr-requirements/tech-stack-decisions.md
