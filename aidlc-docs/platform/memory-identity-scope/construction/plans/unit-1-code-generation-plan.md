# Unit-1 Code Generation Plan

## Stage Context
- Initiative: Memory Service Identity-Scope Consistency Fix
- Unit: unit-1 (Shared Identity Dependency)
- Project Type: Brownfield
- Workspace Root: . (soorma-core repo root)
- Code Location Rule: application code in repo root; documentation in aidlc-docs only

## Architecture Pattern Alignment (Soorma Core)
- Section 1 (Authentication): Implement shared validation for both service tenant and service user context; keep generic errors (no transport/header leakage).
- Section 2 (Two-Layer SDK): N/A for unit-1 code changes because scope is shared backend dependency only (no new SDK service methods/wrappers).
- Section 6 (Error Handling): Return deterministic HTTP 400 validation failures through shared dependency path.
- Section 7 (Testing): Add focused shared-library unit tests for behavior contract.

## Unit Context and Traceability
- Unit responsibilities source: `inception/application-design/unit-of-work.md` (U1)
- Requirement mapping source: `inception/application-design/unit-of-work-story-map.md`
- Unit dependencies source: `inception/application-design/unit-of-work-dependency.md`
- Dependencies: None upstream; output consumed by unit-2
- Service boundaries: shared library only (`libs/soorma-service-common`), no memory-service endpoint adoption in unit-1
- FR/NFR coverage in this unit:
  - FR-2, FR-3 (dependency creation and reusable adoption seam)
  - NFR-1 (generic validation errors)
  - NFR-5 (extensible shared dependency design)

## Part 1 - Planning Checklist
- [x] Step 1: Analyze unit context and load unit design artifacts (functional design, NFR requirements, NFR design).
- [x] Step 2: Identify exact code locations to modify in brownfield structure.
- [x] Step 3: Include unit generation context (stories, dependencies, interfaces, boundaries).
- [x] Step 4: Create and save this code generation plan as the single source of truth.
- [x] Step 5: Summarize plan and scope for review.
- [x] Step 6: Log approval prompt in audit.md.
- [x] Step 7: Wait for explicit user approval to execute generation.
- [x] Step 8: Record approval response in audit.md.
- [x] Step 9: Update aidlc-state.md for transition from planning to generation.

## Part 2 - Generation Steps (to execute only after approval)
- [x] Step 10: STUB phase in shared dependency module.
  - Target: `libs/soorma-service-common/src/soorma_service_common/dependencies.py`
  - Add `require_user_context` with full type hints and Google-style docstring.
  - Keep implementation scaffold minimal and composable per design.
- [x] Step 11: Export surface update.
  - Target: `libs/soorma-service-common/src/soorma_service_common/__init__.py`
  - Export `require_user_context` for stable top-level imports.
- [x] Step 12: RED phase tests for real behavior.
  - Target: `libs/soorma-service-common/tests/test_dependencies.py`
  - Add tests for success pass-through, missing service tenant, missing service user, empty/whitespace values, and generic messages.
  - Ensure tests reflect real expected behavior contract.
- [x] Step 13: GREEN phase implementation.
  - Replace stub/placeholder with real validation logic in `dependencies.py`.
  - Ensure errors are generic and transport-agnostic.
  - Add structured warning logging seam with safe fields only (no service tenant/user identifiers).
- [x] Step 14: REFACTOR and cleanup.
  - Improve naming, deduplicate helper logic, keep complexity auditable.
  - Preserve existing public APIs and behavior outside unit-1 scope.
- [x] Step 15: Run unit-1 verification tests.
  - Command scope: `libs/soorma-service-common/tests/test_dependencies.py` (and adjacent impacted tests if needed).
  - Confirm no regressions in shared dependency tests.
- [x] Step 16: Write unit code summary artifact.
  - Target: `aidlc-docs/platform/memory-identity-scope/construction/unit-1/code/code-generation-summary.md`
  - Include modified files, test outcomes, and requirement traceability.
- [x] Step 17: Update progress tracking.
  - Mark completed steps [x] in this plan.
  - Update `aidlc-state.md` and append execution audit entries.
  - Keep construction design PR checkpoint marked approved.

## Security Baseline Compliance Check (Planning Stage)
- SECURITY-01 through SECURITY-15: N/A for planning artifact generation in this stage.
- Rationale: No runtime code, infrastructure, or deployment changes executed yet; checks will be enforced during code generation outputs.

## Notes
- This plan intentionally does not include unit-2 memory-service route wiring.
- This plan follows strict gate behavior: no generation until explicit approval.
