# User Stories - Identity Service Initiative

## Story Organization
Primary organization: **Hybrid Epic + Persona + Feature**.
Default acceptance style: **Hybrid Given/When/Then + checklist constraints**.

## Epic 1: Platform Tenant and Principal Lifecycle

### US-1.1 Tenant Onboarding Bootstrap
- **Persona**: Platform Administrator
- **Story**: As a Platform Administrator, I want to onboard a platform tenant with bootstrap admin and optional machine principal setup so that identity governance starts from a secure, consistent baseline.
- **Requirements Traceability**: FR-1, FR-2, FR-4
- **INVEST Notes**:
  - Independent: Can be implemented as an onboarding workflow boundary.
  - Valuable: Enables all downstream identity operations.
  - Small/Testable: Focused on onboarding transaction completion criteria.
- **Acceptance Criteria**:
  - Given a valid onboarding request, when onboarding is submitted, then a platform-tenant identity domain is created.
  - Given bootstrap settings include admin principal, when onboarding completes, then admin role assignment is persisted.
  - Given optional machine bootstrap enabled, when onboarding completes, then machine principal(s) are provisioned with declared role(s).
  - Checklist: onboarding operation writes an auditable event with tenant and actor metadata.

### US-1.2 Principal Lifecycle Management
- **Persona**: Platform Administrator, Machine Principal Operator
- **Story**: As a tenant operator, I want to create/update/revoke human and machine principals so that access is controlled by role and lifecycle state.
- **Requirements Traceability**: FR-2, FR-3, FR-13
- **Acceptance Criteria**:
  - Given an existing tenant domain, when a principal is created, then role validation enforces allowed role sets.
  - Given a principal state update, when revoke is executed, then token issuance is denied for revoked principal state.
  - Given lifecycle operations, when they are performed, then structured audit events are emitted.
  - Checklist: role assignment supports `admin`, `developer`, and machine role family.

## Epic 2: Delegated Trust and Namespace Governance

### US-2.1 Delegated Issuer Registration
- **Persona**: Platform Administrator, Delegated Issuer Administrator
- **Story**: As a Delegated Issuer Administrator, I want to register delegated issuer trust metadata per tenant so that delegated JWT assertions can be validated under explicit policy.
- **Requirements Traceability**: FR-5, FR-8
- **Acceptance Criteria**:
  - Given tenant-scoped issuer registration, when issuer metadata is added, then trust config is stored under that tenant boundary.
  - Given unregistered issuer input, when delegated validation is attempted, then access is denied.
  - Given trust metadata updates, when keys rotate, then new keys can be activated without broad service refactors.
  - Checklist: v1 supports static allowlist; v2 readiness tracks OIDC/JWKS metadata fields.

### US-2.2 External Principal Mapping Policy
- **Persona**: Delegated Issuer Administrator
- **Story**: As a tenant trust operator, I want configurable mapping rules for external principal identifiers so that canonical identity keys are consistent while auth remains tuple-authoritative.
- **Requirements Traceability**: FR-9
- **Acceptance Criteria**:
  - Given mapping policy configured for a tenant, when delegated identity is processed, then canonical principal key generation is deterministic.
  - Given conflicting external identifier forms, when mapping runs, then collisions are prevented or rejected with safe error.
  - Checklist: mapping policy does not override platform/service tuple authorization source of truth.

## Epic 3: Token Issuance and Claim Contract

### US-3.1 Platform Principal JWT Issuance
- **Persona**: Platform Administrator, Platform Developer
- **Story**: As a platform engineer, I want JWT issuance for platform human and machine principals so that ingress auth can be enforced consistently across services.
- **Requirements Traceability**: FR-6, FR-7, FR-10
- **Acceptance Criteria**:
  - Given an active principal, when token issuance is requested, then mandatory claims are present (`iss`, `sub`, `aud`, `exp`, `iat`, `jti`, `platform_tenant_id`, `principal_id`, `principal_type`, `roles`).
  - Given invalid principal state, when token issuance is requested, then issuance is denied fail-closed.
  - Checklist: token issuance decisions are logged without leaking secret/token payload details.

### US-3.2 Delegated Context Claim Handling
- **Persona**: Machine Principal Operator, Delegated Issuer Administrator
- **Story**: As a trust-boundary owner, I want delegated `service_tenant_id` and `service_user_id` claims accepted only under approved policy so that delegated context is constrained to trusted flows.
- **Requirements Traceability**: FR-7, FR-8
- **Acceptance Criteria**:
  - Given trusted machine or validated delegated issuer flow, when optional delegated claims are supplied, then policy-gated acceptance is evaluated.
  - Given non-trusted flow, when delegated claims are supplied, then claims are rejected and access is denied.
  - Checklist: policy decision output is observable via structured audit logs.

## Epic 4: Incremental JWT Rollout and SDK Compatibility

### US-4.1 Shared Dependency JWT Coexistence
- **Persona**: Platform Developer
- **Story**: As a platform developer, I want JWT support introduced inside existing `soorma-service-common` dependencies so that services keep current DI/router call sites unchanged during rollout phase 1.
- **Requirements Traceability**: FR-11, FR-12
- **Acceptance Criteria**:
  - Given existing service routes, when JWT mode is enabled, then existing dependency injection call sites remain unchanged.
  - Given coexistence phase, when header-based context is still present, then both auth mechanisms can be evaluated according to rollout policy.
  - Checklist: no parallel router dependency contract is introduced in phase 1.

### US-4.2 SDK JWT Client Upgrade
- **Persona**: Platform Developer
- **Story**: As an SDK maintainer, I want existing wrapper/client methods upgraded to send JWT-authenticated requests so that agent code and service integrations remain stable while auth shifts.
- **Requirements Traceability**: FR-11, FR-12
- **Acceptance Criteria**:
  - Given existing wrapper method usage, when SDK is upgraded, then callers do not need to change agent handler method signatures.
  - Given JWT-configured environment, when client requests are made, then JWT auth headers/tokens are transmitted correctly.
  - Checklist: direct low-level client usage in handlers remains prohibited and wrapper contract is preserved.

### US-4.3 Header Auth Removal Cutover
- **Persona**: Platform Developer, Platform Administrator
- **Story**: As a platform team, I want to remove legacy header-based auth after JWT path is complete so that the identity model is simplified and security posture is consistent.
- **Requirements Traceability**: FR-11
- **Acceptance Criteria**:
  - Given all JWT paths validated, when cutover is executed, then header-only auth is disabled.
  - Given legacy header-only requests, when received post-cutover, then requests are denied with safe error.
  - Checklist: cutover includes verification tests and rollback procedure notes in build/test instructions.

## Cross-Story Quality Checks
- All stories map to at least one persona and one FR.
- Compatibility constraints from FR-11 are explicit in Epic 4 stories.
- Story slices are implementation-sequencable for incremental PR merges.
- Acceptance criteria combine behavioral and constraint checks for testability.