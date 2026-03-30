# Unit-2 Code Generation Plan

## Stage Context
- Initiative: Memory Service Identity-Scope Consistency Fix
- Unit: unit-2 (Memory Runtime Alignment)
- Project Type: Brownfield
- Workspace Root: . (soorma-core repo root)
- Code Location Rule: application code in repo root; documentation in aidlc-docs only

## Architecture Pattern Alignment (docs/ARCHITECTURE_PATTERNS.md)
- Section 1 (Authentication and Authorization): enforce full identity tuple handling and fail-closed behavior for user-scoped paths.
- Section 2 (SDK Two-Layer): N/A for this unit because changes are backend service internals only (no SDK wrapper method additions).
- Section 3 (Event Choreography): N/A for this unit because no event envelope choreography changes are planned.
- Section 4 (Multi-Tenancy): maintain platform-tenant isolation plus application-layer service tenant and service user predicates.
- Section 5 (State Management): preserve task and plan context state semantics while tightening identity-scoped access.
- Section 6 (Error Handling): keep generic validation failures and fail-closed defaults.
- Section 7 (Testing): add behavior-focused tests for route validation, service propagation, and CRUD predicate consistency.

## Unit Context and Traceability
- Unit responsibilities source: inception/application-design/unit-of-work.md (U2)
- Requirement mapping source: inception/application-design/unit-of-work-story-map.md
- Unit dependencies source: inception/application-design/unit-of-work-dependency.md
- Upstream dependency: U1 shared dependency (`require_user_context`) already complete and approved.
- Downstream dependency: U3 will align schema and migration details to finalized runtime behavior from this unit.
- FR/NFR coverage in this unit:
  - FR-3, FR-4, FR-5, FR-6, FR-7, FR-9, FR-10
  - NFR-1, NFR-2, NFR-4, NFR-6

## Planned Code Targets (Brownfield Modifications)
- API layer:
  - services/memory/src/memory_service/api/v1/semantic.py
  - services/memory/src/memory_service/api/v1/episodic.py
  - services/memory/src/memory_service/api/v1/procedural.py
  - services/memory/src/memory_service/api/v1/working.py
  - services/memory/src/memory_service/api/v1/plans.py
  - services/memory/src/memory_service/api/v1/sessions.py
  - services/memory/src/memory_service/api/v1/task_context.py
  - services/memory/src/memory_service/api/v1/plan_context.py
  - services/memory/src/memory_service/api/v1/admin.py (admin guard boundary only)
- Shared/route dependency integration points:
  - services/memory/src/memory_service/core/dependencies.py
- Service layer:
  - services/memory/src/memory_service/services/plan_service.py
  - services/memory/src/memory_service/services/session_service.py
  - services/memory/src/memory_service/services/task_context_service.py
  - services/memory/src/memory_service/services/plan_context_service.py
- CRUD layer:
  - services/memory/src/memory_service/crud/plans.py
  - services/memory/src/memory_service/crud/sessions.py
  - services/memory/src/memory_service/crud/task_context.py
  - services/memory/src/memory_service/crud/plan_context.py
  - services/memory/src/memory_service/crud/semantic.py
- Tests:
  - services/memory/tests/test_api_validation.py
  - services/memory/tests/test_multi_tenancy.py
  - services/memory/tests/test_task_context.py
  - services/memory/tests/test_plan_context.py
  - services/memory/tests/test_semantic_upsert_privacy.py
  - services/memory/tests/test_semantic_upsert_privacy_simple.py

## Part 1 - Planning Checklist
- [x] Step 1: Analyze unit context and load unit-2 design artifacts.
- [x] Step 2: Read workspace root/project type and identify exact brownfield modification targets.
- [x] Step 3: Confirm unit dependencies, interfaces, and requirement traceability.
- [x] Step 4: Create and save this code generation plan as the single source of truth.
- [x] Step 5: Prepare concise execution summary for user review.
- [x] Step 6: Log approval prompt in audit.md.
- [x] Step 7: Wait for explicit user approval before any code generation execution.
- [x] Step 8: Record user approval response in audit.md.
- [x] Step 9: Update aidlc-state.md to reflect transition from planning to generation.

## Part 2 - Generation Steps (Execute Only After Approval)
- [x] Step 10: STUB phase - route dependency wiring seams.
  - Add explicit user-context dependency application on all user-scoped routers.
  - Keep admin router exempt from user-context dependency.
- [x] Step 11: STUB phase - admin authorization guard seam.
  - Introduce or wire explicit server-side admin authorization dependency for admin routes.
- [x] Step 12: RED phase - API-layer tests.
  - Add failing tests for missing user context on user-scoped endpoints.
  - Add failing tests confirming admin endpoints use explicit admin authorization checks.
- [x] Step 13: GREEN phase - API implementation.
  - Apply `require_user_context` consistently to user-scoped routes.
  - Enforce explicit admin guard for admin endpoints.
- [x] Step 14: STUB/RED/GREEN - service signature propagation.
  - Update service methods to require and propagate `service_tenant_id` and `service_user_id` where missing.
  - Add/adjust tests to fail before implementation and pass after implementation.
- [x] Step 15: STUB/RED/GREEN - CRUD predicate alignment.
  - Update list/get/update/delete predicates for plans and sessions to full identity tuple.
  - Update task_context and plan_context get/update/delete/upsert conflict target runtime behavior to full identity tuple.
  - Update semantic private conflict targets to include `service_tenant_id` where required.
- [x] Step 16: REFACTOR phase.
  - Remove duplication, keep helper boundaries small and framework-agnostic.
  - Keep behavior unchanged outside approved unit-2 scope.
- [x] Step 17: Verification test run.
  - Run focused memory test set for route validation and CRUD predicate behavior.
  - Confirm failures are addressed and no regressions introduced in touched areas.
- [x] Step 18: Documentation summary generation.
  - Create code summary at aidlc-docs/platform/memory-identity-scope/construction/unit-2/code/code-generation-summary.md.
- [x] Step 19: Progress tracking updates.
  - Mark completed generation steps [x] in this plan.
  - Update aidlc-state.md and append execution entries to audit.md.

## Security Baseline Compliance (Planning Stage)
- SECURITY-03: Compliant by intent (structured logging constraints captured in plan).
- SECURITY-05: Compliant by intent (input/identity validation wiring included in generation steps).
- SECURITY-08: Compliant by intent (admin authorization and object-level scope checks planned).
- SECURITY-15: Compliant by intent (fail-closed behavior included as explicit implementation target).
- Remaining SECURITY rules: N/A at planning stage (no infrastructure/deployment artifacts generated in this step).

## Notes
- This plan follows strict gate behavior: no code generation execution before explicit approval.
- Infrastructure Design remains skipped for this initiative as previously approved.
