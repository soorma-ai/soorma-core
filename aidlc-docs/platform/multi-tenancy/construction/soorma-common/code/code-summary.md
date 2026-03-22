# Code Summary — U1: soorma-common
## Initiative: Multi-Tenancy Model Implementation
**Unit**: U1 — `libs/soorma-common`
**Wave**: 1 (no dependencies)
**Completed**: 2026-03-22
**Branch**: dev

---

## Requirements Implemented

| Requirement | Description | Status |
|---|---|---|
| FR-1.1 | `DEFAULT_PLATFORM_TENANT_ID` constant | ✅ |
| FR-1.2 | `SOORMA_PLATFORM_TENANT_ID` env var override | ✅ |
| FR-1.3 | Code comment warning against production use | ✅ |
| FR-1.4 | No format validation on IDs | ✅ |
| FR-6.1 | `EventEnvelope.platform_tenant_id` field defaults to `None` | ✅ |
| FR-6.2 | Field accepts opaque string values | ✅ |
| FR-6.3 | Backward compatible — existing envelope construction unchanged | ✅ |
| FR-6.4 | `tenant_id` and `platform_tenant_id` are distinct fields | ✅ |
| NFR-3.2 | Opaque string, no UUID validation | ✅ |
| NFR-3.3 | Deprecation warning as code comment | ✅ |

---

## Files Changed

### New Files

| File | Description |
|---|---|
| `libs/soorma-common/src/soorma_common/tenancy.py` | New module — provides `DEFAULT_PLATFORM_TENANT_ID` constant with `SOORMA_PLATFORM_TENANT_ID` env var override. Sentinel value: `spt_00000000-0000-0000-0000-000000000000`. Imports only `os`. |
| `libs/soorma-common/tests/test_tenancy.py` | TDD tests for `tenancy.py` — 5 tests covering default value, env var override, empty env var fallback, type assertion, and no-framework-import constraint. |

### Modified Files

| File | Change |
|---|---|
| `libs/soorma-common/src/soorma_common/events.py` | Added `platform_tenant_id: Optional[str] = Field(default=None, ...)` to `EventEnvelope` adjacent to `tenant_id`/`user_id`. Updated docstrings for `tenant_id` and `user_id` to clarify service-layer scope vs platform-layer scope. |
| `libs/soorma-common/src/soorma_common/__init__.py` | Added `from .tenancy import DEFAULT_PLATFORM_TENANT_ID` export. |
| `libs/soorma-common/tests/test_events.py` | Added 4 new tests to `TestEventEnvelope`: `test_platform_tenant_id_defaults_to_none`, `test_platform_tenant_id_accepts_opaque_string`, `test_platform_tenant_id_backward_compatible`, `test_tenant_id_field_semantics`. |

---

## Test Results

```
112 passed in 0.33s
```

All 112 tests pass. No regressions.

### New Tests Added
- `tests/test_tenancy.py` — 5 tests (new file)
- `tests/test_events.py` — 4 tests added to `TestEventEnvelope`

---

## Downstream Contracts Locked

These artifacts are now stable and consumed by downstream units:

| Contract | Consumed By |
|---|---|
| `DEFAULT_PLATFORM_TENANT_ID` constant (exported from `soorma_common`) | U2 (soorma-service-common), U3 (services/registry), U4 (services/event), U5 (services/memory), U6 (sdk) |
| `EventEnvelope.platform_tenant_id: Optional[str]` field | U5 (services/memory), U7 if applicable |

---

## TDD Cycle Executed

| Step | Action | Result |
|---|---|---|
| STUB | `tenancy.py` with `DEFAULT_PLATFORM_TENANT_ID = ""` | Imports without error |
| RED | `test_tenancy.py` — 3 fail (AssertionError), 2 pass structural tests | Confirmed RED |
| GREEN | Implemented `os.environ.get(...) or "spt_..."` | 5/5 pass |
| STUB | 4 new `test_events.py` tests before field added | Confirmed RED (AttributeError) |
| GREEN | Added `platform_tenant_id` field to `EventEnvelope`; updated docstrings | 24/24 pass |
| GREEN | Exported `DEFAULT_PLATFORM_TENANT_ID` from `__init__.py` | Export resolves correctly |
| REFACTOR | Verified no UUID validation, no framework imports in `tenancy.py`, full suite | 112/112 pass |
