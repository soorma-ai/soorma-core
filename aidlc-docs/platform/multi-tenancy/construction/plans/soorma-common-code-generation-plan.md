# Code Generation Plan — soorma-common (U1)
## Initiative: Multi-Tenancy Model Implementation
**Unit**: U1 — `libs/soorma-common`
**Wave**: 1 (no dependencies)
**Date**: 2026-03-22

---

## Unit Context

**Stories / Requirements implemented by this unit**:
- FR-1.1: `DEFAULT_PLATFORM_TENANT_ID` constant
- FR-1.2: `SOORMA_PLATFORM_TENANT_ID` env var override
- FR-1.3: Code comment warning against production use
- FR-1.4: No format validation on IDs
- FR-6.1–6.4: `EventEnvelope.platform_tenant_id` field + updated docstrings for `tenant_id` / `user_id`
- NFR-3.2: Opaque string, no UUID validation
- NFR-3.3: Deprecation warning as code comment

**Dependencies**: None — U1 is Wave 1

**Downstream contracts locked by this unit**:
- `DEFAULT_PLATFORM_TENANT_ID` constant (consumed by U2–U6)
- `EventEnvelope.platform_tenant_id` field (consumed by U5, U7)

**Application code root**: `.` (soorma-core repo root)  
**Documentation root**: `aidlc-docs/platform/multi-tenancy/`

---

## TDD Cycle: STUB → RED → GREEN → REFACTOR

This unit uses the **soorma-core TDD mandate**: all steps must follow STUB → RED → GREEN → REFACTOR strictly.

---

## Steps

### Step 1: STUB — Create `soorma_common/tenancy.py` (stub)
- [ ] Create `libs/soorma-common/src/soorma_common/tenancy.py`
- [ ] Define `DEFAULT_PLATFORM_TENANT_ID: str = ""` (stub — wrong value, tests will fail)
- [ ] Include the required code comment warning (NFR-3.3)
- [ ] Verify module imports without error

**Target file**: `libs/soorma-common/src/soorma_common/tenancy.py`

---

### Step 2: RED — Write `test_tenancy.py` (tests must FAIL against stub)
- [ ] Create `libs/soorma-common/tests/test_tenancy.py`
- [ ] Write `TestDefaultPlatformTenantId`:
  - `test_default_value` — asserts value equals `"spt_00000000-0000-0000-0000-000000000000"` (FAILS against stub `""`)
  - `test_env_var_override` — monkeypatches `SOORMA_PLATFORM_TENANT_ID`, reimports module, asserts override value is used
  - `test_env_var_empty_uses_default` — env var set to `""` → falls back to literal default
- [ ] Run tests: verify they **FAIL** with assertion errors (not ImportError/AttributeError)

**Target file**: `libs/soorma-common/tests/test_tenancy.py`

---

### Step 3: GREEN — Implement `tenancy.py` (real logic, tests must PASS)
- [ ] Replace stub value with real env var resolution logic in `tenancy.py`
- [ ] Run `test_tenancy.py`: verify all tests **PASS**

---

### Step 4: STUB — `EventEnvelope` field not yet added (RED state for new tests)
- [ ] Write new test methods in `libs/soorma-common/tests/test_events.py`:
  - `test_platform_tenant_id_defaults_to_none` — creates `EventEnvelope` without `platform_tenant_id`, asserts field is `None`
  - `test_platform_tenant_id_accepts_opaque_string` — sets `platform_tenant_id="spt_test-123"`, asserts value stored correctly
  - `test_platform_tenant_id_backward_compatible` — existing minimal envelope construction still works (no required field added)
  - `test_tenant_id_field_semantics` — verify `tenant_id` is optional string (existing field, docstring context test)
- [ ] Run the new tests: they must **FAIL** with `AttributeError: 'EventEnvelope' has no attribute 'platform_tenant_id'`

---

### Step 5: GREEN — Add `platform_tenant_id` field to `EventEnvelope`
- [ ] Modify `libs/soorma-common/src/soorma_common/events.py`:
  - Add `platform_tenant_id: Optional[str]` field adjacent to `tenant_id` / `user_id`
  - Update `platform_tenant_id` field docstring: "Platform tenant ID — injected by Event Service from authenticated X-Tenant-ID header at publish time. SDK agents MUST NOT set this field; any value will be overwritten by the Event Service."
  - Update `tenant_id` field docstring: "Service tenant ID — SDK-supplied. Identifies the tenant within the service layer (e.g., memory, tracker). Distinct from `platform_tenant_id`. Passed through the event bus unchanged."
  - Update `user_id` field docstring: "Service user ID — SDK-supplied. Identifies the user within the service tenant context. Passed through the event bus unchanged."
- [ ] Run all `test_events.py` tests: new tests **PASS**, existing tests still **PASS**

---

### Step 6: GREEN — Export `DEFAULT_PLATFORM_TENANT_ID` from `__init__.py`
- [ ] Modify `libs/soorma-common/src/soorma_common/__init__.py`:
  - Add `from .tenancy import DEFAULT_PLATFORM_TENANT_ID` (import from new module)
  - Add `DEFAULT_PLATFORM_TENANT_ID` to the public exports block
- [ ] Verify import: `from soorma_common import DEFAULT_PLATFORM_TENANT_ID` resolves correctly

---

### Step 7: REFACTOR — Review and clean up
- [ ] Review `tenancy.py` for clarity: ensure code comment warning is prominent
- [ ] Verify no UUID format validation was accidentally introduced
- [ ] Verify `tenancy.py` imports only `os` (no FastAPI/Starlette/SQLAlchemy)
- [ ] Run full test suite: `pytest libs/soorma-common/tests/` — all tests pass

---

### Step 8: Code Summary
- [ ] Create `aidlc-docs/platform/multi-tenancy/construction/soorma-common/code/code-summary.md`
  - List all modified and created files with purpose
  - Note test execution results (expected: all pass)

---

## Files Touch List

| File | Status | Description |
|------|--------|-------------|
| `libs/soorma-common/src/soorma_common/tenancy.py` | **NEW** | `DEFAULT_PLATFORM_TENANT_ID` constant + env var resolution |
| `libs/soorma-common/src/soorma_common/events.py` | **MODIFIED** | Add `platform_tenant_id` field; update `tenant_id` + `user_id` docstrings |
| `libs/soorma-common/src/soorma_common/__init__.py` | **MODIFIED** | Export `DEFAULT_PLATFORM_TENANT_ID` |
| `libs/soorma-common/tests/test_tenancy.py` | **NEW** | TDD tests for constant + env var resolution |
| `libs/soorma-common/tests/test_events.py` | **MODIFIED** | Add tests for `platform_tenant_id` field |
| `aidlc-docs/platform/multi-tenancy/construction/soorma-common/code/code-summary.md` | **NEW** | Step 8 documentation |

---

## Story Coverage

| Requirement | Steps |
|---|---|
| FR-1.1 (constant) | Steps 1, 2, 3, 6 |
| FR-1.2 (env var override) | Steps 1, 2, 3 |
| FR-1.3 (code comment warning) | Step 1, 7 |
| FR-1.4 (no format validation) | Step 7 |
| FR-6.1–6.4 (EventEnvelope changes) | Steps 4, 5 |
| NFR-3.2 (opaque strings) | Steps 5, 7 |
| NFR-3.3 (warning) | Step 1 |
