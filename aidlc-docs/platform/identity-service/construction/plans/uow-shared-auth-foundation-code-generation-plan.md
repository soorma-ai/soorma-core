# Code Generation Plan - uow-shared-auth-foundation

## Unit Context
- Unit: uow-shared-auth-foundation
- Purpose: Establish JWT-capable shared auth dependency foundation with deterministic fail-closed behavior.
- Primary stories: US-4.1 (primary), US-3.1 (shared claim contract foundation), US-3.2 (delegated claim gate foundation).
- Dependencies: Inception approved, unit design approved, construction design PR checkpoint approved.
- Downstream units enabled by this unit: uow-identity-core-domain, uow-sdk-jwt-integration, uow-cutover-hardening.

## Architecture Pattern Alignment (docs/ARCHITECTURE_PATTERNS.md)
- Section 1 Authentication and two-tier tenancy: preserve platform + service tenant/user split and fail-closed semantics.
- Section 2 Two-layer SDK architecture: no direct service-client exposure in handlers; this unit does not add new PlatformContext wrappers.
- Section 4 Multi-tenancy and RLS: keep tenancy context derivation compatible with existing service dependency boundaries.
- Section 6 Error handling: standardize 401 (authn) and 403 (authz/trust denial) behavior.
- Section 7 Testing: enforce STUB -> RED -> GREEN -> REFACTOR and coexistence regression coverage.

## Stories and Responsibilities
- US-4.1: Shared dependency JWT coexistence and authoritative JWT precedence.
- US-3.1 (partial): Mandatory claim-contract enforcement primitives in shared auth dependencies.
- US-3.2 (partial): Delegated context structural validation and trust-policy hook contract.

## Expected Interfaces and Contracts
- Shared auth context contract: normalized canonical auth context for consuming services.
- Trust-policy hook contract: route policy + canonical context -> trust decision.
- Service boundary contract: route-level authorization remains service-owned.
- Error contract: safe, deterministic status mapping and structured telemetry fields.

## Database Entities Owned by This Unit
- None. This unit does not introduce new persistent business entities.
- Existing PostgreSQL RLS session variable behavior remains integration-critical and must be preserved.

## Code Targets (Brownfield - modify in place)
- libs/soorma-service-common/src/soorma_service_common/dependencies.py
- libs/soorma-service-common/src/soorma_service_common/middleware.py
- libs/soorma-service-common/src/soorma_service_common/tenant_context.py
- libs/soorma-service-common/src/soorma_service_common/__init__.py
- services/memory/src/memory_service/core/dependencies.py
- services/tracker/src/tracker_service/core/dependencies.py
- services/event-service/src/api/dependencies.py
- services/registry/src/registry_service/api/dependencies.py
- libs/soorma-service-common/tests/test_dependencies.py
- libs/soorma-service-common/tests/test_middleware.py
- libs/soorma-service-common/tests/test_tenant_context.py
- services/memory/tests/test_api_validation.py
- services/tracker/tests/test_query_api.py
- services/event-service/tests/test_multi_tenancy.py

## Execution Checklist
- [x] Step 1 - Analyze unit context, approved artifacts, and story map.
- [x] Step 2 - Confirm architecture alignment and wrapper completeness expectations for this unit.
- [x] Step 3 - Identify exact brownfield file targets and test targets.
- [x] Step 4 - Define implementation slices and test strategy with STUB -> RED -> GREEN -> REFACTOR.
- [x] Step 5 - Generate this code generation plan artifact.
- [x] Step 6 - Record approval prompt in audit.md and request user approval for this plan.
- [ ] Step 7 - STUB phase: add/adjust shared auth contract scaffolding and placeholder logic where needed.
- [ ] Step 8 - RED phase: write/adjust tests for real expected JWT precedence, trust hook gating, and fail-closed behavior (failing for correct reasons).
- [ ] Step 9 - GREEN phase: implement JWT/header coexistence logic, canonical context normalization, and error semantics to satisfy tests.
- [ ] Step 10 - REFACTOR phase: clean up duplication, align imports/contracts, and verify architecture constraints remain intact.
- [ ] Step 11 - Execute focused test suites for shared library and affected services.
- [ ] Step 12 - Produce code-stage summary artifact at aidlc-docs/platform/identity-service/construction/uow-shared-auth-foundation/code/code-generation-summary.md.
- [ ] Step 13 - Present Code Generation completion gate (Request Changes / Continue to Next Stage).
- [ ] Step 14 - On approval, update aidlc-state.md and audit.md, then transition to next stage.

## Step 7-10 Detailed Scope
1. Shared auth contract layer:
- Add canonical auth context model and resolver flow in shared dependency path.
- Enforce JWT-authoritative precedence when JWT is present.
- Accept legacy headers when JWT is absent (coexistence behavior for this unit).
- Prohibit fallback to legacy headers if JWT is present but invalid.

2. Delegated context gate:
- Validate delegated tuple structure.
- Integrate trust-policy hook invocation contract.
- Emit trust outcome markers for service-level authorization use.

3. Error and telemetry behavior:
- Standardize 401/403 outcome mapping per design rules.
- Ensure structured logs include safe fields and omit token secrets.

4. Service dependency integration:
- Update consuming service dependency modules to use revised shared abstractions without route-level contract breakage.

5. Testing and regression:
- Unit tests for normalization, precedence, trust hook, and fail-closed paths.
- Targeted service regression tests to confirm no behavioral drift in required header validation and tenancy isolation behavior.

## Non-Applicable Items for This Unit
- Repository/data migration scripts: N/A (no schema ownership in this unit).
- Frontend components and UI tests: N/A.
- Deployment-manifest changes: N/A in code generation scope; covered in build/test instructions stage if needed.
