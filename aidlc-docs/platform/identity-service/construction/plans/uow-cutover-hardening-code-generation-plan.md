# Code Generation Plan - uow-cutover-hardening

## Unit Context
- Unit: uow-cutover-hardening
- Purpose: complete FR-11 phase 3 cutover by removing legacy tenant-header runtime dependence, enforcing JWT-only secured ingress behavior, converging active contracts on one canonical tenant identifier, finalizing RS256 and JWKS-only production trust paths, and closing the operational hardening gaps called out by the approved design.
- Primary stories:
  - US-4.3 Header Auth Removal Cutover (primary)
  - US-3.1 Platform Principal JWT Issuance (hardening continuation)
  - US-3.2 Delegated Context Claim Handling (finalization continuation)
- Dependencies:
  - Hard dependency: uow-shared-auth-foundation (approved/completed)
  - Hard dependency: uow-identity-core-domain (approved/completed)
  - Hard dependency: uow-sdk-jwt-integration (approved/completed)
  - Downstream stage: Build and Test for the initiative
- Test case traceability (QA construction enrichment + inception index):
  - TC-UCH-001 JWT-only ingress after release cutover
  - TC-UCH-002 Header-only request denied post-cutover
  - TC-UCH-003 Structured telemetry emitted for denied legacy access
  - TC-UCH-004 Trusted-caller self-issue succeeds with canonical tenant contract
  - TC-UCH-005 Issue-for-other without override authority is denied
  - TC-UCH-006 Legacy tenant alias payload is rejected
  - TC-UCH-007 Unknown kid or invalid signature is denied fail-closed
  - TC-UCH-008 Unallowlisted delegated issuer is denied before trust retrieval
  - TC-UCH-009 Unknown kid denial emits alert-ready centralized signal

## Architecture Pattern Alignment (docs/ARCHITECTURE_PATTERNS.md)
- Section 1 Authentication and two-tier tenancy:
  - secured service ingress must deny header-only requests after cutover and derive tenant and user context from bearer JWT claims only.
  - trusted-caller token issuance remains the only deliberate secured exception and must enforce caller/subject and tenant-bound authorization server-side.
- Section 2 Two-layer SDK architecture:
  - handler-facing access remains through `context.memory`, `context.tracker`, `context.bus`, and `context.identity` wrappers only.
  - any cutover transport changes stay inside low-level clients and wrapper internals; no direct service-client imports are introduced into agent code.
- Section 3 Event choreography:
  - event publishing and response semantics remain explicit; auth hardening must not alter `response_event` or correlation behavior.
- Section 4 Multi-tenancy and RLS:
  - canonical tenant identity must be server-derived and fail closed on mismatch, omission, or legacy alias drift.
  - persistence and service contracts must converge on one active tenant identifier with explicit migration handling.
- Section 5 State management:
  - token issuance, override authorization, and key-rotation state remain explicit and auditable.
- Section 6 Error handling:
  - denial paths remain typed, safe, deterministic, and non-leaking.
- Section 7 Testing:
  - STUB -> RED -> GREEN -> REFACTOR remains mandatory, with explicit negative security coverage for cutover regressions.

## Wrapper Completeness Verification (Section 2 Gate)
- Existing handler-facing wrappers remain the required surface:
  - `sdk/python/soorma/context.py`
  - `sdk/python/soorma/identity/wrapper.py`
- Unit 4 does not introduce new handler-visible service methods.
- Verification focus for this unit:
  - low-level clients stop depending on legacy tenant headers as the active auth path.
  - wrapper signatures remain stable while forwarding canonical bearer-auth behavior internally.
  - any identity-service caller-auth special cases stay isolated to `context.identity` and `soorma/identity/client.py` internals.

## Expected Interfaces and Contracts
- Shared auth contract:
  - bearer JWT is required for all secured non-public routes except the approved token-issuance trusted-caller path.
  - invalid JWT, unknown `kid`, unavailable trust source after cache expiry, and legacy alias mismatch all deny fail closed.
- Canonical tenant contract:
  - active runtime contracts use `tenant_id` as the canonical tenant identity.
  - `platform_tenant_id` and `tenant_domain_id` are removed from active request/response and internal decision paths or are left only behind an explicit bounded migration/deprecation seam that does not remain part of the active contract.
- Signing and verification contract:
  - RS256 with identity-service private-key custody is the normal production issuance path.
  - public-key verification uses JWKS/discovery or approved public-key distribution only.
  - HS256 is not a normal production or default local-dev cutover path.
- Delegated issuer contract:
  - delegated trust validation uses approved OIDC/JWKS-backed issuer validation within bounded scope.
  - unallowlisted issuers and policy-disallowed delegated claims are denied before deeper processing.
