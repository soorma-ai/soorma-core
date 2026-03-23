# Test Specifications — Narrative
## Unit: memory
## Initiative: Multi-Tenancy Model Implementation
## Scope: happy-path-negative
**Unit abbreviation**: M = memory

---

### TC-M-001 — Alembic migration drops tenants and users reference tables

**Context**: The Memory Service's legacy `tenants` and `users` FK reference tables must be dropped as part of the breaking schema migration. Soorma does not own service-tier identity. Covers FR-3.1.

**Scenario description**: The Alembic migration is applied to a test database with the old schema. The `tenants` and `users` tables no longer exist after the migration.

**Steps**:
1. Apply the Memory Service Alembic breaking migration to a test database
2. Query the PostgreSQL information schema for table names
3. Check for presence of `tenants` and `users` tables

**Expected outcome**: Neither `tenants` nor `users` table exists in the database after migration. No foreign key constraints reference these tables.

**Technical details** (from construction design):
- Migration file: `services/memory/alembic/versions/008_multi_tenancy_three_column_identity.py`
- Drop ordering (BR-U4-04): Step 1 drops all existing RLS policies on all 8 tables → Step 2 drops FK constraints referencing `tenants.id`/`users.id` → Steps 10–11 execute `DROP TABLE tenants; DROP TABLE users`; this ordering is required because old policies reference `::UUID` cast that becomes invalid after column type change
- Assertion: `SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name IN ('tenants', 'users')` must return 0 rows
- Finding reference: business-rules.md BR-U4-04, domain-entities.md (Dropped Entities)

**Scope tag**: happy-path
**Priority**: High
**Source**: memory / FR-3.1, FR-3.2
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/memory/

---

### TC-M-002 — All 8 memory tables have the three-column identity structure after migration

**Context**: All memory tables must carry the composite three-column identity: `platform_tenant_id`, `service_tenant_id`, `service_user_id`. This ensures every data record is correctly namespaced. Covers FR-3.3, FR-3.5.

**Scenario description**: After the Alembic migration, each of the 8 tables is inspected for the three required identity columns with the correct types and constraints.

**Steps**:
1. Apply Alembic migration to a test database
2. For each table (`semantic_memory`, `episodic_memory`, `procedural_memory`, `working_memory`, `task_context`, `plan_context`, `sessions`, `plans`): inspect columns

**Expected outcome**: Each table has `platform_tenant_id VARCHAR(64) NOT NULL`, `service_tenant_id VARCHAR(64) NOT NULL`, and `service_user_id VARCHAR(64)` (nullable where user scoping is optional). No UUID types or FK references to `tenants`/`users`.

**Technical details** (from construction design):
- ORM model file: `services/memory/src/memory_service/models/memory.py`
- Migration steps: Step 3 adds `platform_tenant_id VARCHAR(64) NOT NULL DEFAULT 'spt_00000000-0000-0000-0000-000000000000'`; Steps 4–5 add `service_tenant_id`/`service_user_id` (NULL); Steps 6–7 migrate existing `tenant_id`/`user_id` data; Step 8 drops old columns
- `SemanticMemory.user_id` was `String(255)` — renamed `service_user_id String(64)` and truncated to VARCHAR(64) in migration Step 7
- Updated unique constraints: `task_context → (platform_tenant_id, task_id)`, `plans → (platform_tenant_id, plan_id)`, `sessions → (platform_tenant_id, session_id)`, `working_memory → (plan_id, key)`, `plan_context → (plan_id)`
- Finding reference: business-rules.md BR-U4-05, domain-entities.md (Updated Entities, Identity Summary Table)

**Scope tag**: happy-path
**Priority**: High
**Source**: memory / FR-3.3, FR-3.5
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/memory/

---

### TC-M-003 — RLS policies enforce platform_tenant_id isolation (cross-tenant query returns 0 rows)

**Context**: This is the critical security test — RLS was previously configured but never enforced. With `get_tenanted_db` calling `set_config`, RLS must now actively prevent cross-tenant data access. Covers FR-3b.2, FR-3b.4.

**Scenario description**: Two rows are inserted into `semantic_memory` under different `platform_tenant_id` values. A query run with RLS session variable set to the first tenant returns only that tenant's row.

**Steps**:
1. Insert a semantic memory row with `platform_tenant_id="spt_tenant_1"`, `service_tenant_id="st1"`, `service_user_id="u1"`
2. Insert another row with `platform_tenant_id="spt_tenant_2"`, `service_tenant_id="st1"`, `service_user_id="u1"` (same service tenant, different platform tenant)
3. Call `set_config('app.platform_tenant_id', 'spt_tenant_1', true)` etc. and query `semantic_memory`

