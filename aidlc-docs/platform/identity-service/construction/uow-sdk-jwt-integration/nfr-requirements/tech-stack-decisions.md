# Tech Stack Decisions - uow-sdk-jwt-integration

## Decision Context
These decisions map Unit 3 NFR requirements to implementation and validation tooling for JWT-first SDK integration and compatibility-phase asymmetric verifier distribution.

## 1) Runtime and Layer Boundaries
- Keep Python runtime and package boundaries aligned to soorma-core architecture patterns.
- Maintain two-layer SDK separation:
  - service clients remain internal to SDK context wrappers
  - agent/consumer code uses wrapper interfaces only
- Keep compatibility-safe behavior during migration:
  - JWT authoritative when present
  - fail closed on invalid JWT and unresolved trust states

## 2) Issuance and Verification Distribution
- Introduce compatibility-phase asymmetric signing and verifier publication in identity service surfaces tracked for this unit.
- Verifier strategy is dual-source with strict precedence:
  - primary source: JWKS/discovery
  - fallback source: deterministic static key path
- Fallback usage must be observable, bounded, and policy-controlled.

## 3) Key Rotation and Cache Strategy
- Target key propagation objective is <= 5 minutes.
- Use bounded cache TTL for verifier material with explicit expiry behavior.
- Post-expiry unresolved verification state must fail closed.
- Rotation validation requires deterministic test scenarios for new and retired `kid` values.

## 4) Observability Stack
- Logging: structured decision logs for issuance and verification branches.
- Metrics: p95 latency, deny reason counters, mismatch counters, fallback counters.
- Tracing: correlation propagation through SDK wrapper and identity-service auth paths.
- Security logging rules:
  - never log raw token material
  - preserve durable audit records for override/exception decisions

## 5) Performance and Reliability Validation Tooling
- Correctness/unit validation: deterministic branch and contract tests.
- Integration validation: compatibility behavior and negative security matrix.
- Performance acceptance validation: selected throughput tiers aligned to baseline profile (100/500/1000 RPS, optional burst 1500).
- Reliability contract validation: idempotent bootstrap result codes (`CREATED`, `REUSED`, `FAILED_DRIFT`) and fail-closed drift handling.

## 6) Security Hardening Controls
- Enforce fail-closed security posture for verification and issuance checks.
- Preserve typed error behavior and non-sensitive failure outputs.
- Require durable override auditability and anomaly signal guidance with threshold recommendations.
- Keep delegated and override paths explicitly testable in negative scenarios.

## 7) Rollout Gate Strategy
- Broad compatibility enablement requires:
  - unit + integration happy-path validation
  - negative security matrix completion (invalid signature, unknown `kid`, tenant mismatch, unauthorized issue-for-other)
- Do not broaden rollout if required negative matrix outcomes are not deterministic and passing.

## 8) Implementation Risk and Mitigation
- Risk: mixed verifier source behavior may create ambiguity or hidden downgrade behavior.
- Mitigation:
  - explicit verifier precedence and bounded fallback
  - telemetry for fallback activation and trust-source decisions
  - fail-closed behavior on unresolved trust or stale verifier state
  - rotation and outage scenario validation before rollout expansion