- Telemetry contract:
  - denied legacy/header-only access, override decisions, unknown `kid`, signature failures, and delegated-trust denials emit structured, token-safe telemetry.

## Database Entities and Migration Scope
- Existing identity-service persistence currently still uses `platform_tenant_identity_domains` and `tenant_domain_id`-based relationships.
- Unit 4 must execute one of the approved bounded persistence outcomes:
  - implement the schema/data migration needed to converge active contracts on canonical `tenant_id`, or
  - preserve storage compatibility temporarily but remove `tenant_domain_id` from active API/runtime contracts with an explicit, documented bounded deprecation seam and migration note.
- Any schema change must be explicit and migration-backed under `services/identity-service/alembic/versions/`.

## Brownfield Code Targets (Exact Paths)

### Shared Verification and Request Context (modify in place)
- libs/soorma-service-common/src/soorma_service_common/middleware.py
- libs/soorma-service-common/src/soorma_service_common/dependencies.py
- libs/soorma-service-common/src/soorma_service_common/tenant_context.py

### SDK Runtime and Low-Level Clients (modify in place)
- sdk/python/soorma/context.py
- sdk/python/soorma/memory/client.py
- sdk/python/soorma/tracker/client.py
- sdk/python/soorma/identity/client.py
- sdk/python/soorma/events.py
- sdk/python/soorma/cli/commands/dev.py

### Identity Service Runtime and Policy Surfaces (modify in place)
- services/identity-service/src/identity_service/core/config.py
- services/identity-service/src/identity_service/core/dependencies.py
- services/identity-service/src/identity_service/api/v1/tokens.py
- services/identity-service/src/identity_service/api/v1/delegated_issuers.py
- services/identity-service/src/identity_service/api/v1/discovery.py
- services/identity-service/src/identity_service/services/token_service.py
- services/identity-service/src/identity_service/services/provider_facade.py
- services/identity-service/src/identity_service/services/delegated_trust_service.py
- services/identity-service/src/identity_service/models/domain.py
- services/identity-service/src/identity_service/crud/tenant_domains.py
- services/identity-service/src/identity_service/crud/principals.py
- services/identity-service/alembic/versions/0001_identity_core_init.py
- services/identity-service/alembic/versions/ (new migration only if required)

### Tests (modify/add)
- libs/soorma-service-common/tests/test_middleware.py
- libs/soorma-service-common/tests/test_dependencies.py
- libs/soorma-service-common/tests/test_tenant_context.py
- sdk/python/tests/test_memory_client.py
- sdk/python/tests/test_tracker_service_client.py
- sdk/python/tests/test_context_wrappers.py
- sdk/python/tests/test_context_identity_wrapper.py
- sdk/python/tests/cli/test_dev.py
- services/identity-service/tests/test_token_api.py
- services/identity-service/tests/test_provider_facade.py
- services/identity-service/tests/test_delegated_issuer_api.py
- services/identity-service/tests/test_discovery_api.py
- services/identity-service/tests/test_onboarding_api.py

### Documentation and Changelog Targets
- services/identity-service/README.md
- services/identity-service/CHANGELOG.md
- sdk/python/CHANGELOG.md
- docs/identity_service/README.md
- docs/identity_service/JWT_TECHNICAL_ARCHITECTURE.md
- docs/identity_service/ASYMMETRIC_BOOTSTRAP_PRIMER.md

### Unit Documentation Output (Construction)
- aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/code/code-generation-summary.md

