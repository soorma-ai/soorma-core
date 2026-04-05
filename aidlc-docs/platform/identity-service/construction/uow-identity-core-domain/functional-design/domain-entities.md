# Domain Entities - uow-identity-core-domain

## Modeling Boundary
This artifact defines domain entities and repository contracts (Q8 = B). It intentionally avoids physical schema design.

## Core Entities

### PlatformTenantIdentityDomain
- Purpose: Root trust boundary for a platform tenant.
- Key attributes:
  - tenant_domain_id
  - platform_tenant_id
  - status (active, suspended)
  - created_at, created_by
  - default_policy_refs

### Principal
- Purpose: Human or machine identity under a tenant domain.
- Key attributes:
  - principal_id
  - tenant_domain_id
  - principal_type (human, machine)
  - lifecycle_state (active, suspended, revoked)
  - external_ref (optional)
  - created_at, updated_at

### RoleAssignment
- Purpose: Role linkage for principal authorization.
- Key attributes:
  - assignment_id
  - principal_id
  - role_name
  - role_scope (platform_baseline, tenant_extension)
  - granted_by, granted_at

### DelegatedIssuer
- Purpose: Trusted external issuer metadata.
- Key attributes:
  - delegated_issuer_id
  - tenant_domain_id
  - issuer_id
  - status
  - jwk_set_ref_or_material
  - audience_policy_ref
  - claim_mapping_policy_ref
  - created_by, created_at

### ClaimMappingPolicy
- Purpose: Rule set for normalizing delegated claims into canonical keys.
- Key attributes:
  - mapping_policy_id
  - tenant_domain_id
  - policy_version
  - mode (reject_on_collision, deterministic_merge)
  - namespace_rules
  - precedence_rules

### ExternalIdentityBinding
- Purpose: Persisted binding between external asserted identity and canonical principal.
- Key attributes:
  - binding_id
  - tenant_domain_id
  - source_issuer_id
  - external_identity_key
  - canonical_identity_key
  - principal_id
  - verification_state
  - created_at, updated_at

### TokenIssuanceRecord
- Purpose: Audit-supporting record of issuance decisions.
- Key attributes:
  - issuance_id
  - tenant_domain_id
  - principal_id
  - issuance_type (platform, delegated)
  - decision (issued, denied)
  - decision_reason_code
  - issued_at

### IdentityAuditEvent
- Purpose: Security and lifecycle event capture.
- Key attributes:
  - event_id
  - tenant_domain_id
  - event_type
  - actor
  - correlation_id
  - payload_summary
  - emitted_at

## Value Objects

### CanonicalIdentityKey
- Deterministic internal identity key computed from mapping policy.

### DelegatedIdentityAssertion
- Parsed delegated claim set prior to mapping/binding.

### TrustDecision
- Encapsulates issuer trust evaluation result and reason code.

### ErrorEnvelope
- Domain error contract with typed code, HTTP mapping, safe message, correlation_id.

## Invariants
1. Principal belongs to exactly one tenant domain.
2. Platform-baseline role semantics are fixed for soorma-core authorization.
3. Tenant-extension roles do not imply platform privilege.
4. Delegated issuance requires trusted active issuer and policy authorization.
5. Binding collisions default to reject unless deterministic merge is explicitly enabled.
6. Canonical remap requires explicit admin override operation.

## Repository Contracts (Conceptual)
- TenantDomainRepository
- PrincipalRepository
- RoleAssignmentRepository
- DelegatedIssuerRepository
- ClaimMappingPolicyRepository
- ExternalIdentityBindingRepository
- TokenIssuanceRepository
- IdentityAuditEventRepository

## Domain Services (Conceptual)
- OnboardingDomainService
- PrincipalLifecycleService
- DelegatedTrustService
- TokenIssuanceService
- MappingAndBindingService
- IdentityErrorMapper
- AuditTelemetryService
