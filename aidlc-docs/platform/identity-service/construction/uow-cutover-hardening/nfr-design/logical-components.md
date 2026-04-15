# Logical Components - uow-cutover-hardening NFR Design

## Component Inventory
| Component | Responsibility | Inputs | Outputs | Primary NFR Mapping |
|---|---|---|---|---|
| JwtVerificationOrchestrator | Coordinates token verification flow and fail-closed decisions | JWT, request context, verifier settings | Verified principal or deny reason | NFR-1, NFR-3, NFR-4 |
| VerifierKeyProvider | Resolves verification keys from JWKS and cache sources with strict precedence | `kid`, issuer metadata, cache state | Verification key material or typed retrieval error | NFR-3, NFR-4 |
| LastKnownGoodKeyCache | Stores bounded verifier keys for temporary trust-source outages | JWKS key set updates | Cached key entries with TTL metadata | NFR-3 |
| RotationCoordinator | Applies event invalidation and bounded polling refresh to meet propagation objective | Rotation events, polling schedule | Cache invalidation and refresh actions | NFR-4 |
| AuthDecisionTelemetryEmitter | Emits structured logs, metrics, and trace tags for auth decisions | Decision outcome + context | Telemetry events with reason codes | NFR-5 |
| SecurityAlertSignalPublisher | Produces canonical alert signals and threshold evaluations | Telemetry aggregates | Alert triggers for on-call systems | NFR-6 |
| RollbackReadinessValidator | Validates rollback entry criteria and post-rollback verification matrix completeness | Deployment state, runbook checks | Rollback readiness status and verification checklist | NFR-7 |
| DevBootstrapProvisioner | Automates local RS256 keypair and JWKS bootstrap for `soorma dev` | Local bootstrap config | Asymmetric default local trust assets | NFR-8 |
| DelegatedIssuerTrustEvaluator | Validates delegated issuer trust metadata and policy gates | Delegated issuer config, trust metadata | Trust decision and allowed issuer context | NFR-9 |
| DelegatedJwksResolver | Retrieves and refreshes delegated issuer keys with cache and rotation controls | Delegated issuer metadata, `kid` | Delegated verification key material or typed deny reason | NFR-9 |

## Design Interaction Flow
1. JwtVerificationOrchestrator receives token and calls VerifierKeyProvider.
2. VerifierKeyProvider attempts delegated or primary JWKS resolution based on trusted issuer context.
3. LastKnownGoodKeyCache is used only within TTL as resilience backstop.
4. If key resolution fails with cache expired or invalid trust state, orchestration returns fail-closed typed deny.
5. AuthDecisionTelemetryEmitter records decision metadata; SecurityAlertSignalPublisher evaluates thresholds.
6. RotationCoordinator maintains key freshness objective through event invalidation and polling backstop.

## Denial and Alert Contract
Minimum canonical denial reasons:
- `unknown_kid`
- `invalid_signature`
- `issuer_untrusted`
- `key_source_unavailable_cache_expired`

Alert contract groups:
- Denial spike alerts by reason family
- Override anomaly alerts
- Unknown `kid` / signature failure spike alerts

## Rollback Design Boundary
- Rollback model is deterministic deployment rollback only.
- Runtime policy toggles are not part of rollback mechanism.
- Post-rollback verification matrix must re-check token validation behavior, deny-path correctness, and tenant isolation outcomes.

## Security Baseline Applicability in This Artifact
- Compliant: SECURITY-03, SECURITY-08, SECURITY-11, SECURITY-14, SECURITY-15
- N/A at this stage: SECURITY-01, SECURITY-02, SECURITY-04, SECURITY-05, SECURITY-06, SECURITY-07, SECURITY-09, SECURITY-10, SECURITY-12, SECURITY-13

N/A rationale: these controls require code-level implementation, infrastructure definitions, credential/runtime configuration, or CI policy artifacts not produced during NFR design documentation.