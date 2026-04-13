# Code Generation Plan - uow-identity-core-domain

## Unit Context
- Unit: uow-identity-core-domain
- Purpose: Implement core identity domain capabilities for onboarding, principal lifecycle, token issuance, delegated issuer trust, and mapping/collision governance.
- Primary stories:
  - US-1.1 Tenant Onboarding Bootstrap
  - US-1.2 Principal Lifecycle Management
  - US-2.1 Delegated Issuer Registration
  - US-2.2 External Principal Mapping Policy
  - US-3.1 Platform Principal JWT Issuance (shared with uow-shared-auth-foundation)
  - US-3.2 Delegated Context Claim Handling (shared with uow-shared-auth-foundation)
- Dependencies:
  - Hard dependency: uow-shared-auth-foundation (completed)
  - Downstream dependents: uow-sdk-jwt-integration, uow-cutover-hardening
- Test case traceability (inception QA extension):
  - TC-UICD-001 onboarding creates identity domain
  - TC-UICD-002 token issuance returns mandatory claims
  - TC-UICD-003 unregistered delegated issuer denied

## Architecture Pattern Alignment (docs/ARCHITECTURE_PATTERNS.md)
- Section 1 Authentication and two-tier tenancy:
  - Preserve platform tenant as root trust boundary while handling delegated service-tenant/service-user claims via policy-gated flows.
- Section 2 Two-layer SDK architecture:
  - Agent handlers remain wrapper-only. No direct service-client imports in handler code.
  - Wrapper completeness is verified as part of this plan before implementation starts.
- Section 3 Event choreography:
  - Any event-assisted audit/telemetry follows explicit event payload/correlation conventions.
- Section 4 Multi-tenancy and RLS:
  - Identity-domain persistence is tenant-isolated with server-side enforcement.
- Section 5 State management:
  - Principal lifecycle and trust state transitions are explicit and auditable.
- Section 6 Error handling:
  - Typed domain errors with stable HTTP mapping and safe envelopes.
- Section 7 Testing:
  - Execute STUB -> RED -> GREEN -> REFACTOR with unit/integration/negative security coverage.

## Wrapper Completeness Verification (Section 2 Gate)
- Service methods introduced in this unit must have corresponding PlatformContext-level wrapper contracts before implementation completes.
- Planned wrapper contract targets in this unit (surface only; transport/auth hardening remains in uow-sdk-jwt-integration):
  - `context.identity.onboard_tenant(...)`
  - `context.identity.create_principal(...)`
  - `context.identity.update_principal(...)`
  - `context.identity.revoke_principal(...)`
  - `context.identity.issue_token(...)`
  - `context.identity.register_delegated_issuer(...)`
  - `context.identity.update_delegated_issuer(...)`

## Expected Interfaces and Contracts
- API contract groups:
  - onboarding
  - principal lifecycle
  - token issuance
  - delegated issuer trust
  - external mapping/collision resolution
- Security contracts:
  - fail-closed trust and authorization decisions
  - typed error catalog with deterministic status mapping
  - structured audit/telemetry emission

## Database Entities Owned by This Unit
- PlatformTenantIdentityDomain
- Principal
- RoleAssignment
- DelegatedIssuer
- ClaimMappingPolicy
- ExternalIdentityBinding
- TokenIssuanceRecord
- IdentityAuditEvent

## Brownfield Code Targets (Exact Paths)

### New Identity Service (Application Code)
- services/identity-service/pyproject.toml
- services/identity-service/README.md
- services/identity-service/CHANGELOG.md
- services/identity-service/Dockerfile
- services/identity-service/alembic.ini
- services/identity-service/entrypoint.sh
- services/identity-service/alembic/env.py
- services/identity-service/alembic/versions/0001_identity_core_init.py
- services/identity-service/src/identity_service/__init__.py
- services/identity-service/src/identity_service/main.py
- services/identity-service/src/identity_service/core/__init__.py
- services/identity-service/src/identity_service/core/config.py
- services/identity-service/src/identity_service/core/db.py
- services/identity-service/src/identity_service/core/dependencies.py
- services/identity-service/src/identity_service/api/__init__.py
- services/identity-service/src/identity_service/api/v1/__init__.py
- services/identity-service/src/identity_service/api/v1/onboarding.py
- services/identity-service/src/identity_service/api/v1/principals.py
- services/identity-service/src/identity_service/api/v1/tokens.py
- services/identity-service/src/identity_service/api/v1/delegated_issuers.py
- services/identity-service/src/identity_service/api/v1/mappings.py
- services/identity-service/src/identity_service/models/__init__.py
- services/identity-service/src/identity_service/models/domain.py
- services/identity-service/src/identity_service/models/dto.py
- services/identity-service/src/identity_service/crud/__init__.py
- services/identity-service/src/identity_service/crud/tenant_domains.py
- services/identity-service/src/identity_service/crud/principals.py
- services/identity-service/src/identity_service/crud/delegated_issuers.py
- services/identity-service/src/identity_service/crud/mappings.py
- services/identity-service/src/identity_service/crud/token_records.py
- services/identity-service/src/identity_service/services/__init__.py
- services/identity-service/src/identity_service/services/onboarding_service.py
- services/identity-service/src/identity_service/services/principal_service.py
- services/identity-service/src/identity_service/services/token_service.py
- services/identity-service/src/identity_service/services/delegated_trust_service.py
- services/identity-service/src/identity_service/services/mapping_service.py
- services/identity-service/src/identity_service/services/audit_service.py
- services/identity-service/src/identity_service/services/provider_facade.py
- services/identity-service/tests/conftest.py
- services/identity-service/tests/test_onboarding_api.py
- services/identity-service/tests/test_principal_lifecycle_api.py
- services/identity-service/tests/test_token_api.py
- services/identity-service/tests/test_delegated_issuer_api.py
- services/identity-service/tests/test_mapping_policy_api.py

