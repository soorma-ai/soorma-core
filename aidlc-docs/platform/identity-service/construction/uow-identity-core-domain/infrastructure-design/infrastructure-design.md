# Infrastructure Design - uow-identity-core-domain

## Design Scope
This document maps the identity-core domain design to deployable infrastructure choices that preserve open-core portability while supporting hardened production profiles.

## Deployment Baseline
- Primary model: local baseline + cloud-ready provider-neutral reference.
- Initial concrete reference mapping: GCP.
- Runtime baseline: containerized service deployment with a migration path to orchestrated runtime where scale/operations require it.

## Infrastructure Mapping by Logical Component

### Issuance Policy Engine
- Compute: identity-service runtime process boundary.
- Dependencies:
  - delegated issuer trust metadata repository
  - policy/mapping reference resolver
- Infrastructure notes:
  - fail-closed behavior is mandatory when trust metadata freshness cannot be guaranteed.

### Trust Evaluator
- Compute: same service boundary as issuance policy engine.
- Dependencies:
  - trust metadata source of truth (relational DB)
  - key material resolver
- Infrastructure notes:
  - delegated issuance requires issuer status and policy references to be resolvable.

### Mapping/Binding Collision Evaluator
- Compute: in-process decision component.
- Dependencies:
  - durable mapping/binding store (relational DB)
  - explicit override approval path
- Infrastructure notes:
  - default reject on collision; no silent remap path.

### Resilience Manager (Policy Cache/Invalidation)
- Baseline mapping:
  - in-process bounded TTL cache
  - relational DB durable source of truth
- Optional scale-up mapping:
  - shared cache service for high fan-out workloads.
- Required behavior:
  - bounded last-known-good use during transient outage.
  - fail-closed after TTL expiry.

### Replay-Protection Coordinator
- Baseline mapping:
  - in-process acceleration for hot checks
  - relational durability for replay markers and policy-state continuity
- Optional enhancement:
  - shared cache for distributed acceleration where validated by load profile.

### Telemetry Adapter
- Required observability mapping:
  - centralized structured logs
  - centralized metrics
  - distributed tracing with correlation propagation
- Security baseline:
  - sensitive-data-safe telemetry output only.

## Persistence Baseline
- Primary source of truth: single relational database.
- Identity-core entities covered:
  - tenant identity domain records
  - principals and lifecycle state
  - delegated issuer trust metadata
  - mapping/binding state and collision decisions
  - replay/policy continuity markers

## Key Management Baseline
- Effective default profile:
  - production deployments use external KMS-backed key management and rotation integration.
  - local/self-hosted bootstrap may start with service-managed keys until KMS configuration exists.
- Security posture:
  - key-rotation updates must apply immediately to new validations/issuance checks.

## Networking Boundary Pattern
- External ingress:
  - shared gateway or reverse-proxy boundary for externally reachable paths.
- Internal service-to-service:
  - mTLS where supported by deployment profile.
- Forbidden baseline:
  - direct unmanaged public ingress on raw service endpoints.

### Local Development Clarification
- Existing Docker Compose service-name networking remains valid for local service-to-service communication.
- A local reverse proxy or API gateway is optional and used only when teams need edge-behavior simulation (routing plugins, policy tests, external ingress emulation).

## Bootstrap and Hardened Profiles

### Bootstrap Profile
- No mandatory internal mTLS setup requirement.
- No mandatory full API-gateway feature set requirement.
- App-layer authorization and fail-closed trust behavior are mandatory.

### Hardened Profile
- mTLS enabled where cert lifecycle support exists.
- Expanded gateway policy controls and security routing.
- Optional shared-cache layer for scale and resilience tuning.

## Deployment Safety Gate (Before Code Generation)
Required gate for this unit:
1. Per-slice deployment simulation + regression checkpoint.
2. Rollback playbook validation.
3. Environment smoke checks for each impacted identity path.

## Security Baseline Traceability
- SECURITY-03: structured logs/metrics/traces with safe telemetry handling.
- SECURITY-08: policy-gated server-side trust/authorization decisions.
- SECURITY-15: fail-closed behavior after bounded cache validity and on trust/auth failures.

## Traceability Notes
- Functional design source:
  - aidlc-docs/platform/identity-service/construction/uow-identity-core-domain/functional-design/business-logic-model.md
- NFR design source:
  - aidlc-docs/platform/identity-service/construction/uow-identity-core-domain/nfr-design/nfr-design-patterns.md
