# Code Generation Plan — U4: services/memory
## Initiative: Multi-Tenancy Model Implementation
**Date**: 2026-03-23  
**Unit**: U4 — `services/memory` (Wave 3)  
**Depends On**: U1 (`libs/soorma-common` ✅), U2 (`libs/soorma-service-common` ✅)  
**Change Type**: Major (~47 files)

---

## Unit Context

The Memory Service transitions from a two-column UUID FK identity model to a three-column
opaque-string identity model, rebuilt PostgreSQL RLS policies, and the `soorma-service-common`
shared middleware layer.

**Business Rules in force**: BR-U4-01 through BR-U4-11 (see functional-design/business-rules.md)  
**NFRs in force**: NFR-M-01 through NFR-M-06 (see nfr-requirements/nfr-requirements.md)  
**Security patterns**: RLS string-comparison policy, FORCE ROW LEVEL SECURITY, transaction-scoped set_config  
**QA gate**: TC-M-001 through TC-M-013 (see inception/test-cases/memory/ + enrichment-delta.md)

---

## Execution Summary

| Group | Steps | Files |
|-------|-------|-------|
| 1. Config, Alembic Migration | Steps 1–2 | 2 files |
| 2. ORM Models | Step 3 | 1 file |
| 3. Middleware, Dependencies, Database | Steps 4–6 | 3 files |
| 4. Main app | Step 7 | 1 file |
| 5. CRUD Layer | Steps 8–15 | 8 files |
| 6. Service Layer | Steps 16–23 | 8 files |
| 7. API Routes Layer | Steps 24–32 | 9 files (8 modify + 1 create) |
| 8. Data Deletion Service | Step 33 | 1 file (create) |
| 9. pyproject.toml | Step 34 | 1 file |
| 10. Tests | Steps 35–41 | ~10 files |
| 11. Documentation | Step 42 | code-summary.md |

---

## Step 1: Update Config — `memory_service/core/config.py`
- [ ] Remove `is_local_testing` field (BR-U4-10)
- [ ] Remove `default_tenant_name`, `default_user_id`, `default_username` fields (BR-U4-10)
- [ ] Update `default_tenant_id` default value to `"spt_00000000-0000-0000-0000-000000000000"` (BR-U4-07)
- [ ] Remove `sync_database_url` optional field (no longer needed — PostgreSQL-only, NFR-M-05)
- [ ] **File**: `services/memory/src/memory_service/core/config.py`

## Step 2: Create Alembic Migration 008 — `008_multi_tenancy_three_column_identity.py`
- [ ] Step 1 in migration: Drop all existing RLS policies on 8 tables (BR-U4-04)
- [ ] Step 2: Drop FK constraints on all 8 tables referencing `tenants.id` and `users.id`
- [ ] Step 3: `ADD COLUMN platform_tenant_id VARCHAR(64) NOT NULL DEFAULT 'spt_...'` on all 8 tables (BR-U4-07)
- [ ] Step 4: `ADD COLUMN service_tenant_id VARCHAR(64) NULL` on all 8 tables
- [ ] Step 5: `ADD COLUMN service_user_id VARCHAR(64) NULL` on all 8 tables
- [ ] Step 6: Migrate UUID FK data → string columns (`tenant_id::text → service_tenant_id`, `user_id::text → service_user_id`) for 7 tables (all except semantic_memory)
- [ ] Step 7: For `semantic_memory` — rename `user_id String(255) → service_user_id` via cast/truncate to VARCHAR(64) (BR-U4-05)
- [ ] Step 8: Drop old `tenant_id` and `user_id` columns from all 8 tables
- [ ] Step 9: Drop FK on `plan_context.plan_id → plans.id`; convert `plan_context.plan_id` to `String(100)`
- [ ] Step 10: Drop `tenants` table
- [ ] Step 11: Drop `users` table
- [ ] Step 12: Update unique constraints — `task_context` → `(platform_tenant_id, task_id)`; `plans` → `(platform_tenant_id, plan_id)`, `sessions` → `(platform_tenant_id, session_id)`
- [ ] Step 13: Rebuild RLS policies on all 8 tables using string comparison (NFR-M-01, Pattern 1)
- [ ] Step 14: `ENABLE ROW LEVEL SECURITY` + `FORCE ROW LEVEL SECURITY` on all 8 tables
- [ ] `downgrade()` function documented as data-destructive (BR-U4-04)
- [ ] **File**: `services/memory/alembic/versions/008_multi_tenancy_three_column_identity.py`

