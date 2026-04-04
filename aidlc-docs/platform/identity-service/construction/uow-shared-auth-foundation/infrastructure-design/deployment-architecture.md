# Deployment Architecture - uow-shared-auth-foundation

## Architecture Summary
A provider-neutral deployment shape with a GCP reference mapping is defined for the shared auth foundation unit.

## Logical Topology (Provider-Neutral)
1. External clients
   - Tenant-developed services/agents
   - Selected end-user clients for exposed service paths
2. Ingress boundary
   - Minimal reverse proxy / ingress layer at bootstrap
   - Optional evolution to full API gateway capabilities
3. Application services
   - Soorma-core services running containerized runtime
   - Shared auth dependency in process
4. Data plane
   - Relational database for durable trust-policy and replay state
   - In-memory cache in service process
   - Optional shared cache enhancement path
5. Observability plane
   - centralized logs, metrics, and tracing backend

## GCP Reference Mapping (Initial Concrete Example)
- Container runtime: Cloud Run services
- Relational persistence: Cloud SQL (PostgreSQL)
- Optional shared cache enhancement: Memorystore (Redis)
- Ingress: Cloud Load Balancing + service-level ingress controls
- Observability: Cloud Logging, Cloud Monitoring, Cloud Trace
- Secrets/config: Secret Manager + environment configuration

## Bootstrap vs Hardened Profiles

### Bootstrap Profile (default)
- No mandatory internal mTLS
- No mandatory full API gateway
- JWT app-layer authorization mandatory
- Reverse proxy/ingress boundary mandatory for external exposure
- Centralized logs/metrics/traces required

### Hardened Profile (progressive)
- Internal mTLS enabled where supported
- Expanded gateway policy enforcement
- Optional security event stream integration for anomaly workflows
- Shared cache layer for scale/latency optimization when needed

## Resilience and Failure Handling
- Trust-policy retrieval:
  - cache-aside pattern with bounded TTL
  - fail-closed when policy freshness cannot be guaranteed
- Replay protection:
  - durable state in relational store with expiry policy
  - in-memory acceleration allowed

## Refactor Safety Deployment Gate
Before advancing to Code Generation for this unit:
1. Per-slice deployment simulation + regression checkpoint
2. Rollback playbook validation
3. Environment smoke checks across impacted services

## Portability Strategy
- Keep architecture core provider-neutral.
- Maintain one concrete provider mapping (GCP now) to reduce adoption ambiguity.
- Add additional provider mapping appendices as ecosystem demand emerges.
