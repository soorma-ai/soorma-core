# NFR Requirements - uow-identity-core-domain

## Scope
This document captures non-functional requirements for identity-core domain capabilities including onboarding, principal lifecycle, delegated trust, mapping/binding policy enforcement, issuance decisions, and audit/telemetry behavior.

## NFR-1 Performance (Latency)
- Decision: best-effort latency target for this unit.
- Q1 Answer: D.
- Interpretation:
  - Track p95 latency behavior for core identity operations.
  - Optimize regressions and outliers, but do not enforce a global hard ms gate in this unit.

## NFR-2 Throughput Validation
- Decision: profile-based throughput tiers inherited from uow-shared-auth-foundation.
- Q2 Answer: D (inherit profile strategy).
- Required per-instance tiers:
  - Tier 1: 100 RPS steady
  - Tier 2: 500 RPS steady
  - Tier 3: 1000 RPS steady
  - Optional burst: 1500 RPS short-window
- Validation expectations:
  - performance acceptance runs
  - stability checks for latency trends, error rates, and resource behavior

## NFR-3 Availability
- Decision: match service-wide availability expectation.
- Q3 Answer: A.
- No separate identity-specific standalone availability SLO is defined in this unit.

## NFR-4 Resilience for Delegated Policy/Metadata Unavailability
- Decision: bounded last-known-good cache strategy, then fail closed.
- Q4 Answer: C (aligned to shared-auth foundation strategy).
- Required behavior:
  - During temporary backing-data outage: use valid cached policy within configured bounded TTL.
  - After TTL expiry: deny delegated trust-dependent operations fail-closed.

## NFR-5 Key Rotation Propagation
- Decision: delegated issuer trust-material changes take effect immediately for new validations/issuance checks.
- Q5 Answer: A.
- Requirement:
  - no stale-key acceptance once rotation update is committed.

## NFR-6 Observability
- Decision: logs + metrics + traces with correlation propagation.
- Q6 Answer: C.
- Minimum telemetry:
  - structured logs for trust/issuance/mapping decisions
  - metrics for latency, deny/error counts, collision counters
  - tracing across request, trust-evaluation, and policy enforcement boundaries

## NFR-7 Audit Durability
- Decision: fail-closed for critical mutations; best-effort for low-risk updates.
- Q7 Answer: B.
- Critical mutation examples:
  - delegated issuer trust changes
  - key rotation updates
  - principal revocation
- Low-risk updates may proceed on best-effort audit with explicit monitoring.

## NFR-8 Rollout Readiness Before Broad Delegated Issuance Enablement
- Decision: unit/integration tests plus negative security regression matrix are mandatory baseline.
- Q8 Answer: B.
- Mandatory regression scope:
  - unauthorized issuance denial
  - issuer mismatch and trust-deny paths
  - mapping-collision reject/override paths
  - typed error contract consistency and safe responses

## NFR-9 Security Hardening Depth
- Decision: inherit shared-auth foundation strategy for this stage.
- Q9 Answer: X (resolved to inherited strategy from uow-shared-auth-foundation).
- Effective requirement:
  - baseline controls + replay-protection hooks and nonce/jti validation controls.

## Security Baseline Alignment
- SECURITY-03: structured logging and non-sensitive error/telemetry output
- SECURITY-08: server-side access control enforcement and policy checks
- SECURITY-15: fail-closed handling on trust/authn/authz failures

## Traceability Notes
- Functional design alignment:
  - aidlc-docs/platform/identity-service/construction/uow-identity-core-domain/functional-design/business-logic-model.md
  - aidlc-docs/platform/identity-service/construction/uow-identity-core-domain/functional-design/business-rules.md
  - aidlc-docs/platform/identity-service/construction/uow-identity-core-domain/functional-design/domain-entities.md
- Inherited NFR strategy references:
  - aidlc-docs/platform/identity-service/construction/uow-shared-auth-foundation/nfr-requirements/nfr-requirements.md