## Step 3: Update ORM Models — `memory_service/models/memory.py`
- [ ] Remove `Tenant` class and `User` class entirely
- [ ] Remove all `ForeignKey` imports/usages for `tenants.id` and `users.id`
- [ ] `SemanticMemory`: replace `tenant_id UUID FK` → `platform_tenant_id String(64) NOT NULL`; replace `user_id String(255)` → `service_user_id String(64) nullable=True`; add `service_tenant_id String(64) nullable=True`; update `__table_args__` UniqueConstraints (BR-U4-05)
- [ ] `EpisodicMemory`: same three-column pattern (both were UUID FKs)
- [ ] `ProceduralMemory`: same three-column pattern
- [ ] `WorkingMemory`: same three-column pattern; keep `plan_id` unchanged; keep `(plan_id, key)` unique constraint
- [ ] `TaskContext`: same three-column pattern; update unique constraint to `(platform_tenant_id, task_id)` (BR-U4-05)
- [ ] `PlanContext`: same three-column pattern; `plan_id` becomes plain `String(100)` (FK dropped in migration)
- [ ] `Plan`: same three-column pattern; update unique constraint to `(platform_tenant_id, plan_id)`
- [ ] `Session`: same three-column pattern; update unique constraint to `(platform_tenant_id, session_id)`
- [ ] **File**: `services/memory/src/memory_service/models/memory.py`

## Step 4: Delete Middleware — `memory_service/core/middleware.py`
- [ ] Delete file entirely (BR-U4-09)
- [ ] `TenancyMiddleware` is replaced entirely by `soorma_service_common.TenancyMiddleware`
- [ ] **File**: `services/memory/src/memory_service/core/middleware.py` → **DELETE**

## Step 5: Replace Dependencies — `memory_service/core/dependencies.py`
- [ ] Replace entire file with thin re-exports from `soorma_service_common` (BR-U4-09)
- [ ] Re-export: `TenantContext`, `get_tenant_context`, `get_tenanted_db` from `soorma_service_common`
- [ ] Use `create_get_tenanted_db` factory with local `get_db` (same pattern as registry U3)
- [ ] **File**: `services/memory/src/memory_service/core/dependencies.py`

## Step 6: Update Database — `memory_service/core/database.py`
- [ ] Remove `ensure_tenant_exists()` function (no tenants table)
- [ ] Remove `ensure_user_exists()` function (no users table)
- [ ] Remove `set_session_context()` function (replaced by `get_tenanted_db` from soorma-service-common)
- [ ] Keep `get_db()` generator (used by `create_get_tenanted_db` factory in dependencies.py)
- [ ] **File**: `services/memory/src/memory_service/core/database.py`

## Step 7: Update Main App — `memory_service/main.py`
- [ ] Update import: `from soorma_service_common import TenancyMiddleware` (remove local import)
- [ ] Remove `settings.is_local_testing` reference in lifespan startup log (BR-U4-10)
- [ ] **File**: `services/memory/src/memory_service/main.py`

---

## CRUD Layer (Steps 8–15)

*Pattern for all 8 CRUD files*:
- Replace `(tenant_id: UUID, user_id: UUID)` params → `(platform_tenant_id: str, service_tenant_id: str, service_user_id: str)` on all function signatures
- Replace all `Model.tenant_id == tenant_id`, `Model.user_id == user_id` WHERE conditions with new column names
- Remove `UUID` import where no longer needed (use `str` params instead)
- BR-U4-01: assert `platform_tenant_id` is non-empty at top of each function
- Keep all business logic, return types, and docstrings unchanged

## Step 8: Update CRUD — `crud/semantic.py`
- [ ] Signature: `(tenant_id: UUID, user_id: str)` → `(platform_tenant_id: str, service_tenant_id: str, service_user_id: str)` for `upsert_semantic_memory`, `get_semantic_memories`, `search_semantic`
- [ ] Update upsert ON CONFLICT keys to `(platform_tenant_id, service_tenant_id, external_id)`
- [ ] Update all WHERE clauses
- [ ] **File**: `services/memory/src/memory_service/crud/semantic.py`

## Step 9: Update CRUD — `crud/episodic.py`
- [ ] Signature: `(tenant_id: UUID, user_id: UUID)` → `(platform_tenant_id, service_tenant_id, service_user_id)`
- [ ] Update all WHERE clauses
- [ ] **File**: `services/memory/src/memory_service/crud/episodic.py`

