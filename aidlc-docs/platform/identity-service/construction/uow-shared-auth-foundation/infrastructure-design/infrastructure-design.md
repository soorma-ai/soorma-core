# Infrastructure Design - uow-shared-auth-foundation

## Design Scope
This infrastructure design maps the shared auth foundation logical components to deployable infrastructure choices for an open-core baseline.

## Deployment Baseline
- Primary model: local baseline plus cloud-ready provider-neutral architecture.
- Initial concrete reference mapping: GCP.
- Runtime baseline: container-serverless style deployment (for example Cloud Run style) with migration path to Kubernetes if required by scale or operations.

## Infrastructure Mapping by Logical Component

### AuthValidator
- Compute: service container runtime.
- Dependencies:
  - JWT verification libraries
  - claim schema validation layer
- Infrastructure notes:
  - no special infra dependency beyond service runtime and configuration/secret sources.

### TrustEvaluator
- Compute: same service runtime boundary as AuthValidator.
- Dependencies:
  - issuer pinning policy source
  - replay-check interfaces
- Infrastructure notes:
  - depends on durable trust-policy/replay persistence path.

### PolicySourceResilience
- Primary storage mapping:
  - in-memory cache for fast reads
  - relational DB persistence for durable source of truth
- Resilience behavior:
  - cache-aside with bounded TTL
  - fail-closed after staleness threshold
- Future enhancement path:
  - optional shared cache layer (for example Redis) when scale/latency demands justify.

### ObservabilityAdapter
- Required telemetry mapping:
  - centralized logs
  - centralized metrics
  - distributed tracing with correlation propagation
- Event correlation:
  - per-decision event correlation retained as design requirement.

## Networking Boundary Pattern
- External ingress:
  - terminate externally reachable traffic at shared ingress boundary (minimal reverse proxy at bootstrap; full API gateway optional later).
- External client classes:
  - authenticated tenant-developed agents/services
  - selected end-user-facing clients for future services using platform-tenant JWTs or delegated service-tenant JWTs
- Internal service-to-service:
  - mTLS profile-based hardening control, not mandatory at bootstrap.

## Security and Bootstrap Posture
- Bootstrap requirements:
  - no mandatory mTLS setup for local/basic self-hosted startup
  - no mandatory full-feature API gateway at bootstrap
- Mandatory security baseline in all profiles:
  - token-based app-layer authorization
  - fail-closed trust and auth behavior
  - secret-safe structured observability
- Hardened profile extensions:
  - mTLS where platform supports cert lifecycle
  - richer gateway policies, anomaly routing/event stream

## Deployment Safety Gate (Pre-Code-Generation Readiness)
- Required gate selection:
  - per-slice deployment simulation + regression checkpoint
  - rollback playbook validation
  - environment smoke checks for each impacted service
- Purpose:
  - compensating control for approved compatibility override and direct refactor strategy.

## Open-Core Documentation Strategy
- Selected strategy:
  - provider-neutral core guidance
  - one concrete reference provider implementation (GCP first)
- Rationale:
  - preserves portability while giving adopters actionable deployment examples.

## Traceability Notes
- This design reflects resolved clarification to use dual-track documentation with GCP as reference provider.
- This unit retains approved FR-11 compatibility override with explicit regression-based safety controls.