**Expected outcome**: Only the row with `platform_tenant_id="spt_tenant_1"` is returned. The second row is invisible due to RLS policy `semantic_memory_platform_rls`.

**Technical details** (from construction design):
- `get_tenanted_db` factory: `services/memory/src/memory_service/core/dependencies.py` — calls `await db.execute(text("SELECT set_config('app.platform_tenant_id', :v, true)"), {"v": platform_tenant_id})`; third argument `true` = transaction-scoped
- RLS policy name pattern: `{table_name}_platform_rls` (e.g., `semantic_memory_platform_rls`)
- Policy expression: `USING (platform_tenant_id = current_setting('app.platform_tenant_id', true))` — string equality, no `::UUID` cast
- Pattern source: nfr-design-patterns.md Pattern 2 (set_config Activation Lifecycle), Pattern 1 (RLS Policy Expression)
- Finding reference: business-rules.md BR-U4-03, nfr-design-patterns.md Pattern 1 & 2

**Scope tag**: happy-path
**Priority**: High
**Source**: memory / FR-3b.2, FR-3b.4
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/memory/

---

### TC-M-004 — Memory Service API stores and retrieves semantic memory with three-column identity

**Context**: End-to-end happy path for the Memory Service API after schema migration — store a semantic memory item and retrieve it using the two-tier tenant identity headers. Covers FR-3.8, FR-3.9.

**Scenario description**: A platform tenant's service stores a semantic memory item via the Memory API. It is retrieved using the same composite identity.

**Steps**:
1. Start the Memory Service with migrated schema and `TenancyMiddleware` registered
2. `POST /semantic-memory` with headers `X-Tenant-ID: spt_abc`, `X-Service-Tenant-ID: tenant_xyz`, `X-User-ID: user_123` and a valid memory payload
3. `GET /semantic-memory` with the same headers

**Expected outcome**: POST returns HTTP 201. GET returns HTTP 200 with the stored item. Response body includes `platform_tenant_id`, `service_tenant_id`, and `service_user_id` fields (BR-U4-11). No errors.

**Technical details** (from construction design):
- `TenancyMiddleware` source: `soorma_service_common.TenancyMiddleware` registered in `services/memory/src/memory_service/main.py`
- Header-to-state mapping: `X-Tenant-ID` → `request.state.platform_tenant_id`; `X-Service-Tenant-ID` → `request.state.service_tenant_id`; `X-User-ID` → `request.state.service_user_id`
- Semantic memory router: `services/memory/src/memory_service/api/v1/semantic.py`
- Response DTO (BR-U4-11): `SemanticMemoryResponse` MUST expose `platform_tenant_id`, `service_tenant_id`, `service_user_id`; legacy `tenant_id` field MUST NOT appear
- Finding reference: business-rules.md BR-U4-09, BR-U4-11, domain-entities.md (SemanticMemory identity columns)

**Scope tag**: happy-path
**Priority**: High
**Source**: memory / FR-3.8, FR-3.9
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/memory/

---

### TC-M-005 — MemoryDataDeletion.delete_by_platform_tenant deletes all rows for a platform tenant

**Context**: The GDPR deletion interface must delete all memory records across all tables for a given platform tenant in a single transaction. Covers FR-4.1, FR-4.2.

**Scenario description**: Rows are inserted across multiple memory tables under a specific `platform_tenant_id`. The deletion method is called and all rows disappear.

**Steps**:
1. Insert test rows into `semantic_memory`, `episodic_memory`, `task_context` under `platform_tenant_id="spt_delete_me"`
2. Call `MemoryDataDeletion.delete_by_platform_tenant(platform_tenant_id="spt_delete_me")`
3. Query all three tables for rows with `platform_tenant_id="spt_delete_me"`

**Expected outcome**: All three queries return zero rows for `"spt_delete_me"`. Rows under other `platform_tenant_id` values are unaffected.

**Technical details** (from construction design):
- Class: `MemoryDataDeletion` in `services/memory/src/memory_service/services/data_deletion.py`
- Parent class: `PlatformTenantDataDeletion` from `soorma_service_common`
- Covered tables (BR-U4-06, exactly 6): `semantic_memory`, `episodic_memory`, `procedural_memory`, `working_memory`, `task_context`, `plan_context`
- NOT covered: `plans`, `sessions` (lifecycle management — see TC-M-012 for explicit boundary test)
- Finding reference: business-rules.md BR-U4-06, domain-entities.md (New Entity: MemoryDataDeletion)

