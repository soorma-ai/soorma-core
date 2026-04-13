# Deployment Architecture - uow-sdk-jwt-integration

## Architecture Summary
Unit 3 deployment architecture preserves provider-neutral core guidance with one concrete GCP reference, while implementing deterministic verifier precedence, bounded cache resilience, and controlled ingress for JWKS publication.

## Logical Topology (Provider-Neutral)
1. Callers
   - SDK-enabled platform clients
   - service clients using JWT-authenticated flows
2. Ingress boundary
   - shared gateway/reverse-proxy for externally reachable identity endpoints (including JWKS publication)
3. Identity-service runtime
   - verifier source resolver
   - discovery cache manager
   - rotation invalidation coordinator
   - bootstrap/drift evaluators
   - audit writers and telemetry adapters
4. Data plane
   - relational database as source of truth for key/discovery and critical audit durability
   - in-process bounded cache for fast verifier/discovery access
   - optional shared cache enhancement path
5. Event plane
   - existing platform event bus/topic for key-rotation invalidation
   - bounded polling backstop for convergence reliability
6. Key management plane
   - external KMS-backed keys in production profile
   - service-managed bootstrap fallback for local/self-hosted startup
7. Observability plane
   - centralized logs, metrics, traces with correlation identifiers

## GCP Reference Mapping (Concrete Example)
- Runtime: Cloud Run services
- Ingress/gateway: Cloud Load Balancing + controlled service ingress path
- Relational store: Cloud SQL (PostgreSQL)
- Optional shared cache: Memorystore (Redis)
- Event bus: Pub/Sub topic/subscription model for invalidation signaling
- Key management: Cloud KMS
- Observability: Cloud Logging, Cloud Monitoring, Cloud Trace
- Secrets/config: Secret Manager + environment configuration

## Trust and Traffic Boundaries
- Public or partner traffic enters only through gateway/reverse-proxy boundary.
- JWKS publication is externally reachable through controlled ingress, not direct unmanaged service exposure.
- Internal verification logic enforces deterministic source precedence and fail-closed outcomes.
- Service-to-service mTLS is profile-based hardening and not a bootstrap blocker.

## Resilience and Rotation Behavior
- Discovery/JWKS cache model:
  - bounded TTL with jittered proactive refresh
  - hard-expiry fail-closed behavior
- Rotation model:
  - invalidation event triggers rapid refresh
  - bounded polling backstop ensures eventual convergence if signals are delayed

## Profiles

### Bootstrap Profile (Default)
- Local/self-hosted friendly startup.
- Service-managed keys allowed until KMS is configured.
- In-process cache baseline.
- Gateway boundary still required for externally reachable paths.

### Hardened Profile (Progressive)
- KMS-backed key management mandatory.
- Optional shared cache enabled based on scale evidence.
- Expanded ingress/mTLS hardening where supported by platform operations.

## Pre-Code-Generation Safety Gate
All checks must pass before advancing:
1. Unit + integration happy paths.
2. Mandatory negative security matrix.
3. Selected throughput profile validation for verifier/discovery paths.

## Portability Strategy
- Keep core architecture provider-neutral.
- Maintain one concrete provider mapping (GCP) for implementation readiness.
- Add additional provider appendices only when deployment demand requires them.
