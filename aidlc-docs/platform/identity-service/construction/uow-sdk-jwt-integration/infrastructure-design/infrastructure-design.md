# Infrastructure Design - uow-sdk-jwt-integration

## Design Scope
This document maps Unit 3 SDK JWT integration and compatibility-phase verifier-distribution behavior to deployable infrastructure choices, aligned to Unit 2 baseline decisions.

## Deployment Baseline
- Primary model: local baseline + cloud-ready provider-neutral reference.
- Concrete reference mapping: GCP.
- Baseline objective: preserve open-core portability while keeping one practical cloud reference for implementation guidance.

## Infrastructure Mapping by Logical Component

### VerifierSourceResolver
- Compute: shared auth verification boundary used by identity-service and consuming services.
- Dependencies:
  - JWKS/discovery resolver
  - static fallback key descriptor
- Infrastructure notes:
  - strict precedence is enforced (JWKS primary, bounded static fallback).
  - unresolved trust source must fail closed.

### DiscoveryCacheManager
- Baseline mapping:
  - in-process bounded TTL cache
  - relational persistence for key/discovery metadata continuity
- Optional scale-up:
  - shared cache service for high fan-out deployments when load evidence justifies it.
- Required behavior:
  - jittered proactive refresh
  - hard-expiry fail-closed

### RotationInvalidationCoordinator
- Event infrastructure mapping:
  - existing platform event bus/topic for invalidation signals
  - bounded polling backstop for convergence safety
- Required behavior:
  - converge verifier state within configured propagation objective
  - remain deterministic under transient event delay

### BootstrapStateEvaluator + ProtectedDriftClassifier
- Compute: identity-service/CLI orchestration boundary.
- Dependencies:
  - relational source of truth for protected bootstrap state
- Infrastructure notes:
  - protected drift outcome is blocking (`FAILED_DRIFT`) and fail closed.

### DecisionTraceAdapter
- Observability mapping:
  - centralized structured logs
  - centralized metrics
  - distributed tracing with correlation propagation
- Required trace boundaries:
  - verifier source selection/fallback
  - override decision paths
  - audit-write outcomes

### CriticalAuditWriter and AsyncAuditWriter
- Persistence split:
  - critical security decisions persisted synchronously
  - non-critical events persisted asynchronously
- Infrastructure notes:
  - critical path persistence failures block guarded operations fail closed.
  - async path failures emit monitoring/retry signals and do not open security boundaries.

## Key Management Baseline
- Production profile:
  - external KMS-backed signing key management with rotation integration.
- Local/self-hosted bootstrap profile:
  - service-managed keys permitted until KMS is configured.
- Constraint:
  - compatibility profile cannot drift into unmanaged production signing posture.

## Networking and Ingress Boundary
- JWKS publication and externally reachable identity APIs are exposed through shared gateway/reverse-proxy boundary.
- Direct unmanaged public service exposure is not baseline.
- Service-to-service mTLS remains profile-based hardening where supported.

## Persistence Baseline
- Relational database remains source of truth for:
  - key/discovery metadata continuity
  - bootstrap protected-state checks
  - critical security/audit decision durability
- In-process cache remains baseline acceleration layer.

## Deployment Safety Gate (Before Code Generation)
Required gate for this unit:
1. Unit + integration happy-path validation.
2. Mandatory negative security matrix pass.
3. Selected throughput profile validation for verifier/discovery paths.

## Security Baseline Traceability
- SECURITY-03: required logs/metrics/traces with correlation and safe telemetry.
- SECURITY-08: gateway and server-side authorization boundaries preserved.
- SECURITY-13: signing/verifier integrity maintained with deterministic precedence.
- SECURITY-15: fail-closed defaults on trust, drift, and critical persistence failure.

## Traceability
- Functional design source:
  - aidlc-docs/platform/identity-service/construction/uow-sdk-jwt-integration/functional-design/business-logic-model.md
  - aidlc-docs/platform/identity-service/construction/uow-sdk-jwt-integration/functional-design/business-rules.md
- NFR design source:
  - aidlc-docs/platform/identity-service/construction/uow-sdk-jwt-integration/nfr-design/nfr-design-patterns.md
  - aidlc-docs/platform/identity-service/construction/uow-sdk-jwt-integration/nfr-design/logical-components.md
- Plan answers source:
  - aidlc-docs/platform/identity-service/construction/plans/uow-sdk-jwt-integration-infrastructure-design-plan.md
