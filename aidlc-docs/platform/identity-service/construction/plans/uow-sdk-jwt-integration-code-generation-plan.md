# Code Generation Plan - uow-sdk-jwt-integration

## Unit Context
- Unit: uow-sdk-jwt-integration
- Purpose: Implement JWT-first SDK and wrapper integration, compatibility-phase asymmetric signing/JWKS verification behavior, canonical tenant propagation, and deterministic local bootstrap behavior.
- Primary stories:
  - US-4.2 SDK JWT Client Upgrade (primary)
  - US-3.1 Platform Principal JWT Issuance (integration continuation)
  - US-3.2 Delegated Context Claim Handling (integration continuation)
- Dependencies:
  - Hard dependency: uow-shared-auth-foundation (approved/completed)
  - Hard dependency: uow-identity-core-domain (approved/completed)
  - Downstream dependent: uow-cutover-hardening
- Test case traceability (QA construction enrichment):
  - TC-USJI-001 wrapper signature compatibility with internal JWT injection
  - TC-USJI-002 canonical JWT outbound request
  - TC-USJI-003 invalid JWT denied fail-closed with typed safe error
  - TC-USJI-004 JWT + matching alias success
  - TC-USJI-005 JWT + mismatching alias deny
  - TC-USJI-006 unknown kid/invalid signature deny
  - TC-USJI-007 deterministic bootstrap outcomes and protected-drift fail-closed

## Architecture Pattern Alignment (docs/ARCHITECTURE_PATTERNS.md)
- Section 1 Authentication and two-tier tenancy:
  - Preserve platform tenant boundary while propagating service tenant/user via canonical JWT-derived identity context for this unit's compatibility paths.
- Section 2 Two-layer SDK architecture:
  - Agent handlers remain wrapper-only; no direct low-level service-client imports in handler code.
  - Wrapper surface stays stable while transport/auth behavior evolves internally.
- Section 3 Event choreography:
  - Any event-assisted bootstrap/audit behavior retains explicit event semantics and correlation propagation.
- Section 4 Multi-tenancy and RLS:
  - Service-side verification and policy checks remain server-enforced with fail-closed tenant-bound behavior.
- Section 5 State management:
  - Bootstrap and issuance state transitions remain explicit and machine-auditable.
- Section 6 Error handling:
  - Typed, safe error envelopes for auth failures and mismatch denials.
- Section 7 Testing:
  - Enforce STUB -> RED -> GREEN -> REFACTOR with focused integration and negative security coverage.

## Wrapper Completeness Verification (Section 2 Gate)
- Existing `context.identity` wrapper methods introduced in Unit 2 remain the only handler-facing identity API surface.
- Unit 3 does not introduce handler-facing direct-service imports.
- Any additional JWT transport/auth behavior is implemented under wrapper/client internals only.
- Verification targets:
  - `sdk/python/soorma/context.py`
  - `sdk/python/soorma/identity/wrapper.py`
  - `sdk/python/tests/test_context_identity_wrapper.py`
  - `sdk/python/tests/test_context_wrappers.py`

## Expected Interfaces and Contracts
- SDK contracts:
  - Wrapper method signatures unchanged.
  - JWT-first auth path enabled internally for identity interactions.
  - Canonical tenant semantics aligned to JWT `tenant_id` with bounded compatibility alias handling.
- Identity-service contracts:
  - Compatibility-phase issuance caller-auth and subject-authorization policy enforced.
  - Asymmetric signer metadata (`alg`, `kid`) and verifier-distribution path (JWKS + bounded fallback) enforced.
- Security contracts:
  - Fail-closed on invalid JWT, unknown `kid`, signature failure, and tenant mismatch.
  - Typed safe errors and structured audit/telemetry for deny/override decisions.

## Database Entities Owned by This Unit
- No new primary domain entities are introduced by this unit.
- Existing identity-service persistence may be updated for key/discovery metadata and issuance-policy state if required by implementation.
- Any schema changes must be explicit and migration-backed.

## Brownfield Code Targets (Exact Paths)

### SDK Runtime and Wrappers (modify in place)
- sdk/python/soorma/context.py
- sdk/python/soorma/identity/client.py
- sdk/python/soorma/identity/wrapper.py
- sdk/python/soorma/identity/__init__.py
- sdk/python/soorma/events.py
- sdk/python/soorma/cli/commands/dev.py

### Identity Service Integration Surfaces (modify in place)
- services/identity-service/src/identity_service/services/provider_facade.py
- services/identity-service/src/identity_service/services/token_service.py
- services/identity-service/src/identity_service/api/v1/tokens.py
- services/identity-service/src/identity_service/main.py
- services/identity-service/src/identity_service/core/config.py

### Shared Verification Dependency (modify in place as needed)
- libs/soorma-service-common/src/soorma_service_common/middleware.py
- libs/soorma-service-common/src/soorma_service_common/dependencies.py
- libs/soorma-service-common/src/soorma_service_common/tenant_context.py

