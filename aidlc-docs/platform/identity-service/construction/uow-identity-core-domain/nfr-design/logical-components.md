# Logical Components - uow-identity-core-domain NFR Design

## Overview
This artifact defines logical components required to realize approved NFR design patterns for identity-core operations.

## Component LC-1: IssuancePolicyEngine
- Purpose: Evaluate issuance eligibility and route-scoped policy checks.
- Inputs:
  - principal state, role set, trust decision, route context
- Outputs:
  - issue/deny decision + typed reason code

## Component LC-2: TrustEvaluator
- Purpose: Validate delegated issuer trust state and key-material validity.
- Inputs:
  - issuer metadata, key version refs, policy refs
- Outputs:
  - trusted/untrusted decision + trust classification code

## Component LC-3: ResilienceManager
- Purpose: Manage bounded TTL policy cache and invalidation behavior.
- Responsibilities:
  - cache-aside policy retrieval
  - TTL enforcement
  - fail-closed transition after expiry
  - invalidation event handling

## Component LC-4: KeyRotationCoordinator
- Purpose: Implement hybrid rotation propagation model.
- Responsibilities:
  - atomic local keyset pointer swap
  - publish/consume invalidation signals
  - consistency monitoring hooks

## Component LC-5: CollisionPolicyEvaluator
- Purpose: Apply deterministic mapping/binding collision rules.
- Responsibilities:
  - default reject-on-collision
  - deterministic precedence checks
  - collision decision reason coding

## Component LC-6: OverrideApprovalGateway
- Purpose: Control explicit canonical remap approvals.
- Responsibilities:
  - authorization and approval workflow checks
  - remap eligibility validation
  - override event emission

## Component LC-7: ReplayProtectionCoordinator
- Purpose: Enforce replay-protection controls.
- Responsibilities:
  - nonce/jti tracking integration
  - replay-detection decision hooks
  - expiry policy coordination

## Component LC-8: AuditWriterCritical
- Purpose: Critical fail-closed audit path.
- Coverage:
  - issuer trust changes
  - key rotation updates
  - principal revocation
  - high-risk authorization decisions

## Component LC-9: AuditWriterBestEffort
- Purpose: Async best-effort audit path for low-risk updates.
- Coverage:
  - non-critical informational lifecycle events
  - low-risk telemetry expansions

## Component LC-10: TelemetryAdapter
- Purpose: Structured logs, metrics, and tracing propagation.
- Responsibilities:
  - correlation id propagation
  - metrics emission (latency, deny/error, collision counters)
  - tracing spans for trust/mapping/issuance decision boundaries

## Component Interactions (High-Level)
1. Request enters IssuancePolicyEngine.
2. TrustEvaluator + ResilienceManager + KeyRotationCoordinator resolve trust/key state.
3. CollisionPolicyEvaluator processes mapping/binding conflicts.
4. OverrideApprovalGateway handles explicit remap-only operations.
5. ReplayProtectionCoordinator validates replay constraints.
6. Decision and events flow to AuditWriterCritical or AuditWriterBestEffort.
7. TelemetryAdapter emits logs/metrics/traces across the flow.

## Failure-Mode Defaults
- Trust/policy/key failures: fail closed.
- Cache expiry without source recovery: fail closed for delegated-dependent paths.
- Audit critical path failure: deny critical mutation.
- Best-effort audit path failure: proceed for low-risk event with monitoring signal.

## Traceability
- Pattern source: aidlc-docs/platform/identity-service/construction/uow-identity-core-domain/nfr-design/nfr-design-patterns.md
- Requirement source: aidlc-docs/platform/identity-service/construction/uow-identity-core-domain/nfr-requirements/nfr-requirements.md