**Scope tag**: happy-path
**Priority**: High
**Source**: memory / FR-4.1, FR-4.2
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/memory/

---

### TC-M-006 — MemoryDataDeletion.delete_by_service_tenant scoped within platform tenant

**Context**: Service-tenant deletion must be scoped — only delete rows for the given `(platform_tenant_id, service_tenant_id)` combination; rows for the same service tenant under a different platform tenant must not be touched. Covers FR-4.1, NFR-1.3.

**Scenario description**: Rows exist for the same `service_tenant_id` under two different `platform_tenant_id` values. Deletion is called for one platform tenant.

**Steps**:
1. Insert rows: `(spt_1, st1, u1)` and `(spt_2, st1, u1)` into `semantic_memory`
2. Call `delete_by_service_tenant(platform_tenant_id="spt_1", service_tenant_id="st1")`
3. Query both inserts

**Expected outcome**: Row for `(spt_1, st1, u1)` is deleted. Row for `(spt_2, st1, u1)` remains.

**Technical details** (from construction design):
- Method signature: `delete_by_service_tenant(db: AsyncSession, platform_tenant_id: str, service_tenant_id: str) -> int`
- WHERE pattern (Pattern 3): `Model.platform_tenant_id == platform_tenant_id AND Model.service_tenant_id == service_tenant_id`
- Pattern source: nfr-design-patterns.md Pattern 3 (Composite Key Enforcement — Defence-in-Depth)
- Finding reference: business-rules.md BR-U4-02, nfr-design-patterns.md Pattern 3

**Scope tag**: happy-path
**Priority**: High
**Source**: memory / FR-4.1, NFR-1.3
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/memory/

---

### TC-M-007 — Memory Service uses shared TenancyMiddleware from soorma-service-common

**Context**: The local `TenancyMiddleware` implementation in the Memory Service must be removed and replaced with the shared one. Covers FR-3.6.

**Scenario description**: The Memory Service codebase is inspected for local middleware and for import from `soorma_service_common`.

**Steps**:
1. Check whether `memory_service/core/middleware.py` (or equivalent local file) exists and contains a `TenancyMiddleware` class
2. Inspect `memory_service/main.py` for middleware registration

**Expected outcome**: File `services/memory/src/memory_service/core/middleware.py` does not exist (deleted, not emptied). `main.py` imports `TenancyMiddleware` from `soorma_service_common` and registers it via `app.add_middleware(TenancyMiddleware)`. No local `TenancyMiddleware` class exists anywhere in the `memory_service` package.

**Technical details** (from construction design):
- Deleted file (BR-U4-09): `services/memory/src/memory_service/core/middleware.py` — file is removed entirely, not just emptied
- New import in `main.py`: `from soorma_service_common import TenancyMiddleware` (or `from soorma_service_common.middleware import TenancyMiddleware`)
- Registration: `app.add_middleware(TenancyMiddleware)` in `services/memory/src/memory_service/main.py`
- Finding reference: business-rules.md BR-U4-09

**Scope tag**: happy-path
**Priority**: High
**Source**: memory / FR-3.6
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/memory/

---

### TC-M-008 — RLS policy rebuilds use string comparison (no ::UUID cast)

**Context**: The old RLS policies used `::UUID` cast, which will fail after the VARCHAR migration. The new policies must use string comparison. Covers FR-3b.1, FR-3b.2.

**Scenario description**: The PostgreSQL `pg_policies` or migration script is inspected for the new policy expressions.

**Steps**:
1. Apply the migration
2. Query `pg_policies` for policies on the 8 memory tables
3. Inspect the `qual` (using) expression for each policy

**Expected outcome**: 8 policies exist (one per table), named `{table_name}_platform_rls`. No `::uuid` cast in any policy expression. Each `qual` contains `platform_tenant_id = current_setting('app.platform_tenant_id', true)` (string equality, `missing_ok=true`). `rowsecurity` and `forcersls` are both `true` on each table.

**Technical details** (from construction design):
- Policy name pattern: `{table_name}_platform_rls` (e.g., `semantic_memory_platform_rls`, `episodic_memory_platform_rls`, …)
- Full SQL (Pattern 1): `USING (platform_tenant_id = current_setting('app.platform_tenant_id', true))` — `missing_ok=true` prevents errors when session variable unset
- `FORCE ROW LEVEL SECURITY` applied via `ALTER TABLE {table} FORCE ROW LEVEL SECURITY` — prevents superuser/table-owner bypass in test environments
- Migration step 13 creates policies; step 14 enables `ENABLE ROW LEVEL SECURITY` + `FORCE ROW LEVEL SECURITY` on all 8 tables
- Finding reference: nfr-design-patterns.md Pattern 1 (RLS Policy Expression), business-rules.md BR-U4-04

