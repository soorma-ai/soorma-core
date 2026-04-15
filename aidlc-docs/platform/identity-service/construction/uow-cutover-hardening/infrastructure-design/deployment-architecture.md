# Deployment Architecture - uow-cutover-hardening

## Overview
This deployment architecture maps the cutover-hardening logical components onto existing soorma-core runtime infrastructure while avoiding new platform services unless strictly required.

## Logical-to-Infrastructure Mapping
| Logical Component | Infrastructure Placement | Notes |
|---|---|---|
| JwtVerificationOrchestrator | identity-service application runtime | Runs inside existing service instances |
| VerifierKeyProvider | identity-service application runtime | Uses outbound HTTPS calls to allowlisted trust endpoints |
| LastKnownGoodKeyCache | In-memory process cache inside each instance | No external cache dependency |
| RotationCoordinator | identity-service runtime plus existing event bus subscription | Event-driven invalidation with polling backstop |
| AuthDecisionTelemetryEmitter | identity-service runtime to centralized observability sink | Structured logs, metrics, traces |
| SecurityAlertSignalPublisher | Existing monitoring/alerting stack | Reuses current alerting infrastructure |
| RollbackReadinessValidator | Manual operational runbook procedure | No dedicated service or runtime API |
| DevBootstrapProvisioner | local `soorma dev` bootstrap workflow | Generates ephemeral RS256/JWKS artifacts |
| DelegatedIssuerTrustEvaluator | identity-service runtime | Applies allowlist and policy checks |
| DelegatedJwksResolver | identity-service runtime with restricted outbound network path | Trust retrieval only to approved endpoints |

## Runtime Architecture
1. A request reaches the existing identity-service deployment.
2. JwtVerificationOrchestrator and VerifierKeyProvider run inside the service instance.
3. When needed, the service makes outbound HTTPS calls only to allowlisted issuer metadata/JWKS endpoints.
4. Resolved verifier keys are cached locally in-process with bounded TTL.
5. Invalidation events arrive over the existing event bus; polling acts as bounded backstop.
6. Security telemetry is emitted to the centralized observability stack.

## Network Boundary Design
- Ingress: no new public ingress components are required by this unit.
- Egress: only approved delegated issuer endpoints may be reached from runtime environments.
- Trust retrieval traffic must use TLS and explicit destination restrictions per environment.
- Broad unrestricted outbound internet access is not part of the target architecture.

## Deployment and Rollback Shape
- Deployment model: in-place release rollout using existing service deployment path.
- Rollback model: manually executed documented rollback procedure.
- Post-deployment checks and post-rollback checks must verify:
  - JWT verification correctness
  - deny-path safety
  - delegated issuer trust behavior
  - tenant isolation correctness

## Local Development Architecture
- `soorma dev` bootstraps local asymmetric trust artifacts automatically.
- Local JWKS exposure and keypair generation are ephemeral per environment instance.
- HS256 is not the default local bootstrap architecture.

## Shared Infrastructure Decision
No new shared-infrastructure artifact is generated for this unit because the design reuses existing deployment, messaging, network-policy, and observability systems rather than introducing a new shared service.

## Security Baseline Applicability Summary
- Compliant: SECURITY-03, SECURITY-07, SECURITY-08, SECURITY-11, SECURITY-14, SECURITY-15
- N/A: SECURITY-01, SECURITY-02, SECURITY-04, SECURITY-05, SECURITY-06, SECURITY-09, SECURITY-10, SECURITY-12, SECURITY-13

N/A rationale: those controls require storage definitions, load balancer/gateway resources, IAM specifics, code-level validation, or build/runtime hardening artifacts not created in this stage.