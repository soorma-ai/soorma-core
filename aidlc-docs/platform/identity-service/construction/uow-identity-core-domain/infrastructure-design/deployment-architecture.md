# Deployment Architecture - uow-identity-core-domain

## Architecture Summary
Identity-core domain is deployed with a provider-neutral baseline and a GCP reference mapping, preserving local bootstrap simplicity while enabling production hardening controls.

## Logical Topology (Provider-Neutral)
1. External clients
   - tenant-admin tooling and trusted service clients
   - delegated identity callers through approved issuer paths
2. Ingress boundary
   - shared gateway or reverse-proxy boundary
3. Identity service runtime
   - issuance policy engine
   - trust evaluator
   - mapping/binding collision evaluator
   - resilience manager
   - replay-protection coordinator
   - telemetry adapter
4. Data plane
   - relational database as source of truth
   - in-process bounded cache for policy/trust acceleration
   - optional shared cache enhancement path
5. Key management plane
   - external KMS-backed key material in production profile
   - bootstrap fallback to service-managed keys when KMS is unavailable
6. Observability plane
   - centralized logs, metrics, traces with correlation identifiers

## GCP Reference Mapping (Concrete Example)
- Runtime: Cloud Run services
- Relational store: Cloud SQL (PostgreSQL)
- Optional shared cache: Memorystore (Redis)
- Ingress: Cloud Load Balancing and service ingress controls
- Key management: Cloud KMS
- Observability: Cloud Logging, Cloud Monitoring, Cloud Trace
- Secrets/config: Secret Manager + environment configuration

## Traffic and Trust Boundaries
- Public traffic enters only via gateway/reverse-proxy boundary.
- Service-to-service traffic may enforce mTLS where supported.
- Delegated issuance is denied unless issuer trust metadata and policy references validate.
- Platform-principal paths remain available under existing trusted call-path model.

## Resilience and Failure Handling
- Policy/trust backing-data outage:
  - use bounded last-known-good cache window.
  - after TTL expiry, deny delegated trust-dependent operations fail-closed.
- Replay protections:
  - maintain durable replay markers in relational store.
  - allow in-process fast-path checks for hot traffic.

## Profiles

### Bootstrap Profile (Default)
- Gateway/reverse-proxy boundary required.
- App-layer authorization required.
- Full gateway feature set and mTLS not mandatory at bootstrap.
- Service-managed keys permitted only until KMS is configured.
- Local Docker Compose deployments may use native service-name networking directly; adding Kong/reverse proxy in local dev is optional.
- Optional local gateway profile can be enabled when integration tests need edge-policy or ingress behavior validation.

### Hardened Profile (Progressive)
- KMS-backed keys mandatory.
- mTLS enabled where infrastructure supports cert lifecycle.
- Optional shared-cache and enhanced gateway policies enabled per workload risk/scale.

## Pre-Code-Generation Safety Gate
All checks must pass before advancing:
1. Per-slice deployment simulation + regression checkpoint.
2. Rollback playbook validation.
3. Environment smoke checks for each impacted identity path.

## Portability Strategy
- Keep the architecture provider-neutral in core docs.
- Maintain one concrete provider mapping (GCP) for actionable implementation guidance.
- Add additional provider appendices when deployment demand requires them.