**Scope tag**: happy-path
**Priority**: High
**Source**: memory / FR-3b.1, FR-3b.2
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/memory/

---

### TC-M-009 — Memory API query without RLS session variables returns no rows

**Context**: Negative/security test: if `set_config` is NOT called before a query (e.g., a misconfigured path that bypasses `get_tenanted_db`), RLS must prevent data leakage by returning zero rows. Covers FR-3b.2, FR-3b.4 (security pairing).

**Scenario description**: A raw database query against a memory table is executed WITHOUT calling `set_config` first (simulating a hypothetical code path that bypasses the dependency).

**Steps**:
1. Obtain a DB connection without calling `set_config`
2. Query `semantic_memory` for any rows

**Expected outcome**: Zero rows returned. The RLS policy evaluates `platform_tenant_id = current_setting('app.platform_tenant_id', true)` where `current_setting(...)` returns `''` (empty string, `missing_ok=true`); no stored `platform_tenant_id` equals `''`, so all rows are filtered.

**Technical details** (from construction design):
- `current_setting('app.platform_tenant_id', true)` — `missing_ok=true` (3rd arg) returns `''` instead of raising a PostgreSQL error when session variable is absent
- `''` matches no stored `platform_tenant_id` (all values are `spt_`-prefixed; default is `'spt_00000000-0000-0000-0000-000000000000'`)
- Test implementation: obtain `AsyncSession` directly from `create_async_engine(settings.database_url)` instead of via the `get_tenanted_db` factory — do NOT call `set_config` or `set_config_for_session`
- Pattern source: nfr-design-patterns.md Pattern 1 (RLS Policy Expression — `missing_ok` semantics)
- Finding reference: business-rules.md BR-U4-03, nfr-design-patterns.md Pattern 1

**Scope tag**: happy-path-negative
**Priority**: High
**Source**: memory / FR-3b.2, FR-3b.4
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/memory/

---

### TC-M-010 — Memory API rejects request with missing service tenant for user-scoped operations

**Context**: Negative case: some memory operations require `service_tenant_id`. When it is absent and the operation requires it, the API should return a clear validation error. Covers FR-3.8, FR-3.9.

**Scenario description**: A `POST /semantic-memory` request is sent with `X-Tenant-ID` and `X-User-ID` headers but no `X-Service-Tenant-ID`.

**Steps**:
1. Send `POST /semantic-memory` with `X-Tenant-ID: spt_abc`, `X-User-ID: user_123` — omit `X-Service-Tenant-ID`
2. Observe the response

**Expected outcome**: HTTP 422 (or 400) with a clear error message indicating `service_tenant_id` is required for user-scoped operations.

**Technical details** (from construction design):
- `TenancyMiddleware` behaviour: when `X-Service-Tenant-ID` header is absent, `request.state.service_tenant_id` is set to `""` (empty string)
- BR-U4-02 rule: any operation scoped by `service_user_id` MUST also receive a non-empty `service_tenant_id`; `service_user_id` values are not globally unique — only unique within `(platform_tenant_id, service_tenant_id)`
- Error type: HTTP 422 (Pydantic validation) if enforced at model level, or HTTP 400 if enforced in the route handler — test must accept either
- Finding reference: business-rules.md BR-U4-02

**Scope tag**: happy-path-negative
**Priority**: High
**Source**: memory / FR-3.8
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/memory/

---

### TC-M-011 — MemoryDataDeletion does not delete rows for wrong service user when scoped to service_user

**Context**: Negative/boundary case for `delete_by_service_user` — only delete the exact `(platform_tenant_id, service_tenant_id, service_user_id)` triplet. Covers FR-4.1, NFR-1.3.

**Scenario description**: Two rows exist for the same platform/service tenant but different users. Deletion for one user must leave the other untouched.

**Steps**:
1. Insert rows: `(spt_1, st1, user_A)` and `(spt_1, st1, user_B)` into `working_memory`
2. Call `delete_by_service_user(platform_tenant_id="spt_1", service_tenant_id="st1", service_user_id="user_A")`
3. Query both rows

**Expected outcome**: Row for `user_A` is deleted. Row for `user_B` remains.

