# Code Generation Plan — soorma-service-common (U2)
## Initiative: Multi-Tenancy Model Implementation
**Date**: 2026-03-22

---

## Unit Context

| Attribute | Value |
|---|---|
| Unit | U2 — `libs/soorma-service-common` |
| Change Type | Greenfield — new library |
| Workspace Root | `.` (soorma-core repo root) |
| Target Path | `libs/soorma-service-common/` |
| Depends On | U1 (`libs/soorma-common`) — complete |
| Unblocks | U4 (services/memory), U5 (services/tracker), U7 (services/event-service) |

## Design Artifacts

- Functional Design: `aidlc-docs/platform/multi-tenancy/construction/soorma-service-common/functional-design/`
- NFR Requirements: `aidlc-docs/platform/multi-tenancy/construction/soorma-service-common/nfr-requirements/`
- NFR Design: `aidlc-docs/platform/multi-tenancy/construction/soorma-service-common/nfr-design/`

## Extensions Active

- **security-baseline**: SECURITY-05 (input validation) — applicable to `get_tenanted_db` and `set_config_for_session` (caller-supplied string parameters). Addressed via type hints + None-to-empty-string guard.
- **qa-test-cases (B)**: Construction-pass test specs to be generated after implementation.
- **pr-checkpoint**: N/A at this step (gate already approved).
- **jira-tickets**: N/A at this step.

---

## File Structure to Create

```
libs/soorma-service-common/
├── pyproject.toml
├── README.md
└── src/
    └── soorma_service_common/
        ├── __init__.py
        ├── middleware.py
        ├── dependencies.py
        ├── tenant_context.py
        ├── deletion.py
        └── py.typed
tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_middleware.py
    ├── test_dependencies.py
    ├── test_tenant_context.py
    └── test_deletion.py
```

---

## Steps

### STUB PHASE

- [ ] **Step 1**: Create `libs/soorma-service-common/pyproject.toml`
- [ ] **Step 2**: Create `libs/soorma-service-common/README.md`
- [ ] **Step 3**: Create `libs/soorma-service-common/src/soorma_service_common/__init__.py` (stub exports)
- [ ] **Step 4**: Create `libs/soorma-service-common/src/soorma_service_common/py.typed`
- [ ] **Step 5**: Create `libs/soorma-service-common/src/soorma_service_common/middleware.py` (stub — `NotImplementedError`)
- [ ] **Step 6**: Create `libs/soorma-service-common/src/soorma_service_common/dependencies.py` (stub — `NotImplementedError`)
- [ ] **Step 7**: Create `libs/soorma-service-common/src/soorma_service_common/tenant_context.py` (stub — `NotImplementedError`)
- [ ] **Step 8**: Create `libs/soorma-service-common/src/soorma_service_common/deletion.py` (ABC — raises `NotImplementedError` by design)

### RED PHASE (tests written for REAL expected behaviour — will fail on stubs)

- [ ] **Step 9**: Create `libs/soorma-service-common/tests/__init__.py`
- [ ] **Step 10**: Create `libs/soorma-service-common/tests/conftest.py` (shared fixtures: mock `Request`, mock `AsyncSession`, test FastAPI app)
- [ ] **Step 11**: Create `libs/soorma-service-common/tests/test_middleware.py`
  - Header extraction: X-Tenant-ID → `request.state.platform_tenant_id`
  - Header extraction: X-Service-Tenant-ID → `request.state.service_tenant_id`
  - Header extraction: X-User-ID → `request.state.service_user_id`
  - Absent X-Tenant-ID → falls back to `DEFAULT_PLATFORM_TENANT_ID`
  - Absent X-Service-Tenant-ID / X-User-ID → `None`
  - Health/docs paths bypass middleware (no `request.state` set)
  - BR-U2-01: middleware does NOT call any DB function
- [ ] **Step 12**: Create `libs/soorma-service-common/tests/test_dependencies.py`
  - `get_platform_tenant_id` reads from `request.state.platform_tenant_id`
  - `get_service_tenant_id` reads from `request.state.service_tenant_id`
  - `get_service_user_id` reads from `request.state.service_user_id`
  - `get_tenanted_db`: yields AsyncSession; verifies `set_config` called x3 with correct args
  - `get_tenanted_db`: verifies third arg to `set_config` is `true` (transaction-scoped — NFR-U2-SEC-01, BR-U2-04)
  - `get_tenanted_db`: `None` service_tenant_id → `''` passed to `set_config` (BR-U2-05)
  - `get_tenanted_db`: `None` service_user_id → `''` passed to `set_config` (BR-U2-05)
  - `set_config_for_session`: same set_config assertions (direct DB session path — NATS path)
- [ ] **Step 13**: Create `libs/soorma-service-common/tests/test_tenant_context.py`
  - `get_tenant_context` assembles `TenantContext` with correct identity values from `request.state`
  - `TenantContext.db` is the session from `get_tenanted_db` (RLS-activated)
  - `TenantContext.platform_tenant_id` is always non-None
- [ ] **Step 14**: Create `libs/soorma-service-common/tests/test_deletion.py`
  - `PlatformTenantDataDeletion` is abstract — cannot be instantiated directly
  - Concrete subclass with all 3 methods implemented can be instantiated
  - Each abstract method signature matches: `delete_by_platform_tenant(db, platform_tenant_id) -> int`
  - `delete_by_service_tenant(db, platform_tenant_id, service_tenant_id) -> int`
  - `delete_by_service_user(db, platform_tenant_id, service_tenant_id, service_user_id) -> int`
  - Partial subclass (missing an abstract method) cannot be instantiated (Python ABC enforcement)
- [ ] **Step 15**: Run tests — verify RED (all fail due to `NotImplementedError`, NOT import/attribute errors)

### GREEN PHASE (implement real logic)

- [ ] **Step 16**: Implement `middleware.py` — `TenancyMiddleware.dispatch()` (header extraction, DEFAULT fallback, health path bypass)
- [ ] **Step 17**: Implement `dependencies.py` — `get_platform_tenant_id`, `get_service_tenant_id`, `get_service_user_id`, `get_tenanted_db`, `set_config_for_session`
- [ ] **Step 18**: Implement `tenant_context.py` — `TenantContext` dataclass + `get_tenant_context`
- [ ] **Step 19**: Run all tests — verify GREEN (all pass)

### REFACTOR PHASE

- [ ] **Step 20**: Update `__init__.py` with complete public API exports
- [ ] **Step 21**: Verify `pyproject.toml` has no forbidden dependencies (no service-package deps; no SDK deps)
- [ ] **Step 22**: Run tests again — confirm GREEN after refactor

### CODE SUMMARY ARTIFACT

- [ ] **Step 23**: Write `aidlc-docs/platform/multi-tenancy/construction/soorma-service-common/code/code-summary.md`

---

## Security Baseline Compliance at Code Generation

| Rule | Status | Notes |
|------|--------|-------|
| SECURITY-01 | N/A | No data stores in this library |
| SECURITY-02 | N/A | No network intermediaries in this library |
| SECURITY-03 | N/A | No deployed application; library has no logger config |
| SECURITY-04 | N/A | No HTML-serving endpoints |
| SECURITY-05 | Enforced | Type hints on all functions; None→'' guard in set_config calls; parameterized DB calls via SQLAlchemy text() with bound params |
