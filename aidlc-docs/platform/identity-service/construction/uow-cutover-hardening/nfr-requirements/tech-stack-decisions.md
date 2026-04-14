# Tech Stack Decisions - uow-cutover-hardening

## Decision Context
These decisions map NFR requirements for hard cutover into implementation and validation expectations for identity-service and related consumers.

## 1) Runtime and Contract Boundaries
- Preserve current Python service/runtime boundaries and existing package layout.
- Enforce JWT-only secured endpoint policy in normal production path.
- Keep issuance endpoint as trusted-caller authenticated entry path.
- Enforce canonical `tenant_id` active contract with no dual-name compatibility path.

## 2) Signing and Verification
- Production signing contract: RS256 with identity-service private key custody.
- Verification contract: JWKS/public-key distribution path.
- Unknown `kid` or signature failure: deny fail closed.
- No permissive downgrade behavior to HS256 in normal production path.

## 3) Discovery, Caching, and Rotation
- Use bounded last-known-good cache for temporary JWKS/OIDC retrieval failures.
- Cache expiry with unresolved trust source triggers fail-closed behavior.
- Key propagation objective: <= 5 minutes.
- Rotation model uses explicit overlap window with deterministic old-key rejection after expiry.

## 4) Observability and Alerting
- Required telemetry depth: structured logs + metrics + tracing correlation.
- Required security-oriented alerts:
  - denial spikes (including legacy/header denial patterns)
  - admin-override anomaly patterns
  - unknown kid/signature failure spikes
- Dependency policy:
  - no forced new monitoring vendor dependency
  - use existing soorma-core observability tooling where available

## 5) Performance and Load Validation
- Latency objective: p95 <= 100 ms for secured JWT-authenticated request paths.
- Throughput profile: tiered baseline (100/500/1000 sustained, optional bounded burst).
- Validation expectations:
  - correctness and deny-path behavior under load
  - measurable latency and error-rate reporting

## 6) Rollback and Operational Safety
- Rollback is release/deployment based (not runtime mode toggle).
- Maintain deterministic rollback runbook:
  - entry criteria
  - execution steps
  - post-rollback verification checks
- Rollback readiness is required before proceeding to later construction stages.

## 7) Local Development Bootstrap
- Current state: `soorma dev` local bootstrap defaults to symmetric HS256 shared-secret setup.
- Target for this unit: change `soorma dev` default bootstrap to asymmetric (RS256 keypair + JWKS wiring).
- After this unit's cutover implementation, HS256 is not the default local path.
- Local developer ergonomics are addressed via automation, not by weakening production-aligned trust contracts.

## 8) Delegated Issuer Finalization
- OIDC/JWKS delegated validation finalization is in scope for this unit.
- Implementation is bounded to approved scope only:
  - trust metadata validation
  - key retrieval/cache/rotation behavior
  - policy-gated delegated claim acceptance
- Any expansion beyond this scope requires explicit re-baselining.