**Technical details** (from construction design):
- Method signature: `delete_by_service_user(db: AsyncSession, platform_tenant_id: str, service_tenant_id: str, service_user_id: str) -> int`
- WHERE pattern (Pattern 3): `Model.platform_tenant_id == platform_tenant_id AND Model.service_tenant_id == service_tenant_id AND Model.service_user_id == service_user_id`
- Table used in test: `working_memory` (all 6 covered tables apply the same composite WHERE pattern)
- Pattern source: nfr-design-patterns.md Pattern 3 (Composite Key Enforcement)
- Finding reference: business-rules.md BR-U4-02, nfr-design-patterns.md Pattern 3

**Scope tag**: happy-path-negative
**Priority**: High
**Source**: memory / FR-4.1, NFR-1.3
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/memory/

---

### TC-M-012 — MemoryDataDeletion does not delete plans or sessions rows

**Context**: BR-U4-06 specifies that `MemoryDataDeletion` covers exactly 6 tables and explicitly excludes `plans` and `sessions` (lifecycle management tables whose lifecycle is tied to active workflows, not GDPR erasure). This boundary test validates the exclusion is hard-coded and that lifecycle data cannot be accidentally deleted via the GDPR interface. Covers BR-U4-06.

**Scenario description**: Rows are inserted into `plans` and `sessions` tables alongside data in a covered table, all under the same platform tenant. Deletion is called. Only the covered-table rows are deleted; `plans` and `sessions` rows are untouched.

**Steps**:
1. Insert a row into `plans` with `platform_tenant_id="spt_delete_me"` and a row into `sessions` with the same `platform_tenant_id`
2. Insert a row into `semantic_memory` with `platform_tenant_id="spt_delete_me"` (control — covered table)
3. Call `MemoryDataDeletion.delete_by_platform_tenant(db, platform_tenant_id="spt_delete_me")`
4. Query `semantic_memory`, `plans`, and `sessions` for rows with `platform_tenant_id="spt_delete_me"`

**Expected outcome**: `semantic_memory` returns zero rows for `"spt_delete_me"` (deleted). `plans` and `sessions` still contain their inserted rows (not deleted by `MemoryDataDeletion`).

**Technical details** (from construction design):
- `MemoryDataDeletion` models list: `SemanticMemory, EpisodicMemory, ProceduralMemory, WorkingMemory, TaskContext, PlanContext` — exactly 6 (BR-U4-06)
- `Plan` and `Session` are NOT in the deletion list
- Source: `services/memory/src/memory_service/services/data_deletion.py`
- Finding reference: business-rules.md BR-U4-06, domain-entities.md (Identity Summary Table)

**Scope tag**: happy-path
**Priority**: High
**Source**: memory / BR-U4-06
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/memory/

---

### TC-M-013 — Admin deletion endpoint activates RLS session before bulk delete

**Context**: The admin HTTP endpoint for platform-tenant data deletion bypasses the standard `get_tenanted_db` dependency (driven by `TenancyMiddleware` headers). Instead it calls `set_config_for_session(db, platform_tenant_id, "", "")` from `soorma_service_common` directly before delegating to `MemoryDataDeletion`. This validates the admin-specific RLS activation pattern (Pattern 4). Covers BR-U4-08, Pattern 4.

**Scenario description**: An admin API request triggers bulk deletion for a platform tenant. The endpoint activates the correct RLS scope manually and all covered-table rows are removed.

**Steps**:
1. Insert rows into `semantic_memory` and `episodic_memory` under `platform_tenant_id="spt_admin_delete"`
2. Call the admin deletion endpoint (e.g., `DELETE /admin/platform-tenants/spt_admin_delete/data`) or invoke the admin service method directly
3. Observe the response status and returned rows-deleted count
4. Query `semantic_memory` and `episodic_memory` for `platform_tenant_id="spt_admin_delete"`

**Expected outcome**: HTTP 200 with a total rows-deleted count greater than zero. All inserted rows for `"spt_admin_delete"` are deleted. The endpoint uses `set_config_for_session` from `soorma_service_common` (not `get_tenanted_db`) to activate RLS scope.

**Technical details** (from construction design):
- Admin router: `services/memory/src/memory_service/api/v1/admin.py`
- Uses `Depends(get_db)` (bare — no RLS activation via `get_tenanted_db`; BR-U4-08)
- Activation call: `await set_config_for_session(db, platform_tenant_id, "", "")` imported from `soorma_service_common` — called before any deletion query
- Deletion delegate: `await MemoryDataDeletion().delete_by_platform_tenant(db, platform_tenant_id)`
- Pattern source: nfr-design-patterns.md Pattern 4 (Admin Deletion RLS Bypass)
- Finding reference: business-rules.md BR-U4-08, nfr-design-patterns.md Pattern 4

**Scope tag**: happy-path
**Priority**: High
**Source**: memory / BR-U4-08, Pattern 4
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/memory/
