# Business Rules - uow-identity-core-domain

## Rule Set

### BR-01 Onboarding Authority
Only trusted onboarding authority may create a new tenant domain:
- Operator-admin control-plane path, or
- Controlled self-service claim/invite token flow.

### BR-02 Onboarding Atomicity
Tenant domain and bootstrap admin must be created atomically.

### BR-03 Machine Bootstrap Default
Machine-principal bootstrap is optional and disabled by default.

### BR-04 Runtime Onboarding
Platform tenant onboarding is a runtime business operation, not deployment-time pre-seeding.

### BR-05 Baseline Role Governance
Platform baseline roles are authoritative for soorma-core access control:
- admin, developer, planner, worker, tool.

### BR-06 Tenant Role Extension Constraint
Tenant-defined extension roles are allowed only as namespaced delegated claims or tenant-owned access-control metadata.

### BR-07 No Implicit Privilege Escalation
Tenant extension roles must never auto-map to platform privileged roles.

### BR-08 Delegated Issuer Minimum Fields
Delegated issuer registration requires:
- issuer_id
- jwk_set/signing key material
- status
- created_by
- audience policy reference
- claim mapping policy reference

### BR-09 Day-1 Operability
Tenant must be operational day-1 without delegated-flow setup by using baseline platform-principal issuance.

### BR-10 Issuance Scope
Before full SDK JWT rollout completion:
- Platform-principal issuance is allowed on trusted existing call paths.
- Delegated issuance is allowed only under registered issuer + policy gating.

### BR-11 Mandatory Claim Contract
Issued tokens must contain mandatory base claims per FR-7.

### BR-12 Delegated Claim Contract
Delegated claims are optional and accepted only when explicit route/policy checks pass.

### BR-13 Mapping Collision Default
Collision handling default is reject_on_collision.

### BR-14 Deterministic Merge Optionality
deterministic_merge is optional and tenant opt-in; bounded to approved delegated/machine contexts.

### BR-15 Deterministic Precedence
Collision precedence order:
1. Active trusted issuer over inactive/untrusted issuer
2. Existing verified binding over new unverified binding
3. If both verified, preserve earliest canonical binding and reject automatic remap

### BR-16 Remap Safety
Canonical remap requires explicit admin override operation; no silent background remap.

### BR-17 Typed Error Contract
Trust and lifecycle failures must return domain-specific typed error codes with stable HTTP mapping.

### BR-18 Safe Error Envelope
Error responses must avoid sensitive details and include correlation context.

### BR-19 Audit Write-Side Durability
Critical mutations (issuer trust changes, key rotation, principal revocation) are fail-closed on audit-write failure. Lower-risk updates may be best-effort with explicit monitoring.

### BR-20 Persistence Boundary
Functional design defines domain entities and repository contracts; schema-level detail is deferred from this stage.

### BR-21 Test Coverage Contract
Functional design requires:
- Unit tests for domain services and validators
- API integration tests for onboarding, lifecycle, issuance, delegated trust
- Negative security regression matrix for unauthorized issuance, issuer mismatch, and mapping collisions

### BR-22 Event Coverage
Identity-domain event catalog is emitted in this unit for core lifecycle and security outcomes.

## Security Alignment
- SECURITY-03: Structured event/audit logging with non-sensitive payloads
- SECURITY-08: Server-side authorization and policy checks at all protected operations
- SECURITY-15: Fail-closed behavior and safe exception response patterns