## Execution Checklist (Single Source of Truth)
- [x] Step 1 - Analyze approved unit design artifacts, migration checklist, story map, test-case traceability, and dependency readiness.
- [x] Step 2 - Validate architecture alignment (Sections 1-7) and wrapper completeness constraints.
- [x] Step 3 - Confirm brownfield target paths and ownership boundaries (application code vs initiative documentation).
- [x] Step 4 - Define implementation slices with STUB -> RED -> GREEN -> REFACTOR and explicit negative security coverage.
- [x] Step 5 - Create this code-generation plan artifact for Unit 4.
- [x] Step 6 - Log code-generation approval prompt in audit.md and request explicit plan approval.
- [x] Step 7 - Wait for explicit user approval of this plan before executing Part 2.
- [x] Step 8 - STUB phase (complete when 8A, 8B, 8C, and 8D are checked).
- [x] Step 8A - STUB (shared auth): introduce/adjust seams for JWT-only enforcement, canonical tenant extraction, and legacy denial reason codes.
- [x] Step 8B - STUB (SDK): prepare memory/tracker/event/identity client seams for JWT-only active behavior and header-path removal where required.
- [x] Step 8C - STUB (identity-service): prepare issuance authorization, delegated-trust finalization, and canonical tenant-contract migration seams.
- [x] Step 8D - STUB (docs/migration): prepare migration/doc update surfaces and summary artifact skeleton.
- [x] Step 9 - RED phase (complete when 9A, 9B, 9C, and 9D are checked).
- [x] Step 9A - RED (shared auth): failing tests for header-only denial, unknown `kid` deny, cache-expiry fail-closed behavior, and canonical tenant extraction.
- [x] Step 9B - RED (SDK): failing tests showing legacy header dependence is removed from active request behavior and JWT-only auth is projected correctly.
- [x] Step 9C - RED (identity-service): failing tests for self-issue-only baseline, override denial without authority, cross-tenant denial, delegated issuer allowlist/OIDC enforcement, and RS256-only production path.
- [x] Step 9D - RED (migration/docs): failing assertions or checks for canonical tenant naming, bootstrap defaults, and documented rollback/cutover expectations.
- [x] Step 10 - GREEN phase (complete when 10A, 10B, 10C, and 10D are checked).
- [x] Step 10A - GREEN (shared auth): implement JWT-only secured ingress behavior, typed deny reasons, and canonical tenant/user resolution.
- [x] Step 10B - GREEN (SDK): implement JWT-only active service-client behavior and align local bootstrap defaults with the approved hard-cutover contract.
- [x] Step 10C - GREEN (identity-service): implement caller-auth hardening, canonical tenant convergence, delegated OIDC/JWKS validation finalization, and RS256/JWKS-only production trust path.
- [x] Step 10D - GREEN (migration/docs): implement any required schema/data migration and update code-stage summary/docs/changelogs.
- [x] Step 11 - REFACTOR phase (complete when 11A, 11B, 11C, and 11D are checked).
- [x] Step 11A - REFACTOR (shared auth): simplify middleware/dependency precedence and preserve fail-closed guarantees.
- [x] Step 11B - REFACTOR (SDK): remove redundant compatibility code and tighten auth-token propagation boundaries.
- [x] Step 11C - REFACTOR (identity-service): simplify issuance and delegated-trust decision paths without weakening policy enforcement.
- [x] Step 11D - REFACTOR (migration/docs): remove stale terminology, dead compatibility notes, and redundant config guidance.
- [x] Step 12 - Execute focused test suites (complete when 12A, 12B, 12C, and 12D are checked).
- [x] Step 12A - Tests (shared auth): middleware, dependencies, and tenant-context suites.
- [x] Step 12B - Tests (SDK): memory/tracker/context/CLI suites for outbound auth behavior.
- [x] Step 12C - Tests (identity-service): token, delegated issuer, discovery, provider facade, and onboarding suites.
- [x] Step 12D - Tests (cross-cutover checks): explicit negative security cases and any migration verification added for this unit.
- [x] Step 13 - Produce code-stage summary artifact at aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/code/code-generation-summary.md.
- [x] Step 14 - Present Code Generation completion gate (Request Changes / Continue to Next Stage).
- [ ] Step 15 - On approval, update aidlc-state.md and audit.md, then transition to Build and Test.

## Detailed Generation Sequence
1. Shared auth cutover:
   - remove active legacy header fallback for secured non-public routes.
   - enforce canonical JWT-derived tenant and user context with fail-closed mismatch handling.
   - emit structured denial telemetry for header-only and verification-failure paths.
2. Identity-service hardening:
   - keep token issuance as the only trusted-caller secured exception.
   - enforce self-issue baseline and explicit admin-override authorization checks.
   - finalize delegated issuer OIDC/JWKS validation within approved scope.
   - eliminate HS256 as the normal production path.
3. SDK/runtime alignment:
   - update low-level clients and wrappers so active runtime behavior no longer depends on tenant headers for the cutover paths in scope.
   - keep wrapper signatures stable.
   - align `soorma dev` defaults and generated environment with RS256/JWKS hard-cutover expectations.
4. Canonical tenant naming and migration:
   - converge active code/docs/contracts on canonical `tenant_id` naming.
   - implement or document bounded persistence migration/deprecation behavior explicitly.
5. Focused regression and negative security coverage:
   - header-only denial
   - override denial without authority
   - cross-tenant and cross-principal issuance denial
   - invalid signature and unknown `kid` denial
   - delegated issuer allowlist/trust-source denial
6. Documentation and summary:
   - update operational docs, changelogs, and the Unit 4 construction code summary.

## Non-Applicable Items in This Unit
- Frontend components and UI tests: N/A.
- New standalone service creation: N/A (brownfield in-place hardening and migration only).
- New handler-facing wrapper surface area: N/A unless implementation reveals an unavoidable gap, in which case wrapper completeness must be re-verified before execution proceeds.