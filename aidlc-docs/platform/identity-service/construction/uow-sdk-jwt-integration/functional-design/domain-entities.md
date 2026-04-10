# Domain Entities - uow-sdk-jwt-integration

## Modeling Boundary
This unit defines functional entities and value objects for SDK JWT integration behavior, compatibility controls, issuance caller-auth policy, and bootstrap safety semantics.

## Core Entities

### SdkJwtOutboundContext
- Purpose: Canonical outbound identity/auth context derived from JWT claims.
- Key attributes:
  - jwt_subject
  - tenant_id
  - principal_id
  - principal_type
  - roles
  - issuer
  - audience
  - expires_at
  - correlation_id

### CompatibilityAliasEnvelope
- Purpose: Optional legacy alias values observed on compatibility paths.
- Key attributes:
  - alias_tenant_id (optional)
  - alias_user_id (optional)
  - alias_source
  - present_flag

### AliasMismatchDecision
- Purpose: Deterministic result of defensive alias validation.
- Key attributes:
  - allowed (boolean)
  - reason_code (`ALIAS_MATCH`, `ALIAS_ABSENT`, `ALIAS_TENANT_MISMATCH`)
  - enforced_action (`ALLOW`, `DENY_FAIL_CLOSED`)

### IssuanceCallerAuthContext
- Purpose: Caller authentication and authorization state for token issuance request.
- Key attributes:
  - auth_mode (`ADMIN_KEY_COMPAT`)
  - caller_principal_id
  - caller_tenant_id
  - scopes
  - admin_override_requested
  - auth_status

### IssuanceAuthorizationDecision
- Purpose: Decision object for self-issue vs admin override path.
- Key attributes:
  - allowed (boolean)
  - policy_path (`SELF_ISSUE`, `ADMIN_OVERRIDE`)
  - deny_reason_code
  - target_principal_id
  - tenant_boundary_valid

### SigningMaterialDescriptor
- Purpose: Identity-service signing key contract for issued JWTs.
- Key attributes:
  - algorithm
  - kid
  - private_key_ref
  - key_state

### VerifierDistributionPolicy
- Purpose: Compatibility verifier model for consumers.
- Key attributes:
  - static_key_enabled
  - jwks_enabled
  - precedence_order
  - cache_ttl
  - unknown_kid_behavior

### BootstrapExecutionState
- Purpose: State model for idempotent `soorma dev` tenant bootstrap.
- Key attributes:
  - tenant_exists
  - protected_drift_detected
  - immutable_field_drift
  - action_taken
  - outcome_code (`CREATED`, `REUSED`, `FAILED_DRIFT`)

### SdkAuthExceptionEnvelope
- Purpose: Typed SDK exception payload for JWT/auth failures.
- Key attributes:
  - exception_type
  - category
  - safe_message
  - http_status_hint
  - reason_code
  - correlation_id

## Value Objects

### WrapperCompatibilityInvariant
Represents invariant that wrapper signatures remain unchanged during this unit.

### TenantBoundaryTuple
Represents caller/target tenant binding tuple used by issuance policy checks.

### AuditDecisionRecord
Represents structured audit payload for override, mismatch, and bootstrap decisions.

## Invariants
1. JWT claim tenant is canonical for outbound SDK identity context.
2. If alias envelope is present, alias tenant must equal canonical JWT tenant.
3. Any canonical-vs-alias mismatch causes deny fail-closed.
4. Issuance caller-auth compatibility path cannot become signing path.
5. Issued JWTs are always signed by identity-service asymmetric signing material.
6. Self-issue is default; admin override requires explicit scoped authorization.
7. Bootstrap idempotency cannot silently overwrite immutable identity/trust fields.
8. SDK auth failures surface as typed safe exceptions.

## Conceptual Repositories/Services
- JwtContextResolver
- CompatibilityAliasValidator
- IssuancePolicyEvaluator
- SigningMaterialProvider
- VerifierPolicyResolver
- BootstrapStateEvaluator
- SdkErrorMapper
- SecurityAuditEmitter
