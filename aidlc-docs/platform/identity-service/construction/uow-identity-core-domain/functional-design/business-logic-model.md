# Business Logic Model - uow-identity-core-domain

## Purpose
Define the core identity-domain business workflows for tenant onboarding, principal lifecycle, delegated trust registration, token issuance, mapping/binding, and audit emission.

## Scope and Preconditions
- Unit: uow-identity-core-domain
- Depends on: uow-shared-auth-foundation
- In scope:
  - Tenant onboarding with bootstrap admin
  - Principal lifecycle for human and machine principals
  - Delegated issuer registration (v1 static allowlist)
  - Token issuance for platform principals and policy-gated delegated flow
  - External identity mapping and binding collision handling
- Out of scope:
  - Full JWT cutover/header-path removal (later units)

## Transaction Boundaries
1. Onboarding atomic boundary:
   - Create platform-tenant identity domain and bootstrap admin in one transaction.
   - Optional machine bootstrap remains optional and disabled by default.
2. Post-onboarding principal operations:
   - Authenticated tenant-admin driven lifecycle operations.
3. Delegated issuer registration:
   - Independent transaction per issuer lifecycle operation.
4. Mapping/binding updates:
   - Isolated transaction with collision policy enforcement and audit emission.

## Core Workflows

### BLM-1 Tenant Onboarding
1. Validate onboarding authority (operator-admin or controlled self-service claim token).
2. Validate tenant bootstrap payload.
3. Create tenant domain and bootstrap admin atomically.
4. Initialize default token and mapping policy references.
5. Emit onboarding audit event.

Outcome:
- Tenant becomes operational day-1 using baseline platform-principal flows.

### BLM-2 Principal Lifecycle
1. Authorize caller as tenant admin.
2. Validate requested role set against baseline role model.
3. Create/update/revoke principal state.
4. Enforce state transitions (active -> revoked is terminal for issuance eligibility).
5. Emit lifecycle audit event.

### BLM-3 Delegated Issuer Registration
1. Authorize tenant admin/trust operator.
2. Validate required issuer fields:
   - issuer_id, jwk_set/signing material, status, created_by, audience policy ref, claim mapping policy ref.
3. Persist issuer trust metadata.
4. Emit issuer-registration audit event.

### BLM-4 Token Issuance
1. Validate caller path and scope.
2. Platform-principal issuance:
   - Allowed on trusted existing call paths.
3. Delegated issuance:
   - Allowed only if issuer is registered and policy-gated.
4. Build mandatory JWT claims.
5. Include optional delegated claims only when policy allows.
6. Emit token issuance audit event.

### BLM-5 External Identity Mapping and Binding
1. Validate delegated assertion signature and issuer trust.
2. Normalize delegated claims to canonical identity key using tenant mapping policy.
3. Evaluate existing binding.
4. If no collision, persist/confirm binding.
5. If collision, apply policy:
   - default reject_on_collision
   - optional deterministic_merge in enabled delegated or machine contexts
6. For remap operations, require explicit admin override.
7. Emit collision_resolution audit event for all collision paths.

### BLM-6 Authorization Failure Handling
1. On trust/auth/policy failure, fail closed.
2. Return typed domain error with stable HTTP mapping and safe message.
3. Emit authorization-failure audit event with correlation context.

## Policy and Decision Points
- Role policy: baseline platform roles are authoritative for soorma-core access.
- Delegated role extensions: namespaced claims; no implicit privilege mapping.
- Delegated claim acceptance: route/policy controlled.
- Collision policy: secure default reject, deterministic merge only when explicitly enabled.

## Event Emission Model
This unit emits full identity-domain event catalog now (aligned with Q10 = C):
- tenant_onboarded
- principal_created
- principal_updated
- principal_revoked
- delegated_issuer_registered
- delegated_issuer_updated
- token_issued
- token_revoked
- mapping_collision_detected
- mapping_collision_resolved
- authorization_denied

## Persistence Modeling Boundary
This model assumes domain entities plus repository contracts (Q8 = B), not schema-level implementation details.
