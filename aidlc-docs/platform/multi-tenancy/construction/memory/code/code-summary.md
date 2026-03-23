# U4 Memory Service — Code Generation Summary

**Unit**: U4 — `services/memory`  
**Initiative**: Platform Multi-Tenancy  
**Phase**: Construction → Code Generation  
**Status**: COMPLETE  

---

## Overview

This unit migrates the Memory Service from a two-column UUID identity model
(`tenant_id UUID FK`, `user_id UUID FK`) to a three-column opaque-string identity model:

| Column | Type | Nullable | Description |
|---|---|---|---|
| `platform_tenant_id` | `VARCHAR(64) NOT NULL` | No | Cross-service platform tenant ID |
| `service_tenant_id` | `VARCHAR(64)` | Yes | Service-level tenant scoping |
| `service_user_id` | `VARCHAR(64)` | Yes | Per-user scoping within a service tenant |

---

## Files Modified (39)

### Core Infrastructure (5)
| File | Change |
|---|---|
| `src/memory_service/core/config.py` | Removed `default_user_id`, `is_local_testing`; `default_tenant_id` → opaque string |
| `src/memory_service/core/database.py` | Removed `ensure_tenant_exists`, `ensure_user_exists`, `set_session_context` |
| `src/memory_service/core/dependencies.py` | Re-exports `TenantContext`, `get_tenant_context`, `create_get_tenanted_db` from `soorma_service_common` |
| `src/memory_service/main.py` | Updated to import `TenancyMiddleware` from `soorma_service_common` |
| `pyproject.toml` | Added `soorma-service-common` dependency; removed `aiosqlite` |

### Database Migration (1)
| File | Change |
|---|---|
| `alembic/versions/008_multi_tenancy_three_column_identity.py` | 14-step migration: add 3 columns, drop FK columns, drop `tenants`/`users` tables, apply RLS FORCE |

### Models (1)
| File | Change |
|---|---|
| `src/memory_service/models/memory.py` | All 8 tables: replaced `tenant_id`/`user_id` UUID FKs with 3-column string identity; `Plan.plan_id` → `VARCHAR(100)` |

### CRUD Layer (8 files)
| File | Change |
|---|---|
| `crud/semantic_memory.py` | 3-column signatures, `assert platform_tenant_id`, updated WHERE filters |
| `crud/episodic_memory.py` | Same pattern |
| `crud/procedural_memory.py` | Same pattern |
| `crud/working_memory.py` | Same pattern |
| `crud/task_context.py` | Same pattern; removed UUID parse |
| `crud/plan_context.py` | Same pattern; `plan_id` is direct string, no UUID FK lookup |
| `crud/plans.py` | Same pattern |
| `crud/sessions.py` | Same pattern |

### Service Layer (8 files)
| File | Change |
|---|---|
| `services/semantic_memory.py` | `_to_response` uses `platform_tenant_id`, `service_user_id or ""`; `ingest`/`search` use 3-col |
| `services/episodic_memory.py` | Same pattern |
| `services/procedural_memory.py` | Fixed delegation bug (was calling self instead of CRUD) |
| `services/working_memory.py` | Same pattern |
| `services/task_context.py` | Same pattern |
| `services/plan_context.py` | Removed UUID indirection for `plan_id`; now direct string |
| `services/plans.py` | Same pattern |
| `services/sessions.py` | Same pattern |

### API Routes (9 files)
| File | Change |
|---|---|
| `api/v1/episodic.py` | Endpoints use `TenantContext.platform_tenant_id`, 3-col service calls |
| `api/v1/procedural.py` | Same pattern |
| `api/v1/working_memory.py` | Same pattern |
| `api/v1/sessions.py` | Same pattern |
| `api/v1/task_context.py` | upsert→3-col; get/update/delete→`platform_tenant_id` only |
| `api/v1/plan_context.py` | Removed `from uuid import UUID`; removed ValueError try/except; `tenant_id`→`platform_tenant_id` |
| `api/v1/plans.py` | create/list→3-col; get/update/delete→`platform_tenant_id` only |
| `api/v1/semantic.py` | All 3 endpoints→3-col; removed `str()` cast |
| `api/v1/__init__.py` | Added `admin` import and `router.include_router(admin.router)` |