### Shared Models and Common Contracts
- libs/soorma-common/src/soorma_common/models.py
- libs/soorma-common/src/soorma_common/tenancy.py

### SDK Wrapper Completeness (No handler direct clients)
- sdk/python/soorma/context.py
- sdk/python/soorma/__init__.py
- sdk/python/soorma/identity/__init__.py
- sdk/python/soorma/identity/client.py
- sdk/python/tests/test_context_wrappers.py
- sdk/python/tests/test_identity_service_client.py

### Local Dev Stack and Service Catalog Integration
- sdk/python/soorma/cli/commands/dev.py
- sdk/python/tests/cli/test_dev.py
- services/README.md

### Unit Documentation Output (Construction)
- aidlc-docs/platform/identity-service/construction/uow-identity-core-domain/code/code-generation-summary.md

## Execution Checklist (Single Source of Truth)
- [x] Step 1 - Analyze unit design artifacts, story map, dependencies, and readiness for code generation.
- [x] Step 2 - Validate architecture alignment (Sections 1-7) and wrapper completeness gate expectations.
- [x] Step 3 - Confirm brownfield target paths and ownership boundaries (application code vs documentation).
- [x] Step 4 - Define explicit generation sequence with STUB -> RED -> GREEN -> REFACTOR testing strategy.
- [x] Step 5 - Create this plan file as the single source of truth for Code Generation execution.
- [x] Step 6 - Log approval prompt in audit.md and request explicit user approval before Part 2 execution.
- [x] Step 7 - STUB phase: scaffold identity-service package, API modules, models, services, and wrapper contracts with placeholder behavior.
- [x] Step 8 - RED phase: add/adjust tests for onboarding, issuance claim contract, delegated trust deny paths, and wrapper surface contracts (failing for correct reasons).
- [x] Step 9 - GREEN phase: implement onboarding, lifecycle, issuance, delegated trust, mapping/collision logic, and wrapper delegation to satisfy tests.
- [x] Step 10 - REFACTOR phase: remove duplication, align imports/contracts, harden typed error mapping, and preserve architecture constraints.
- [x] Step 11 - Integrate local dev stack metadata for identity-service (service definitions, compose generation, and CLI tests).
- [x] Step 12 - Run focused test suites for new service, shared models, SDK wrapper contracts, and negative security paths.
- [x] Step 13 - Produce code-stage summary artifact at aidlc-docs/platform/identity-service/construction/uow-identity-core-domain/code/code-generation-summary.md.
- [x] Step 14 - Present Code Generation completion gate (Request Changes / Continue to Next Stage).
- [x] Step 15 - On approval, update aidlc-state.md and audit.md, then transition to next stage.

## Detailed Generation Sequence
1. Project structure setup (brownfield add):
  - Add new `services/identity-service` package aligned to existing service conventions.
2. Business logic generation:
  - Implement onboarding, principal lifecycle, delegated trust, mapping, issuance, and audit domain services.
3. Business logic unit testing:
  - Domain-service tests for invariants, fail-closed paths, and typed error contracts.
4. API layer generation:
  - Add v1 endpoints for onboarding, principals, tokens, delegated issuers, and mappings.
5. API layer unit/integration testing:
  - Validate request/response contracts and denial behavior for trust failures.
6. Repository layer generation:
  - CRUD and database session integration for identity entities.
7. Repository testing:
  - Persistence and transition coverage, including collision and issuer-state scenarios.
8. Database migration scripts:
  - Add initial schema migration for identity-core domain entities.
9. SDK wrapper contract generation:
  - Add wrapper surface contracts aligned to two-layer architecture and no handler-level direct clients.
10. Documentation and deployment artifacts:
  - Update service catalog and dev stack integration metadata.

## Non-Applicable Items in This Unit
- Frontend components and UI tests: N/A.
- Full SDK JWT transport cutover behavior: deferred to uow-sdk-jwt-integration.
