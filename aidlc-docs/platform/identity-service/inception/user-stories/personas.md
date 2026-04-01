# Personas - Identity Service Initiative

## Persona 1: Platform Administrator
- **Role**: Owns tenant-level identity governance for a platform tenant.
- **Primary Goals**:
  - Onboard platform tenant identity domain.
  - Bootstrap and manage developer users and machine principals.
  - Configure delegated issuer trust and tenant-level token policy.
- **Key Responsibilities**:
  - Assign roles (`admin`, `developer`) and machine principal roles (`planner`, `worker`, `tool`).
  - Define token TTL/scope policy defaults and revocation actions.
  - Approve delegated issuer keys/metadata and lifecycle updates.
- **Pain Points**:
  - Misconfigured trust metadata can over-authorize delegated flows.
  - Lack of clear audit trail can delay incident response.
- **Success Signals**:
  - Tenant onboarding and trust configuration complete without manual patching.
  - Access decisions are explainable and auditable.

## Persona 2: Platform Developer
- **Role**: Builds and integrates services/SDK usage relying on identity contracts.
- **Primary Goals**:
  - Consume stable auth interfaces with minimal handler/service churn.
  - Progress incremental rollout from header-based auth to JWT.
- **Key Responsibilities**:
  - Use `PlatformContext` wrappers and existing dependency injection contracts.
  - Adopt JWT client updates in SDK while keeping phased compatibility.
- **Pain Points**:
  - Breaking DI/router contract changes increase migration risk.
  - Inconsistent claim semantics across services cause integration defects.
- **Success Signals**:
  - Existing service handlers remain stable during phase 1 and 2 rollout.
  - JWT-enabled paths pass integration tests without broad refactors.

## Persona 3: Machine Principal Operator
- **Role**: Operates trusted planner/worker/tool machine identities for automation.
- **Primary Goals**:
  - Provision and rotate machine credentials safely.
  - Ensure agents can call soorma-core ingress with correct claims.
- **Key Responsibilities**:
  - Register machine principals and manage lifecycle/revocation.
  - Use delegated service context only when policy permits.
- **Pain Points**:
  - Hard-to-debug auth failures under mixed claim contexts.
  - Overly broad scopes increase blast radius.
- **Success Signals**:
  - Machine tokens are least-privilege and auditable.
  - Automation remains reliable across auth rollout phases.

## Persona 4: Delegated Issuer Administrator
- **Role**: Manages trusted external issuer configuration per platform tenant.
- **Primary Goals**:
  - Register and maintain issuer keys/metadata for delegated JWT validation.
  - Enforce strict trust boundaries for service-tenant/service-user assertions.
- **Key Responsibilities**:
  - Maintain issuer allowlists in v1 and prepare OIDC/JWKS adoption in v2.
  - Validate mapping and namespace policy behavior per tenant.
- **Pain Points**:
  - Key rotation coordination across external identity systems.
  - Incorrect mapping rules leading to identity collisions.
- **Success Signals**:
  - Delegated tokens validate only under approved trust policies.
  - Namespace/canonical mapping remains stable and non-ambiguous.

## Persona-to-Story Mapping Summary
- **Platform Administrator**: Epic 1, Epic 2, Epic 3, Epic 4.
- **Platform Developer**: Epic 3, Epic 4.
- **Machine Principal Operator**: Epic 1, Epic 2, Epic 4.
- **Delegated Issuer Administrator**: Epic 2, Epic 4.