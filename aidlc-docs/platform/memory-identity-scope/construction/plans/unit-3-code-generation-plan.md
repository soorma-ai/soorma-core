# Unit-3 Code Generation Plan

## Stage Context
- Initiative: Memory Service Identity-Scope Consistency Fix
- Unit: unit-3 (Schema/Index/Migration + Validation Tests)
- Project Type: Brownfield
- Workspace Root: . (soorma-core repo root)
- Code Location Rule: application code in repo root; documentation in aidlc-docs only

## Architecture Pattern Alignment (docs/ARCHITECTURE_PATTERNS.md)
- Section 1 (Authentication and Authorization): preserve identity isolation guarantees by enforcing schema/runtime parity.
- Section 2 (SDK Two-Layer): N/A for this unit (service schema and migration focus only).
- Section 3 (Event Choreography): N/A for this unit (no event contract changes).
- Section 4 (Multi-Tenancy): align uniqueness/index scope with full identity tuple.
- Section 5 (State Management): ensure context tables preserve deterministic ownership boundaries.
- Section 6 (Error Handling): remove runtime DB conflict failures caused by missing matching constraints.
- Section 7 (Testing): add migration/constraint/isolation validation tests.

## Unit Context and Traceability
- Unit responsibilities source: inception/application-design/unit-of-work.md (U3)
- Upstream dependency: U2 runtime conflict targets and predicates are complete and approved.
- FR/NFR coverage in this unit:
  - FR-8, FR-9, FR-11
  - NFR-3, NFR-4

## Planned Code Targets (Brownfield Modifications)
- Migration layer:
  - services/memory/alembic/versions/ (new unit-3 migration revision)
- Model layer:
  - services/memory/src/memory_service/models/memory.py (verify parity with migration)
- Test layer:
  - services/memory/tests/test_multi_tenancy.py
  - services/memory/tests/test_working_memory_deletion.py
  - services/memory/tests/test_semantic_crud.py
  - services/memory/tests/ (additional focused migration/constraint tests if needed)
- Documentation:
  - aidlc-docs/platform/memory-identity-scope/construction/unit-3/code/code-generation-summary.md

## Part 1 - Planning Checklist
- [x] Step 1: Analyze unit-3 context, dependencies, and required parity fixes.
- [x] Step 2: Identify exact brownfield files for migration/model/test updates.
- [x] Step 3: Build explicit implementation sequence for schema/index alignment.
- [x] Step 4: Save this unit-3 plan as the single source of truth.
- [x] Step 5: Prepare concise plan summary for approval gate.
- [x] Step 6: Log approval prompt context in audit.md.
- [x] Step 7: Wait for explicit user approval before any unit-3 code generation execution.

## Part 2 - Generation Steps (Execute Only After Approval)
- [x] Step 8: Create migration revision for working_memory uniqueness alignment.
  - Drop legacy `plan_key_unique`.
  - Add full-identity unique constraint matching runtime ON CONFLICT target.
- [x] Step 9: Create migration changes for plans/sessions uniqueness alignment.
  - Update `plan_unique` and `sessions_unique` to full identity tuple.
- [x] Step 10: Create migration changes for semantic private index alignment.
  - Ensure private indexes include `service_tenant_id` where runtime uses it.
- [x] Step 11: Validate migration idempotence and deterministic ordering.
  - Use IF EXISTS/IF NOT EXISTS where appropriate.
  - Confirm upgrade path from current production schema state.
- [x] Step 12: Confirm model-to-migration parity for affected constraints/indexes.
- [x] Step 13: Add/adjust tests for:
  - ON CONFLICT target compatibility
  - cross-service-tenant and cross-user isolation
  - no regression in user-scoped query behavior
- [x] Step 14: Run focused memory test suite and capture results.
- [x] Step 15: Generate unit-3 code summary artifact in construction/unit-3/code/.
- [x] Step 16: Update aidlc-state.md + audit.md with execution and review-gate status.

## Security Baseline Compliance (Planning Stage)
- SECURITY-03: Compliant by intent (logging/security behavior unchanged; parity work only).
- SECURITY-05: Compliant by intent (identity validation boundaries remain fail-closed).
- SECURITY-08: Compliant by intent (object-level scope hardening via DB constraints/indexes).
- SECURITY-15: Compliant by intent (remediates runtime conflict failures without weakening guardrails).
- Remaining SECURITY rules: N/A at planning stage.

## Notes
- This plan prioritizes restoring main-branch stability by resolving runtime/schema mismatch quickly.
- Implementation starts only after explicit approval for this plan.
