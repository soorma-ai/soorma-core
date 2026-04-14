# Domain Entities - uow-cutover-hardening

## Modeling Boundary
This unit models cutover enforcement, issuance authorization, canonical contract convergence, cryptographic trust validation, and release rollback behavior for hardening phase completion.

## Core Entities

### CutoverReleaseState
- Purpose: Represents one-time release-boundary cutover status.
- Key attributes:
  - release_id
  - cutover_applied_at
  - jwt_only_enforced
  - runtime_toggle_present (must be false)

### SecuredEndpointAuthPolicy
- Purpose: Defines per-endpoint auth requirements after cutover.
- Key attributes:
  - endpoint_name
  - requires_jwt
  - trusted_caller_allowed
  - public_endpoint

### IssuanceCallerAuthContext
- Purpose: Captures authenticated caller identity for token issuance requests.
- Key attributes:
  - caller_principal_id
  - caller_tenant_id
  - auth_mode (`CALLER_JWT`, `ADMIN_KEY`)
  - caller_roles
  - caller_scopes

### AdminOverrideAuthorizationGrant
- Purpose: Represents authority to issue token for target principal other than caller.
- Key attributes:
  - override_allowed
  - authority_source (`JWT_SCOPE`, `SERVER_POLICY_BINDING`)
  - required_scope
  - required_role
  - reason_required

### IssuanceDecision
- Purpose: Deterministic issuance authorization result.
- Key attributes:
  - allowed
  - decision_path (`SELF_ISSUE`, `ADMIN_OVERRIDE`, `DENY`)
  - deny_reason_code
  - target_principal_id
  - tenant_boundary_valid

### CanonicalTenantContract
- Purpose: Active interface tenant identity contract.
- Key attributes:
  - tenant_id
  - alias_present (must be false on active path)
  - contract_version

### SigningPolicyProfile
- Purpose: Defines token signing contract for normal production.
- Key attributes:
  - algorithm (`RS256`)
  - signer_key_ref
  - key_custody_owner (`identity-service`)
  - production_fallback_allowed (must be false)

### VerifierKeySetState
- Purpose: Tracks active verification keys resolved from JWKS/public-key source.
- Key attributes:
  - jwks_uri
  - active_kids
  - fetched_at
  - cache_ttl

### KeyRotationWindow
- Purpose: Represents explicit overlap period for key rotation.
- Key attributes:
  - old_kid
  - new_kid
  - overlap_start
  - overlap_end
  - post_window_old_key_allowed (must be false)

### KeyResolutionDecision
- Purpose: Captures verifier decision for token key resolution.
- Key attributes:
  - kid
  - key_found
  - signature_valid
  - decision (`ALLOW`, `DENY_FAIL_CLOSED`)
  - reason_code (`UNKNOWN_KID`, `INVALID_SIGNATURE`, `EXPIRED_ROTATION_WINDOW`)

### LegacyAccessDenialRecord
- Purpose: Structured record for denied legacy/header-only access.
- Key attributes:
  - event_type
  - timestamp
  - correlation_id
  - tenant_id
  - outcome
  - denial_reason_code

### AuthDecisionTelemetryEvent
- Purpose: Unified telemetry event for authz/authn decisions.
- Key attributes:
  - event_name
  - decision
  - actor_principal_id
  - target_principal_id
  - tenant_id
  - correlation_id
  - reason_code

### RollbackRunbook
- Purpose: Defines release/deployment rollback procedure.
- Key attributes:
  - entry_criteria
  - execution_steps
  - verification_checks
  - owner

### RollbackExecutionState
- Purpose: Captures runtime status of rollback procedure execution.
- Key attributes:
  - rollback_started_at
  - rollback_completed_at
  - status
  - verification_passed
  - incident_reference

### DelegatedIssuerTrustProfile
- Purpose: Tenant-scoped delegated issuer trust definition for OIDC/JWKS validation.
- Key attributes:
  - issuer_id
  - issuer_uri
  - jwks_uri
  - audience_constraints
  - trust_status

### DelegatedJwksValidationState
- Purpose: Tracks delegated issuer key retrieval and validation status.
- Key attributes:
  - issuer_id
  - last_refresh_at
  - active_kids
  - validation_status
  - failure_reason

## Value Objects

### TenantBoundaryTuple
Represents caller and target tenant relation used in issuance authorization checks.

### OverrideContext
Represents required override reason/scope payload and policy linkage.

### VerificationSignalSet
Represents deterministic checks used for cutover and rollback verification.

## Invariants
1. JWT-only secured endpoint policy is active after cutover release.
2. Token issuance trusted-caller path does not bypass issuance authorization policy.
3. Issue-for-other requires explicit override authority from caller auth context.
4. Request payload cannot grant override authority.
5. Active contract uses canonical `tenant_id` only.
6. Production signing policy is RS256 with identity-service private key custody.
7. Verifier resolution denies fail-closed for unknown `kid` or invalid signature.
8. Rotation window enforces old-key rejection after overlap expiry.
9. Denied legacy requests always emit structured telemetry with safe fields.
10. Rollback remains release/deployment procedure, not runtime auth-mode toggling.
11. Delegated issuer OIDC/JWKS validation finalization remains bounded to approved unit scope.

## Conceptual Services
- CutoverPolicyEvaluator
- SecuredEndpointAuthRouter
- IssuanceAuthorizationEvaluator
- OverrideAuthorityResolver
- CanonicalContractValidator
- SigningPolicyEnforcer
- VerifierKeyResolver
- RotationWindowEvaluator
- AuthTelemetryEmitter
- RollbackCoordinator
- DelegatedIssuerValidationService