### Tests (modify/add)
- sdk/python/tests/test_identity_service_client.py
- sdk/python/tests/test_context_identity_wrapper.py
- sdk/python/tests/test_context_wrappers.py
- sdk/python/tests/cli/test_dev.py
- services/identity-service/tests/test_provider_facade.py
- services/identity-service/tests/test_token_api.py
- libs/soorma-service-common/tests/test_middleware.py
- libs/soorma-service-common/tests/test_dependencies.py

### Documentation and Changelog Targets
- services/identity-service/README.md
- services/identity-service/CHANGELOG.md
- sdk/python/README.md

### Unit Documentation Output (Construction)
- aidlc-docs/platform/identity-service/construction/uow-sdk-jwt-integration/code/code-generation-summary.md

## Execution Checklist (Single Source of Truth)
- [x] Step 1 - Analyze unit design artifacts, story map, dependencies, migration checklist, and readiness for code generation.
- [x] Step 2 - Validate architecture alignment (Sections 1-7) and wrapper completeness constraints.
- [x] Step 3 - Confirm brownfield target paths and ownership boundaries (application code vs initiative documentation).
- [x] Step 4 - Define implementation slices with STUB -> RED -> GREEN -> REFACTOR strategy and negative security coverage.
- [x] Step 5 - Create this code-generation plan artifact for Unit 3.
- [x] Step 6 - Log code-generation approval prompt in audit.md and request explicit plan approval.
- [x] Step 7 - Wait for explicit user approval of this plan before executing Part 2.
- [x] Step 8 - STUB phase (complete when 8A, 8B, and 8C are checked).
- [x] Step 8A - STUB (SDK): placeholders for JWT transport hooks and wrapper-internal integration seams.
- [x] Step 8B - STUB (identity-service): placeholders for issuance policy checks, verifier selection, and deny-path contracts.
- [x] Step 8C - STUB (shared dependency): placeholders for canonical tenant/user extraction and fail-closed dependency contracts.
- [x] Step 9 - RED phase (complete when 9A, 9B, and 9C are checked).
- [x] Step 9A - RED (SDK): failing tests for canonical JWT outbound behavior and wrapper compatibility.
- [x] Step 9B - RED (identity-service): failing tests for mismatch deny, unknown kid/signature deny, and issuance-policy protections.
- [x] Step 9C - RED (shared dependency): failing tests for middleware/dependency canonical claim handling and fail-closed paths.
- [x] Step 10 - GREEN phase (complete when 10A, 10B, and 10C are checked).
- [x] Step 10A - GREEN (SDK): implement internal JWT-first behavior while keeping public wrapper signatures stable.
- [x] Step 10B - GREEN (identity-service): implement compatibility-phase auth/authorization and verifier-distribution behavior.
- [x] Step 10C - GREEN (shared dependency): implement deterministic claim verification and safe error mapping support.
- [x] Step 11 - REFACTOR phase (complete when 11A, 11B, and 11C are checked).
- [x] Step 11A - REFACTOR (SDK): remove duplication and tighten internal auth transport contract boundaries.
- [x] Step 11B - REFACTOR (identity-service): align error taxonomy and simplify policy decision paths without changing behavior.
- [x] Step 11C - REFACTOR (shared dependency): tighten middleware/dependency contracts and preserve deterministic precedence behavior.
- [x] Step 12 - Execute focused test suites (complete when 12A, 12B, and 12C are checked).
- [x] Step 12A - Tests (SDK): wrappers/clients and CLI bootstrap behavior.
- [x] Step 12B - Tests (identity-service): issuance, verifier-selection, and deny-path coverage.
- [x] Step 12C - Tests (shared dependency): middleware and dependency validation coverage.
- [x] Step 13 - Produce code-stage summary artifact at aidlc-docs/platform/identity-service/construction/uow-sdk-jwt-integration/code/code-generation-summary.md.
- [ ] Step 14 - Present Code Generation completion gate (Request Changes / Continue to Next Stage).
- [ ] Step 15 - On approval, update aidlc-state.md and audit.md, then transition to next stage.

## Detailed Generation Sequence
1. Business logic generation (identity-service + SDK internals):
   - Implement compatibility-phase caller-auth and subject-authorization checks.
   - Implement asymmetric issuance metadata and verifier-distribution selection behavior.
   - Implement deterministic alias mismatch and fail-closed deny behavior.
2. SDK/wrapper integration:
   - Keep wrapper signatures stable.
   - Inject JWT behavior internally and preserve context ergonomics.
3. Shared dependency alignment:
   - Ensure service-side verification path honors deterministic precedence and safe error mapping.
4. CLI bootstrap flow:
   - Implement deterministic outcome contract (`CREATED`, `REUSED`, `FAILED_DRIFT`) and protected-drift fail-closed behavior.
5. Tests and regressions:
   - Cover happy-path and mandatory negative security matrix scenarios from enriched Unit 3 test specs.
6. Documentation/changelog updates:
   - Record compatibility-phase behavior, constraints, and migration notes.

## Non-Applicable Items in This Unit
- Frontend components and UI tests: N/A.
- New standalone service creation: N/A (brownfield in-place modifications only).
