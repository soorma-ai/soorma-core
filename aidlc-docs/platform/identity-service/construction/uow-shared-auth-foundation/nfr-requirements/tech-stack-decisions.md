# Tech Stack Decisions - uow-shared-auth-foundation

## Decision Context
These decisions map NFR requirements to practical implementation/testing tooling for the shared auth dependency unit in soorma-core.

## 1) Service Runtime and Dependency Layer
- Language/runtime: Python service stack consistent with soorma-core services.
- Dependency boundary: shared auth logic in soorma-service-common.
- Auth path strategy: coexistence mode with JWT authoritative when present, as defined in functional design.

## 2) Validation and Policy Evaluation
- Token validation: centralized in shared dependency layer.
- Trust-policy evaluation: pluggable contract from shared dependency to service route policy.
- Compatibility policy for this unit: coexistence-safe rollout.
  - JWT authoritative when present.
  - Legacy headers accepted when JWT is absent.
  - Invalid JWT fails closed with no header fallback.

## 3) Observability Stack Requirements
- Logging: structured logs with schema validation in CI.
- Metrics: latency, deny reasons, provenance decision counters.
- Tracing: correlation propagation through auth path and trust-decision evaluation.
- Sensitive data controls: token-safe logging with redaction policies.

## 4) Performance Validation Tooling Strategy
- Unit tests: correctness and deterministic branch behavior only.
- Performance acceptance tests: separate load test suite for profile tiers (100/500/1000 RPS + optional burst).
- Regression pack: coexistence matrix scenarios in integration test stage.

## 5) Reliability and Resilience Implementation
- Trust policy source fallback: cached last-known-good policy with bounded TTL.
- Post-TTL behavior: fail closed.
- Error semantics: 401 for authentication failures and 403 for policy/authorization denials.

## 6) Security Hardening Decisions
- Adopt baseline hardening plus issuer pinning checks and replay-protection hooks.
- Keep fail-closed behavior mandatory.
- Ensure audit-safe outputs with no token leakage.

## 7) Open-Core Portability Considerations
- Do not require canary deployment infrastructure as mandatory baseline.
- Keep advanced runtime validation as profile-specific extension guidance.
- Retain strong portable baseline gate via coexistence regression matrix.

## 8) Risk and Mitigation for Coexistence Safety
- Risk: auth-path transition may introduce regressions across mixed JWT/header callers.
- Mitigation:
  - mandatory cross-service regression matrix before cutover progression
  - explicit coverage for header-only coexistence path until cutover unit is complete
  - explicit test focus on deny-path and precedence behavior
  - staged verification in CI/integration environments prior to header-path removal phase
