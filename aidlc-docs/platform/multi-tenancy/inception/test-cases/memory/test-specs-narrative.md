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

**Expected outcome**: Only the row with `platform_tenant_id="spt_tenant_1"` is returned. The second row is invisible due to RLS enforcement.

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

**Expected outcome**: POST returns HTTP 201. GET returns the stored item. No errors.

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

**Expected outcome**: All queries return zero rows. Rows under other `platform_tenant_id` values are unaffected.

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

**Expected outcome**: No local `TenancyMiddleware` class exists. `main.py` imports and registers `TenancyMiddleware` from `soorma_service_common`.

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

**Expected outcome**: No `::UUID` cast appears in any policy expression. All `using` clauses use string equality comparison: `platform_tenant_id = current_setting('app.platform_tenant_id', true)`.

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

**Expected outcome**: Zero rows returned (RLS with missing session variables filters everything out, or `current_setting` returns an empty string that matches no real data).

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

**Expected outcome**: HTTP 400 or 422 with a clear error message indicating `service_tenant_id` is required for this operation.

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

**Scope tag**: happy-path-negative
**Priority**: High
**Source**: memory / FR-4.1, NFR-1.3
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/memory/
