# Business Rules - uow-sdk-jwt-integration

## Rule Set

### BR-01 Canonical Outbound Identity Source
JWT claims are the canonical source for outbound SDK identity context in this unit.

### BR-02 Legacy Alias Optionality
Legacy compatibility alias fields are not required on canonical outbound path.

### BR-03 Defensive Alias Validation
If legacy alias fields appear, they must match canonical JWT tenant identity.

### BR-04 Mismatch Denial
Any JWT-vs-alias tenant mismatch is denied fail-closed.

### BR-05 Wrapper API Stability
Existing wrapper signatures must remain unchanged in this unit.

### BR-06 Internal JWT Injection
JWT transport/auth behavior is injected inside wrappers/clients, not caller APIs.

### BR-07 Issuance Caller Authentication (Compatibility)
Compatibility-phase issuance requests may use temporary admin key caller-auth.

### BR-08 Signing Key Separation
Admin key authenticates caller only; issued JWTs must be signed with identity-service asymmetric signing keys.

### BR-09 Issuance Authorization Policy
Default is self-issue only; admin override is permitted only for scoped authorized callers.

### BR-10 Tenant Boundary Enforcement
Issuance requests violating tenant-bound policy constraints are denied fail-closed.

### BR-11 Override Audit Requirement
Every admin override path must emit structured audit records including actor, target, reason, and correlation context.

### BR-12 Verifier Distribution Policy
Compatibility verifier model supports both static key fallback and JWKS, with deterministic precedence.

### BR-13 CLI Bootstrap Idempotency
`soorma dev` tenant bootstrap uses strict idempotent behavior: create-if-absent, verify-if-present.

### BR-14 Drift Protection
Protected drift detected during idempotent bootstrap must fail-closed.

### BR-15 Explicit Bootstrap Outcome
Bootstrap must return explicit outcome codes: `CREATED`, `REUSED`, `FAILED_DRIFT`.

### BR-16 Immutable Field Safety
Immutable identity/trust fields cannot be silently changed during bootstrap reuse.

### BR-17 SDK Error Contract
JWT/auth failures must surface as typed SDK exceptions with stable categories and safe messages.

### BR-18 Error Detail Safety
Raw HTTP/internal verification details must not be leaked in SDK-facing errors.

### BR-19 Test Coverage Baseline
Mandatory matrix includes wrapper unit tests, SDK-service integration happy paths, and negative security regression paths.

### BR-20 Negative Security Paths
At minimum, negative matrix covers invalid JWT, unknown `kid`, tenant mismatch, and unauthorized issue-for-other.

## Security Baseline Alignment
- SECURITY-03: Structured audit/logging required for overrides, mismatch denials, and bootstrap outcomes.
- SECURITY-08: Server-side authorization checks required for issuance and tenant-bound decisions.
- SECURITY-13: Signature/key-path integrity enforced via asymmetric signing and deterministic verifier precedence.
- SECURITY-15: All auth and policy failures fail closed with safe error envelopes.