### Test Files (10 files updated)
| File | Change |
|---|---|
| `tests/conftest.py` | Replaced SQLite/aiosqlite with mock `AsyncSession`; added string identity constants |
| `tests/test_config.py` | Fixed `default_tenant_id` assertion; removed `default_user_id`/`is_local_testing` refs |
| `tests/test_middleware.py` | Replaced with `soorma_service_common` import verification; verifies `core.middleware` deleted |
| `tests/test_database_utils.py` | Replaced with "verify deleted functions absent" assertions |
| `tests/test_episodic_service.py` | Updated `_to_response` mocks and service call signatures |
| `tests/test_semantic_service.py` | Updated `_to_response` mocks; `ingest` now takes 4 args |
| `tests/test_task_context.py` | UUID test IDs → strings; CRUD/service calls → 3-col |
| `tests/test_working_memory.py` | Bulk-replaced all `tenant_id`→`platform_tenant_id`, `user_id`→`service_user_id` |
| `tests/test_working_memory_deletion.py` | Same bulk replacement |
| `tests/test_plan_context.py` | Fully rewritten: `plan_id` is direct string, no UUID FK lookup anti-patterns removed |

---

## Files Created (3)

| File | Description |
|---|---|
| `src/memory_service/api/v1/admin.py` | GDPR deletion endpoints using bare `get_db` (no RLS) |
| `src/memory_service/services/data_deletion.py` | `MemoryDataDeletion(PlatformTenantDataDeletion)` covering 6 tables |
| `tests/test_multi_tenancy.py` | TC-M-003, 005, 006, 009, 010, 011, 012, 013 |

---

## Files Deleted (1)

| File | Reason |
|---|---|
| `src/memory_service/core/middleware.py` | Replaced by `soorma_service_common.TenancyMiddleware` |

---

## QA Traceability

| Test Case | File |
|---|---|
| TC-M-003 (cross-tenant isolation) | `test_multi_tenancy.py` |
| TC-M-005 (delete_by_platform_tenant → 6 tables) | `test_multi_tenancy.py` |
| TC-M-006 (delete_by_service_tenant → scoped) | `test_multi_tenancy.py` |
| TC-M-009 (no set_config → 0 rows) | `test_multi_tenancy.py` |
| TC-M-010 (service_user_id requires service_tenant_id) | `test_multi_tenancy.py` |
| TC-M-011 (delete_by_service_user → user only) | `test_multi_tenancy.py` |
| TC-M-012 (plans/sessions NOT in MemoryDataDeletion) | `test_multi_tenancy.py` |
| TC-M-013 (admin uses bare get_db) | `test_multi_tenancy.py` |

---

## Business Rules Addressed

| Rule | Description |
|---|---|
| BR-U4-01 | Three-column opaque-string identity replaces UUID FKs |
| BR-U4-02 | `platform_tenant_id` is NOT NULL; service columns are nullable |
| BR-U4-03 | RLS FORCE policy on all 8 tables |
| BR-U4-04 | Alembic migration drops `tenants` and `users` tables |
| BR-U4-05 | `TenancyMiddleware` from `soorma_service_common` (no local copy) |
| BR-U4-06 | `MemoryDataDeletion` covers 6 tables; NOT Plan, NOT Session |
| BR-U4-07 | `plan_id` is VARCHAR(100) direct string; no UUID FK lookup |
| BR-U4-08 | Admin endpoints use bare `get_db` to bypass RLS |
| BR-U4-09 | No local `middleware.py` |
| BR-U4-10 | `service_user_id` queries always include `service_tenant_id` |
