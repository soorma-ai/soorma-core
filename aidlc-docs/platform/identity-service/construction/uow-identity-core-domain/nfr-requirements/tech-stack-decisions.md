# Tech Stack Decisions - uow-identity-core-domain

## Decision Context
This document maps approved NFR decisions to implementation-oriented technology and verification expectations for identity-core operations.

## 1) Runtime and Service Layer
- Runtime baseline: Python service stack consistent with soorma-core services.
- Domain components involved:
  - onboarding, principal lifecycle, delegated trust, mapping/binding, issuance decisioning
- Existing DI/router integration patterns remain consistent with FR-11 sequence constraints.

## 2) Throughput and Performance Strategy
- Throughput validation profiles (inherited): 100/500/1000 RPS + optional 1500 burst.
- Performance objective for this unit: trend monitoring and regression control (best-effort latency target).
- Validation modality: acceptance/load test profiles separate from unit correctness tests.

## 3) Resilience and Data-Dependency Handling
- Delegated policy/metadata fallback:
  - bounded last-known-good cache strategy
  - hard fail-closed after TTL expiry
- Key rotation behavior:
  - immediate effectiveness for new validation/issuance checks

## 4) Observability Stack Requirements
- Logging: structured logs with correlation identifiers and safe/non-sensitive payloads.
- Metrics: latency, deny/error counts, collision counters, issuance decision counters.
- Tracing: distributed traces across auth/trust/mapping/issuance paths with propagation.

## 5) Audit Durability and Mutation Safety
- Durability model:
  - fail-closed for critical trust/lifecycle mutations
  - best-effort for lower-risk updates with explicit monitoring
- Audit event emphasis:
  - delegated trust changes
  - key rotation updates
  - principal revocation
  - issuance denials and collision resolution outcomes

## 6) Security Hardening Depth
- Effective depth for this unit (inherited strategy):
  - baseline controls
  - replay-protection hooks
  - nonce/jti validation controls
- Security baseline rule alignment:
  - SECURITY-03, SECURITY-08, SECURITY-15

## 7) Rollout Verification Baseline
- Mandatory pre-broad-enable gate:
  - unit + integration tests
  - negative security regression matrix
- Matrix must cover:
  - unauthorized issuance deny
  - issuer mismatch/trust deny
  - mapping collision reject and controlled override
  - typed error/HTTP mapping consistency

## 8) Portability and Environment Independence
- No environment-specific canary infrastructure required as mandatory baseline for this unit.
- Advanced deployment-profile validation remains recommended extension guidance.