## Step 10: Update CRUD — `crud/procedural.py`
- [ ] Signature: `(tenant_id: UUID, user_id: UUID)` → `(platform_tenant_id, service_tenant_id, service_user_id)`
- [ ] Update all WHERE clauses
- [ ] **File**: `services/memory/src/memory_service/crud/procedural.py`

## Step 11: Update CRUD — `crud/working.py`
- [ ] Signature: `(tenant_id: UUID, user_id: UUID)` → `(platform_tenant_id, service_tenant_id, service_user_id)`
- [ ] Keep `plan_id: str` (was UUID, now String(100) plain — no FK)
- [ ] Update all WHERE clauses; update upsert conflict constraint name if renamed
- [ ] **File**: `services/memory/src/memory_service/crud/working.py`

## Step 12: Update CRUD — `crud/task_context.py`
- [ ] Signature: `(tenant_id: UUID, user_id: UUID)` → `(platform_tenant_id, service_tenant_id, service_user_id)` (BR-U4-02: `service_tenant_id` required when `service_user_id` used)
- [ ] Update ON CONFLICT index_elements to `['platform_tenant_id', 'task_id']`
- [ ] Update all WHERE clauses
- [ ] **File**: `services/memory/src/memory_service/crud/task_context.py`

## Step 13: Update CRUD — `crud/plan_context.py`
- [ ] Signature: `(tenant_id: UUID, user_id: UUID)` → `(platform_tenant_id, service_tenant_id, service_user_id)`
- [ ] Update all WHERE clauses; `plan_id` stays as `str` (no longer UUID)
- [ ] **File**: `services/memory/src/memory_service/crud/plan_context.py`

## Step 14: Update CRUD — `crud/plans.py`
- [ ] Signature: `(tenant_id: UUID, user_id: UUID)` → `(platform_tenant_id, service_tenant_id, service_user_id)`
- [ ] Update ON CONFLICT / unique constraint references; `plan_id` stays `str`
- [ ] **File**: `services/memory/src/memory_service/crud/plans.py`

## Step 15: Update CRUD — `crud/sessions.py`
- [ ] Signature: `(tenant_id: UUID, user_id: UUID)` → `(platform_tenant_id, service_tenant_id, service_user_id)`
- [ ] Update all WHERE clauses
- [ ] **File**: `services/memory/src/memory_service/crud/sessions.py`

---

## Service Layer (Steps 16–23)

*Pattern for all 8 service files*: Update method signatures to pass `(platform_tenant_id, service_tenant_id, service_user_id)` to CRUD calls; extract these from caller (route) context.

## Step 16: Update Service — `services/semantic_memory_service.py`
- [ ] Signature: `(tenant_id: UUID, user_id: str)` → `(platform_tenant_id: str, service_tenant_id: str, service_user_id: str)` on all methods
- [ ] Update all CRUD call sites
- [ ] **File**: `services/memory/src/memory_service/services/semantic_memory_service.py`

## Step 17: Update Service — `services/episodic_memory_service.py`
- [ ] Signature update; update CRUD call sites
- [ ] **File**: `services/memory/src/memory_service/services/episodic_memory_service.py`

## Step 18: Update Service — `services/procedural_memory_service.py`
- [ ] Signature update; update CRUD call sites
- [ ] **File**: `services/memory/src/memory_service/services/procedural_memory_service.py`

## Step 19: Update Service — `services/working_memory_service.py`
- [ ] Signature update; update CRUD call sites
- [ ] **File**: `services/memory/src/memory_service/services/working_memory_service.py`

## Step 20: Update Service — `services/task_context_service.py`
- [ ] Signature update; update CRUD call sites (enforce BR-U4-02 at service layer)
- [ ] **File**: `services/memory/src/memory_service/services/task_context_service.py`

## Step 21: Update Service — `services/plan_context_service.py`
- [ ] Signature update; update CRUD call sites
- [ ] **File**: `services/memory/src/memory_service/services/plan_context_service.py`

## Step 22: Update Service — `services/plan_service.py`
- [ ] Signature update; update CRUD call sites
- [ ] **File**: `services/memory/src/memory_service/services/plan_service.py`

## Step 23: Update Service — `services/session_service.py`
- [ ] Signature update; update CRUD call sites
- [ ] **File**: `services/memory/src/memory_service/services/session_service.py`

---

## API Routes Layer (Steps 24–32)

*Pattern for all 8 route files*: Replace `context.tenant_id` → `context.platform_tenant_id`, `context.user_id` → `context.service_user_id`; add `context.service_tenant_id` where needed; update service call sites.

