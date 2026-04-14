# Business Logic Model - uow-cutover-hardening

## Purpose
Define functional behavior for final JWT cutover and hardening with a release-boundary migration model: no runtime compatibility flag, no dual tenant contract, and deterministic fail-closed security controls.

## Scope
- One-time release cutover to JWT-only behavior for secured endpoints.
- Token issuance endpoint remains a controlled trusted-caller entry path.
- Issuance authorization policy is self-issue default plus explicit admin override.
- Immediate convergence to canonical `tenant_id` in active contracts.
- Production signing and verification posture: RS256 plus JWKS/public-key verification.
- Unknown `kid` and signature/key mismatch decisions are fail-closed.
- Structured audit telemetry for denial and override decisions.
- Release/deployment rollback readiness with deterministic verification checks.
- Finalize delegated issuer OIDC/JWKS validation within approved unit scope.

## Transaction and Decision Boundaries
1. Ingress auth boundary:
   - Decides whether request is JWT-authenticated, trusted-caller issuance flow, or denied.
2. Issuance policy boundary:
   - Decides self-issue vs. override eligibility and tenant-bound constraints.
3. Canonical tenant boundary:
   - Enforces single `tenant_id` contract on active interfaces.
4. Verifier/key boundary:
   - Resolves JWKS/public key and evaluates `kid` plus signature validity.
5. Audit boundary:
   - Emits deterministic decision telemetry without sensitive token leakage.
6. Rollback boundary:
   - Executes release rollback procedure and verifies post-rollback safety signals.

## Core Workflows

### BLM-1 Release-Boundary Cutover
1. Deploy cutover release with JWT-only secured endpoint policy.
2. Remove legacy header-auth processing path from active request flow.
3. Validate cutover with deterministic verification checks.
4. Keep no runtime feature-flag path for reverting auth mode.

### BLM-2 Secured Request Authentication Matrix
1. For non-public secured endpoints, require valid JWT.
2. For token issuance endpoint, require trusted-caller authentication contract.
3. For health/discovery endpoints, allow unauthenticated access by policy.
4. Deny all other invalid paths fail-closed.

### BLM-3 Token Issuance Authorization
1. Authenticate trusted caller.
2. If caller requests token for self, allow when policy and tenant checks pass.
3. If caller requests token for other principal, require explicit override authority.
4. Require override reason and scope context for issue-for-other path.
5. Deny unauthorized or cross-tenant requests fail-closed.

### BLM-4 Admin Override Path
1. Resolve override authority from caller auth context (JWT scopes/roles or server-side credential policy mapping).
2. Reject any request where override is implied only by payload fields.
3. Enforce tenant-bound checks before issuance.
4. Emit structured override audit event with actor, target, reason, and correlation id.

### BLM-5 Canonical Tenant Contract Convergence
1. Accept and emit `tenant_id` as the only active tenant identifier.
2. Remove compatibility alias behavior from active interfaces.
3. Reject incompatible contract payloads through explicit validation errors.

### BLM-6 Signing and Verification Policy
1. Sign issued JWTs using identity-service private key custody (RS256).
2. Verify tokens in consumers using JWKS/public-key distribution path.
3. Do not downgrade verifier behavior to HS256 in normal production path.
4. Local developer stack uses asymmetric bootstrap automation via soorma dev CLI.

### BLM-7 Key Resolution and Rotation
1. Resolve verification key by `kid` from active JWKS/public key set.
2. If `kid` unknown, deny fail-closed.
3. Support explicit overlap window for key rotation.
4. After overlap window expiry, deny old key signatures.

### BLM-8 Legacy Denial Telemetry
1. Detect header-only or invalid legacy access attempts post-cutover.
2. Deny request safely without disclosing sensitive internals.
3. Emit telemetry containing decision outcome and reason code.

### BLM-9 Release/Deployment Rollback
1. Enter rollback only when predefined trigger criteria are met.
2. Execute deployment rollback procedure (not runtime flag reversal).
3. Run post-rollback verification checks for auth correctness and safety.
4. Publish rollback result telemetry and recovery status.

### BLM-10 Delegated Issuer OIDC/JWKS Finalization
1. Validate delegated issuer trust metadata under approved policy constraints.
2. Resolve delegated issuer keys through OIDC/JWKS path.
3. Apply policy-gated delegated claim acceptance.
4. Deny untrusted issuer or invalid delegated-token paths fail-closed.

## Output Contracts
- No runtime auth-mode toggle in production path.
- Endpoint auth matrix explicitly defined and enforced.
- Canonical `tenant_id` is the only active tenant identifier.
- Issuance override contract requires caller authority plus explicit reason/scope context.
- Verifier contract requires RS256 plus JWKS/public-key path in normal production.
- Rollback contract is release/deployment procedure with deterministic validation checkpoints.

## Security and Reliability Controls
- SECURITY-03: Structured telemetry for denial, override, rotation, and rollback decisions.
- SECURITY-08: Server-side auth and object/function-level authorization enforcement.
- SECURITY-11: Security-critical logic remains modularized by boundary (auth, policy, key management, telemetry).
- SECURITY-14: Decision telemetry fields support alerting on denial spikes and override anomalies.
- SECURITY-15: All failure paths are fail-closed with safe response envelopes.

## QA Traceability
- TC-UCH-001: JWT-only ingress success after cutover.
- TC-UCH-002: Header-only request denied post-cutover.
- TC-UCH-003: Security telemetry emitted for denied legacy access.