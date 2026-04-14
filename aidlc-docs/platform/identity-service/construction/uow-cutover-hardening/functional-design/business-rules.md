# Business Rules - uow-cutover-hardening

## Rule Set

### BR-01 One-Time Cutover
JWT-only behavior is activated via release cutover; no runtime feature flag controls auth mode reversal.

### BR-02 Secured Endpoint JWT Requirement
All secured non-public endpoints require valid JWT after cutover.

### BR-03 Token Issuance Endpoint Exception
Token issuance endpoint uses trusted-caller authentication contract and is the only secured JWT-exempt path.

### BR-04 Public Endpoint Boundary
Only approved health/discovery endpoints are public.

### BR-05 Self-Issue Baseline
Token issuance authorization defaults to self-issue only.

### BR-06 Override Authorization Source
Issue-for-other requires explicit override authority from caller auth context, never from request payload assertions.

### BR-07 Override Reason Requirement
Issue-for-other requests must include explicit override reason/scope context.

### BR-08 Tenant Boundary Enforcement
Caller tenant and target principal tenant constraints must pass before issuance.

### BR-09 Override Audit Requirement
Every override decision must emit structured audit telemetry.

### BR-10 Canonical Tenant Contract
Active interfaces must use `tenant_id` only.

### BR-11 No Active Compatibility Alias
Dual naming compatibility aliases are not retained in active contract path for this release.

### BR-12 Production Signing Policy
Normal production path signs platform-issued JWTs with RS256 under identity-service private key custody.

### BR-13 Production Verification Policy
Normal production path verifies JWTs using JWKS/public-key distribution.

### BR-14 HS256 Restriction
HS256 is not allowed as normal production fallback; if present at all, it is explicit non-production test mode.

### BR-15 Unknown kid Handling
Unknown `kid` must be denied fail-closed.

### BR-16 Rotation Overlap Window
Key rotation supports explicit overlap window with deterministic old-key rejection after expiry.

### BR-17 No Permissive Key Fallback
Verifier must not accept tokens by trying arbitrary keys when `kid` resolution fails.

### BR-18 Legacy Access Denial Telemetry
Denied legacy/header-only requests must emit structured decision telemetry with reason code.

### BR-19 Logging Safety
Telemetry must exclude raw token material, secrets, and sensitive credential content.

### BR-20 Rollback Runbook Requirement
Rollback must be defined as release/deployment procedure with deterministic steps.

### BR-21 Rollback Verification Requirement
Rollback flow must include entry criteria, execution checks, and post-rollback validation signals.

### BR-22 Delegated Issuer Finalization
Delegated issuer OIDC/JWKS validation finalization is required in this unit within approved scope.

### BR-23 Delegated Scope Guardrail
Delegated validation work must stay bounded to approved trust-validation behaviors and policy-gated claim acceptance.

### BR-24 Fail-Closed Default
All authentication, authorization, and trust-validation failures deny access by default.

### BR-25 Safe Error Envelope
Failure responses must be safe, deterministic, and non-leaking.

## Security Baseline Alignment
- SECURITY-03 (Application logging): BR-09, BR-18, BR-19.
- SECURITY-08 (Application access control): BR-02, BR-03, BR-05, BR-06, BR-08.
- SECURITY-10 (Supply chain): N/A in functional design artifact (handled in code/build stage).
- SECURITY-11 (Secure design): BR-01, BR-10, BR-22, BR-23.
- SECURITY-14 (Alerting and monitoring): BR-09, BR-18, BR-21.
- SECURITY-15 (Fail-safe defaults): BR-15, BR-17, BR-24, BR-25.