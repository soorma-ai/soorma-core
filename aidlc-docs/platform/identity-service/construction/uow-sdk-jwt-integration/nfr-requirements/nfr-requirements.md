# NFR Requirements - uow-sdk-jwt-integration

## Scope
This document defines non-functional requirements for JWT-first SDK and wrapper integration in compatibility mode, including asymmetric signing and verifier distribution boundaries that are introduced in this unit.

## NFR-1 Performance (Latency)
- Decision: p95 <= 100 ms for SDK-authenticated identity flows.
- Covered paths:
  - token issuance request path
  - JWKS/discovery retrieval under normal load
  - wrapper-to-service authenticated request path
- Enforcement expectation:
  - instrument p95 for these paths
  - use explicit timeout budgets and cache controls to keep regressions visible

## NFR-2 Throughput Validation
- Decision: tiered throughput profile aligned to prior unit baseline.
- Required per-instance tiers:
  - Tier 1: 100 RPS sustained
  - Tier 2: 500 RPS sustained
  - Tier 3: 1000 RPS sustained
  - Optional burst: 1500 RPS short window
- Validation type:
  - performance acceptance validation for selected tiers
  - integration validation for compatibility and deny paths under load

## NFR-3 Availability and Discovery Resilience
- Decision: use bounded last-known-good verifier material cache, then fail closed at cache expiry.
- Required behavior:
  - temporary JWKS/discovery unavailability: continue using valid cached material within TTL
  - cache TTL expiry with unresolved discovery failure: deny verification-dependent operations fail closed

## NFR-4 Key Rotation Propagation Objective
- Decision: new signing key (`kid`) propagation objective <= 5 minutes across consumers.
- Required controls:
  - deterministic key refresh behavior
  - measurable freshness window tracking
  - explicit validation during rotation scenarios

## NFR-5 Verifier Distribution Mode
- Decision: JWKS primary with deterministic static-key fallback.
- Required semantics:
  - JWKS is the default verifier source
  - static fallback is explicit, deterministic, and bounded
  - no silent downgrade behavior
  - verification remains fail closed on unresolved trust state

## NFR-6 Observability Depth
- Decision: logs + metrics + tracing with correlation propagation.
- Minimum telemetry:
  - structured logs for issuance policy and verification decisions
  - metrics for latency, deny counts, mismatch counts, and fallback activation
  - trace propagation across SDK wrapper call path and identity service auth path

## NFR-7 Idempotent Bootstrap Reliability
- Decision: `soorma dev` bootstrap outcomes must be deterministic.
- Required outcomes:
  - `CREATED`
  - `REUSED`
  - `FAILED_DRIFT`
- Required safety:
  - fail closed on protected drift
  - no implicit mutation for protected values when drift is detected

## NFR-8 Security Hardening Depth
- Decision: baseline hardening + override audit durability + anomaly alert recommendations and threshold guidance.
- Required controls:
  - fail-closed semantics for auth/issuance validation branches
  - typed safe errors without sensitive leakage
  - durable audit records for override decisions and issuance-policy exceptions
  - anomaly signal guidance for threshold-based operational detection

## NFR-9 Rollout Readiness Gate
- Decision: unit + integration happy-path validation plus negative security matrix is mandatory.
- Required matrix scenarios:
  - invalid signature
  - unknown `kid`
  - tenant mismatch
  - unauthorized issue-for-other attempt
- Gate requirement:
  - broad compatibility enablement is blocked until this matrix passes

## Traceability Notes
- This NFR set aligns with the Unit 3 functional-design scope for JWT-first integration and compatibility-phase verifier distribution.
- Identity-service responsibilities for asymmetric signing and JWKS publication remain explicitly in-scope for this unit and are constrained by fail-closed compatibility behavior.