## Step 24: Update Route — `api/v1/semantic.py`
- [ ] Update all `context.tenant_id` → `context.platform_tenant_id`; `str(context.user_id)` → `context.service_user_id`
- [ ] Pass `context.service_tenant_id` to service calls
- [ ] **File**: `services/memory/src/memory_service/api/v1/semantic.py`

## Step 25: Update Route — `api/v1/episodic.py`
- [ ] Same context field replacement
- [ ] **File**: `services/memory/src/memory_service/api/v1/episodic.py`

## Step 26: Update Route — `api/v1/procedural.py`
- [ ] Same context field replacement
- [ ] **File**: `services/memory/src/memory_service/api/v1/procedural.py`

## Step 27: Update Route — `api/v1/working.py`
- [ ] Same context field replacement
- [ ] **File**: `services/memory/src/memory_service/api/v1/working.py`

## Step 28: Update Route — `api/v1/task_context.py`
- [ ] Same context field replacement
- [ ] **File**: `services/memory/src/memory_service/api/v1/task_context.py`

## Step 29: Update Route — `api/v1/plan_context.py`
- [ ] Same context field replacement
- [ ] **File**: `services/memory/src/memory_service/api/v1/plan_context.py`

## Step 30: Update Route — `api/v1/plans.py`
- [ ] Same context field replacement
- [ ] **File**: `services/memory/src/memory_service/api/v1/plans.py`

## Step 31: Update Route — `api/v1/sessions.py`
- [ ] Same context field replacement
- [ ] **File**: `services/memory/src/memory_service/api/v1/sessions.py`

## Step 32: Create Admin Route — `api/v1/admin.py`
- [ ] Create new file with 3 GDPR deletion endpoints (BR-U4-08)
- [ ] `DELETE /admin/tenant/{platform_tenant_id}` — delete all data for platform tenant
- [ ] `DELETE /admin/tenant/{platform_tenant_id}/service-tenant/{service_tenant_id}` — scoped deletion
- [ ] `DELETE /admin/tenant/{platform_tenant_id}/service-tenant/{service_tenant_id}/user/{service_user_id}` — user deletion
- [ ] Use bare `Depends(get_db)` (NOT `get_tenant_context`) — BR-U4-08
- [ ] Register router in `api/v1/__init__.py`
- [ ] **File**: `services/memory/src/memory_service/api/v1/admin.py` (CREATE)

---

## Step 33: Create Data Deletion Service — `services/data_deletion.py`
- [ ] Create `MemoryDataDeletion(PlatformTenantDataDeletion)` class (BR-U4-06)
- [ ] Import `PlatformTenantDataDeletion` from `soorma_service_common`
- [ ] Implement `delete_by_platform_tenant(db, platform_tenant_id)` — deletes from all 6 tables
- [ ] Implement `delete_by_service_tenant(db, platform_tenant_id, service_tenant_id)` — scoped
- [ ] Implement `delete_by_service_user(db, platform_tenant_id, service_tenant_id, service_user_id)` — requires both (BR-U4-02)
- [ ] `_TABLES_6` covers: SemanticMemory, EpisodicMemory, ProceduralMemory, WorkingMemory, TaskContext, PlanContext — NOT Plan, NOT Session (BR-U4-06)
- [ ] **File**: `services/memory/src/memory_service/services/data_deletion.py` (CREATE)

## Step 34: Update pyproject.toml
- [ ] Add `soorma-service-common` to dependencies
- [ ] Remove `aiosqlite` from dev dependencies (NFR-M-05 — PostgreSQL-only)
- [ ] **File**: `services/memory/pyproject.toml`

---

## Tests (Steps 35–41)

## Step 35: Update conftest.py
- [ ] Replace SQLite test engine with PostgreSQL async engine (AsyncMock pattern or pytest-asyncio fixture)
- [ ] Add `IS_LOCAL_TESTING` env var removal (no longer exists in Settings)
- [ ] Add `get_tenanted_db` override fixture using `soorma_service_common` mock pattern (same as registry conftest)
- [ ] Update `TEST_TENANT_ID` to string `"spt_test-tenant-001"` (not UUID)
- [ ] Add `TEST_SERVICE_TENANT_ID = "st_test-service-001"`, `TEST_SERVICE_USER_ID = "su_test-user-001"` constants
- [ ] **File**: `services/memory/tests/conftest.py`

