# NFR Requirements - uow-cutover-hardening

## Scope
This document defines non-functional requirements for final hard cutover to JWT-only secured paths in identity-service, including key verification resilience, observability/alerting, rollback safety, local developer bootstrap expectations, and delegated issuer OIDC/JWKS finalization.

## NFR-1 Performance (Latency)
- Decision: p95 <= 100 ms for secured JWT-authenticated request paths (excluding public health/discovery endpoints).
- Covered paths:
  - secured ingress auth validation
  - issuance authorization decision path
  - verifier key resolution path
- Enforcement expectation:
  - instrument p95 latency metrics
  - define timeout budgets and response-time regression checks

## NFR-2 Throughput Validation
- Decision: tiered throughput profile.
- Required baseline tiers:
  - Tier 1: 100 RPS sustained
  - Tier 2: 500 RPS sustained
  - Tier 3: 1000 RPS sustained
  - Optional burst: 1500 RPS short window
- Validation type:
  - performance acceptance for selected tiers
  - correctness validation for deny and override branches under load

## NFR-3 Availability and JWKS/OIDC Resilience
- Decision: bounded last-known-good verifier cache, then fail closed at cache expiry.
- Required behavior:
  - temporary JWKS/OIDC outage: continue with valid cached material within TTL
  - cache expiry with unresolved trust-source failure: deny verification-dependent operations fail closed

## NFR-4 Key Rotation Propagation Objective
- Decision: new signing key (`kid`) propagation objective <= 5 minutes across consumers.
- Required controls:
  - deterministic refresh behavior
  - explicit overlap-window behavior
  - measurable freshness objective and validation checks

## NFR-5 Observability Depth
- Decision: logs + metrics + tracing with correlation propagation.
- Minimum telemetry:
  - structured logs for auth decisions, override decisions, and key-resolution outcomes
  - metrics for latency, deny counts, unknown kid counts, and signature failure counts
  - tracing correlation across ingress -> policy -> verifier flow
- Security constraint:
  - no raw token values or secret material in logs

## NFR-6 Alerting Expectations
- Decision: alert on denial spikes plus admin-override anomaly patterns and unknown kid/signature failure spikes.
- Required signals:
  - repeated legacy/header-denial spikes
  - unusual override frequency or override failure anomalies
  - unknown kid/signature failure spikes
- Dependency note:
  - this requirement does not mandate a new monitoring vendor; existing observability stack may be used

## NFR-7 Rollback Reliability
- Decision: release/deployment rollback runbook with deterministic entry criteria, execution steps, and post-rollback verification checks.
- Required controls:
  - explicit rollback triggers
  - deterministic rollback execution procedure
  - post-rollback auth correctness and safety verification
- Constraint:
  - rollback is deployment/release based, not runtime feature-flag reversal

## NFR-8 Local Development Bootstrap Policy
- Decision: `soorma dev` defaults to asymmetric bootstrap automation (generate/seed keypair + JWKS wiring), no HS256 default path.
- Required behavior:
  - local bootstrap path remains consistent with RS256 hard-cutover contract
  - HS256 is not default local mode for this unit

## NFR-9 Delegated Issuer OIDC/JWKS Finalization Scope
- Decision: in-scope now with bounded implementation and full NFR controls.
- Scope bounds:
  - issuer trust validation
  - JWKS retrieval/cache/rotation handling
  - policy-gated delegated claim acceptance
- Guardrail:
  - no expansion into new product surface beyond approved unit boundaries

## Security Baseline Alignment
- SECURITY-03 (application logging): NFR-5, NFR-6
- SECURITY-08 (application access control): NFR-3, NFR-7, NFR-9
- SECURITY-11 (secure design): NFR-8, NFR-9
- SECURITY-14 (alerting and monitoring): NFR-5, NFR-6
- SECURITY-15 (fail-safe defaults): NFR-3, NFR-4, NFR-7
- SECURITY-10 (supply chain): N/A in this stage artifact (addressed during code/build stage)

## Traceability Notes
- This NFR set aligns with uow-cutover-hardening functional design artifacts and the unit migration checklist.
- Decisions preserve hard cutover posture while retaining operational safety and deterministic failure handling.
