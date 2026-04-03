# NFR Requirements - uow-shared-auth-foundation

## Scope
This document defines non-functional requirements for the shared authentication foundation unit in coexistence mode and records approved NFR planning decisions.

## NFR-1 Performance (Latency)
- Decision: best-effort latency target for this unit at current stage.
- Interpretation: track p95 auth dependency overhead and optimize regressions, but do not enforce a hard global ms gate yet.
- Reason: open-core deployment/runtime profiles vary and no universal reference environment is mandated in this unit.

## NFR-2 Throughput Validation
- Decision: profile-based throughput tiers.
- Required per-instance tiers:
  - Tier 1: 100 RPS steady
  - Tier 2: 500 RPS steady
  - Tier 3: 1000 RPS steady
  - Optional burst: 1500 RPS short-window
- Validation type: performance acceptance runs (not unit tests).
- Required checks per tier:
  - p95 overhead behavior trend
  - error-rate stability
  - resource stability
  - negative-path determinism under load (invalid JWT, expired JWT, trust deny)

## NFR-3 Availability
- Decision: dependency layer follows service availability target.
- No independent standalone availability SLO is set for this unit.

## NFR-4 Resilience for Trust Policy Source Unavailability
- Decision: use bounded TTL cached last-known-good policy, then fail closed.
- Expected behavior:
  - temporary outage: use valid cached policy within TTL
  - after TTL expiry: deny delegated trust-dependent requests fail-closed

## NFR-5 Observability
- Decision: logs + metrics + traces with correlation propagation.
- Minimum required telemetry:
  - structured auth decision logs
  - latency/deny/provenance metrics
  - trace propagation across auth path with correlation identifiers

## NFR-6 Sensitive Data Handling
- Decision: enforce token-safe logging plus structured log schema validation in CI.
- Requirements:
  - never log raw tokens
  - redact sensitive claims beyond allowed identity context
  - validate log schema consistency in CI checks

## NFR-7 Rollout Verification Gate Before Header-Auth Removal
- Decision: unit/integration tests + coexistence regression matrix are mandatory baseline.
- Mandatory coexistence matrix coverage:
  - JWT-authoritative success path
  - header-only coexistence path (while supported)
  - invalid JWT fail-fast no-fallback path
  - 401 versus 403 behavior
  - delegated trust allow and deny paths
- Optional extensions when profile supports them:
  - synthetic production-like load validation
  - staged canary validation

## NFR-8 Compatibility Strategy (Approved Override)
- Decision: no compatibility constraints for this unit (intentional FR-11 override for this unit scope).
- Justification:
  - pre-release state
  - all impacted services in scope
  - no assumed external stable-contract reliance
  - avoid temporary adapter complexity
- Compensating controls:
  - coordinated refactor across impacted services
  - mandatory cross-service regression gate before next phase

## NFR-9 Security Hardening Depth
- Decision: baseline + issuer pinning checks + replay protection hooks.
- Includes:
  - fail-closed semantics
  - safe error handling
  - issuer trust hardening
  - replay-resistance hook points

## NFR-10 Coverage Target
- Decision: full practical coverage for critical auth branches with explicit deny-path tests.
- Required coverage emphasis:
  - precedence and fail-closed branches
  - delegated trust decisions
  - malformed/expired/issuer mismatch cases
  - service integration and coexistence regressions

## Traceability Notes
- This unit includes an approved compatibility override decision for FR-11 constraints, limited to this pre-release, in-scope refactor context.
- Override source: construction clarification artifact for NFR Q8 compatibility resolution.