## Step 36: Update `test_config.py`
- [ ] Remove tests for `is_local_testing`, `default_tenant_name`, `default_user_id`, `default_username`
- [ ] Add test: `default_tenant_id` default is `"spt_00000000-0000-0000-0000-000000000000"`
- [ ] **File**: `services/memory/tests/test_config.py`

## Step 37: Update `test_middleware.py`
- [ ] Remove tests for local `TenancyMiddleware` (deleted in Step 4)
- [ ] Add tests verifying `soorma_service_common.TenancyMiddleware` sets correct `request.state` fields: `platform_tenant_id`, `service_tenant_id`, `service_user_id`
- [ ] **File**: `services/memory/tests/test_middleware.py`

## Step 38: Update `test_semantic_crud.py` and `test_semantic_memory.py`
- [ ] Replace UUID `tenant_id`/`user_id` params with `platform_tenant_id`/`service_tenant_id`/`service_user_id` strings
- [ ] Update all fixture references
- [ ] **Files**: `tests/test_semantic_crud.py`, `tests/test_semantic_memory.py`

## Step 39: Update episodic, procedural, working memory tests
- [ ] Same fixture/param replacement in: `test_episodic_service.py`, `test_working_memory.py`, `test_working_memory_deletion.py`
- [ ] **Files**: 3 test files

## Step 40: Update task/plan context tests
- [ ] Same fixture/param replacement in: `test_task_context.py`, `test_plan_context.py`
- [ ] **Files**: 2 test files

## Step 41: Add RLS + deletion tests — `test_multi_tenancy.py`
- [ ] TC-M-003: Cross-tenant isolation (wrong `platform_tenant_id` → 0 rows)
- [ ] TC-M-005: `delete_by_platform_tenant()` deletes all rows across 6 tables
- [ ] TC-M-006: `delete_by_service_tenant()` scoped — sibling unaffected
- [ ] TC-M-009: Query without `set_config` → 0 rows
- [ ] TC-M-010: `service_user_id` filter requires `service_tenant_id`
- [ ] TC-M-011: `delete_by_service_user()` removes only that user's rows
- [ ] TC-M-012: `delete_by_platform_tenant()` does NOT delete from `plans` or `sessions` tables
- [ ] TC-M-013: Admin endpoint uses bare `get_db` (no RLS session variables)
- [ ] **File**: `services/memory/tests/test_multi_tenancy.py` (CREATE)

---

## Step 42: Update Code Summary Documentation
- [ ] Create `construction/memory/code/code-summary.md` documenting: modified files (39), created files (3), deleted files (1), test coverage
- [ ] **File**: `aidlc-docs/platform/multi-tenancy/construction/memory/code/code-summary.md`

---

## Dependencies & Interfaces

| Dependency | Status | Location |
|---|---|---|
| `soorma_common.models` | ✅ Available (U1 complete) | `libs/soorma-common` |
| `soorma_service_common.TenancyMiddleware` | ✅ Available (U2 complete) | `libs/soorma-service-common` |
| `soorma_service_common.create_get_tenanted_db` | ✅ Available (U2 complete) | `libs/soorma-service-common` |
| `soorma_service_common.TenantContext` | ✅ Available (U2 complete) | `libs/soorma-service-common` |
| `soorma_service_common.PlatformTenantDataDeletion` | ✅ Available (U2 complete) | `libs/soorma-service-common` |

## QA Traceability

| Test Case | Step |
|---|---|
| TC-M-001 (migration adds 3 columns) | Step 2 |
| TC-M-002 (tenants/users tables dropped) | Step 2 |
| TC-M-003 (cross-tenant isolation) | Step 41 |
| TC-M-004 (RLS FORCE) | Step 2 |
| TC-M-005 (delete_by_platform_tenant — 6 tables) | Steps 33, 41 |
| TC-M-006 (delete_by_service_tenant — scoped) | Steps 33, 41 |
| TC-M-007 (config: is_local_testing removed) | Steps 1, 36 |
| TC-M-008 (RLS string comparison, no ::uuid cast) | Step 2 |
| TC-M-009 (no set_config → 0 rows) | Step 41 |
| TC-M-010 (service_user_id requires service_tenant_id) | Steps 12, 32, 33 |
| TC-M-011 (delete_by_service_user — user rows only) | Steps 33, 41 |
| TC-M-012 (plans/sessions NOT in MemoryDataDeletion) | Steps 33, 41 |
| TC-M-013 (admin endpoint uses bare get_db) | Steps 32, 41 |
