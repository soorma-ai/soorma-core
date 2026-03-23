# Business Rules — U4: services/memory
## Initiative: Multi-Tenancy Model Implementation
**Date**: 2026-03-23

---

## BR-U4-01: platform_tenant_id is ALWAYS required — never None or empty string

**Component**: All CRUD/service layer functions, all API endpoints  
**Rule**: Every query on any of the 8 memory tables MUST include `platform_tenant_id` as a WHERE condition. Functions that accept `platform_tenant_id` MUST validate it is non-empty before executing any query.  
**Rationale**: `platform_tenant_id` is the outer scope for all data. A missing or empty value would return data across all platform tenants — a catastrophic cross-tenant data leakage.  
**Enforcement**: API routes validate via `TenancyMiddleware` (falls back to `DEFAULT_PLATFORM_TENANT_ID`, never None). Service functions include assertion: `assert platform_tenant_id, "platform_tenant_id is required"`. RLS policies provide defence-in-depth (empty string matches no rows).

---

## BR-U4-02: Composite key — service_tenant_id required when service_user_id is used

**Component**: All CRUD/service layer functions, deletion logic  
**Rule**: Any operation that filters or scopes by `service_user_id` MUST also specify `service_tenant_id`. A user ID without a service tenant scope is ambiguous (user IDs are unique only within a service tenant's namespace within a platform tenant).  
**Rationale**: `service_user_id` values are NOT globally unique — they are only unique within `(platform_tenant_id, service_tenant_id)`. Filtering by `service_user_id` alone could match users from different service tenants.  
**Enforcement**: `delete_by_service_user()` requires `service_tenant_id` as a parameter. API endpoints that accept `X-User-ID` also require `X-Service-Tenant-ID` (TC-M-010).

---

## BR-U4-03: RLS policy enforces platform_tenant_id — app code enforces full composite key

**Component**: PostgreSQL RLS policies, service/CRUD layer  
**Rule**: RLS policies enforce `platform_tenant_id` isolation only. Application code (service and CRUD layers) MUST also enforce `platform_tenant_id` explicitly in WHERE clauses, plus `service_tenant_id` and `service_user_id` as applicable. Platform tenant isolation must NOT rely solely on RLS.  
**Rationale**: Defence in depth. RLS is a database-level backstop; application code is the primary enforcement layer. Both are required.  
**Enforcement**: Code review; every CRUD query includes `Model.platform_tenant_id == platform_tenant_id` in WHERE.

---

## BR-U4-04: Old RLS policies must be dropped BEFORE schema migration

**Component**: Alembic migration `008_multi_tenancy_three_column_identity.py`  
**Rule**: All existing RLS policies that reference `tenant_id::UUID` or `user_id::UUID` MUST be dropped as the first step in the migration, BEFORE any column changes. Adding new columns while old policies exist risks FK-based policies breaking.  
**Rationale**: Old policies use `::UUID` cast which will become invalid once `tenant_id` changes to `VARCHAR(64)`. Attempting to evaluate old policies against new schema causes PostgreSQL errors.  
**Enforcement**: Migration step 1 drops policies; step 13 recreates them.

---

## BR-U4-05: String identity columns must be VARCHAR(64) — not Text or String(255)

**Component**: ORM models, Alembic migration  
**Rule**: All three identity columns (`platform_tenant_id`, `service_tenant_id`, `service_user_id`) MUST be `VARCHAR(64)` / `String(64)` — not `Text`, `String(255)`, or other wider types.  
**Rationale**: The two-tier identity model specification defines max 64 characters for all three dimensions. Using `Text` would allow unbounded values that violate the spec and cannot be efficiently indexed.  
**Enforcement**: ORM models use `String(64)`. Migration uses `VARCHAR(64)`. Any data truncated during migration for `SemanticMemory.user_id` (was String(255)) is documented.

---

## BR-U4-06: MemoryDataDeletion covers exactly 6 tables — not 8

**Component**: `MemoryDataDeletion`  
**Rule**: `MemoryDataDeletion` covers: `semantic_memory`, `episodic_memory`, `procedural_memory`, `working_memory`, `task_context`, `plan_context`. It MUST NOT include `plans` or `sessions`.  
**Rationale**: `plans` and `sessions` are lifecycle management tables — their lifecycle is tied to business processes (plan execution, session management), not GDPR erasure. Deleting them via GDPR deletion would break active workflows.  
**Exception**: The admin deletion API provides separate endpoints for plans/sessions deletion if operationally required, but these are not part of `MemoryDataDeletion`.  
**Enforcement**: `MemoryDataDeletion._TABLES_6` lists exactly these 6 models. Tests verify counts for all 6; tests verify `plans` and `sessions` tables are NOT deleted by `delete_by_platform_tenant()`.

---

## BR-U4-07: Migration must default existing rows to DEFAULT_PLATFORM_TENANT_ID

**Component**: Alembic migration  
**Rule**: When adding `platform_tenant_id VARCHAR(64) NOT NULL` to existing tables, existing rows MUST receive the default value `'spt_00000000-0000-0000-0000-000000000000'`. Using a database-level DEFAULT clause is acceptable.  
**Rationale**: Migration must not fail if target tables contain existing rows (pre-production system; some fixture data may exist). The single-platform-tenant default is the correct value for all existing data.  
**Enforcement**: Migration uses `ALTER TABLE ... ADD COLUMN platform_tenant_id VARCHAR(64) NOT NULL DEFAULT 'spt_00000000-0000-0000-0000-000000000000'`.

---

## BR-U4-08: Deletion API endpoints use bare get_db (no RLS activation required)

**Component**: `memory_service/api/v1/admin.py`  
**Rule**: The admin deletion endpoints use `Depends(get_db)` directly, NOT `Depends(get_tenanted_db)`. They do not activate RLS session variables before executing deletes.  
**Rationale**: Admin deletions are by design cross-tenant (the deletion operation IS the erasure of a tenant's data). RLS would block the deletion from succeeding because it enforces isolation. Admin operations must bypass RLS (owner/superuser connection or RLS-exempted role).  
**Security note**: These endpoints must be protected by a separate admin authentication mechanism in production (out of scope for this unit — noted as future work). For now, they are internal endpoints accessible only within the cluster network.

---

## BR-U4-09: Local TenancyMiddleware MUST be removed — no two middleware instances

**Component**: `memory_service/core/middleware.py`, `memory_service/main.py`  
**Rule**: After registering `soorma_service_common.TenancyMiddleware`, the local `TenancyMiddleware` class in `memory_service/core/middleware.py` MUST be deleted. The file itself should be removed or reduced to helper functions only (none remain after this migration).  
**Rationale**: Two middleware instances processing the same request headers would overwrite `request.state` values unpredictably. Only one TenancyMiddleware can be active.  
**Enforcement**: `middleware.py` file is deleted; `main.py` imports only from `soorma_service_common`.

---

## BR-U4-10: settings.is_local_testing must be removed

**Component**: `memory_service/core/config.py`, all callers  
**Rule**: The `is_local_testing` flag (and any code paths gated on it) MUST be removed. Memory Service is PostgreSQL-only — there is no SQLite fallback path to gate on.  
**Rationale**: `is_local_testing` existed to support Registry's SQLite fallback, which was copied to memory service inconsistently. Memory Service never had a working SQLite path. Removing it aligns the codebase with the actual behaviour.  
**Enforcement**: Remove flag from `Settings`. Update `main.py` lifespan log that references it. Tests update to not reference this setting.

---

## BR-U4-11: Response DTOs must reflect three-column identity

**Component**: `soorma_common.models` response models  
**Rule**: Response models (e.g., `SemanticMemoryResponse`, `WorkingMemoryResponse`) MUST expose `platform_tenant_id`, `service_tenant_id`, and `service_user_id` fields. The legacy `tenant_id` field MUST NOT appear in API responses.  
**Rationale**: API response consistency — clients should see the same identity model as the storage model. Breaking from the three-column model in responses would create confusion and bugs in SDK client code.  
**Enforcement**: DTO field names align with ORM column names. Service layer maps ORM → DTO using new field names.
