# Business Rules — services/registry (U3)
## Initiative: Multi-Tenancy Model Implementation
**Date**: 2026-03-22

---

## Identity Rules

**BR-R01**: `platform_tenant_id` is an opaque string — Registry MUST NOT validate it as a UUID or any other specific format.

**BR-R02**: `platform_tenant_id` MUST be sourced exclusively from `request.state.platform_tenant_id`, populated by `TenancyMiddleware`. Route handlers MUST NOT read the `X-Tenant-ID` header directly.

**BR-R03**: When `X-Tenant-ID` is absent or empty, `TenancyMiddleware` defaults `platform_tenant_id` to `DEFAULT_PLATFORM_TENANT_ID` from `soorma_common.tenancy`. Registry route handlers receive this default transparently — no special handling required.

**BR-R04**: Registry is **platform-tenant scoped only**. `service_tenant_id` and `service_user_id` are NOT used by Registry. The middleware populates these on `request.state` but they MUST NOT be injected into any Registry route handler or passed to any service/CRUD function.

**BR-R05**: `get_developer_tenant_id()` MUST be removed entirely from `api/dependencies.py`. No code in the Registry service may import or call it after this migration.

---

## Database Rules

> **Design decision note (deviation from inception spec)**: The original inception spec (`components.md` C3) stated no RLS for Registry. This was revised during functional design to add RLS for SOC2 auditability — a PostgreSQL-level control is categorically stronger evidence than application-layer WHERE conventions, and the incremental cost is small. See `business-logic-model.md` for the full rationale.

**BR-R06**: Registry MUST use `get_tenanted_db` (from `soorma-service-common`) in all route handlers that access `agents`, `events`, or `payload_schemas`. All such route handlers MUST declare `db: AsyncSession = Depends(get_tenanted_db)`, NOT bare `Depends(get_db)`.

**BR-R07**: The Alembic migration MUST enable RLS and create a `platform_tenant_id` isolation policy on all three Registry tables. The `set_config` activation is handled by `get_tenanted_db` — no additional `set_config` calls are needed in Registry code.

**BR-R07a**: RLS policies MUST use `FORCE ROW LEVEL SECURITY` so that the table owner / superuser is also subject to the policy during application queries. Migration scripts and Alembic itself run as a privileged user that bypasses RLS — this is intentional (migrations need to see all rows). Application route handlers run under the application DB user which is subject to `FORCE ROW LEVEL SECURITY`.

**BR-R07b**: Integration test MUST include a cross-tenant isolation assertion: a query executed with `platform_tenant_id=tenant-A` MUST return zero rows that belong to `tenant-B`. This is the primary SOC2 evidence artefact for Registry tenant isolation.

**BR-R08**: `DATABASE_URL` is the single configuration point for the database connection. `IS_LOCAL_TESTING`, `SYNC_DATABASE_URL`, `DB_INSTANCE_CONNECTION_NAME`, `DB_USER`, `DB_NAME`, and `DB_PASS_PATH` MUST be removed from `Settings`.

**BR-R09**: `create_db_engine()` MUST use `settings.DATABASE_URL` directly — no driver branching, no URL assembly.

---

## Migration Rules

**BR-R10**: The Alembic migration MUST rename `tenant_id` → `platform_tenant_id` on all three tables: `agents`, `events`, `payload_schemas`.

**BR-R11**: The migration MUST change the column type from `UUID` to `VARCHAR(64)` using a `USING <column>::text` cast.

**BR-R12**: Composite unique constraints that include the `tenant_id` column MUST be dropped before the rename and recreated with `platform_tenant_id` after the rename. Affected constraints:
- `agents`: `(agent_id, tenant_id)` → `(agent_id, platform_tenant_id)`
- `events`: `(event_name, tenant_id)` → `(event_name, platform_tenant_id)`
- `payload_schemas`: `(schema_name, version, tenant_id)` → `(schema_name, version, platform_tenant_id)`

**BR-R13**: The migration downgrade function MUST be a no-op (`pass`). Pre-release — no production data exists. Rollback handled via new forward migration if ever needed.

**BR-R14**: The migration MUST operate on PostgreSQL only. No SQLite compatibility shims in the migration file.

---

## ORM Rules

**BR-R15**: All three ORM models (`AgentTable`, `EventTable`, `PayloadSchemaTable`) MUST replace:
- Column name: `tenant_id` → `platform_tenant_id`
- Column type: `Uuid(as_uuid=True, native_uuid=True)` → `String(64)`
- Python type annotation: `Mapped[UUID]` → `Mapped[str]`
- Import: remove `from uuid import UUID` if no longer used elsewhere in the model file

**BR-R16**: CRUD method signatures MUST replace `developer_tenant_id: UUID` with `platform_tenant_id: str` as the parameter name and type. All internal assignments (`tenant_id=developer_tenant_id`) MUST become (`platform_tenant_id=platform_tenant_id`).

---

## Dependency Rules

**BR-R17**: `pyproject.toml` MUST add `soorma-service-common` as a main dependency.

**BR-R18**: `aiosqlite` MUST be moved from main dependencies to `[project.optional-dependencies] dev`. It MUST NOT be installed in production images.

---

## Test Rules

**BR-R19**: `conftest.py` MUST remove `os.environ["IS_LOCAL_TESTING"] = "true"` — this env var no longer exists.

**BR-R20**: `conftest.py` MUST keep `os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_registry.db"` — this is how SQLite is selected post-simplification.

**BR-R21**: `TEST_TENANT_ID` MUST be changed from `UUID("00000000-0000-0000-0000-000000000000")` to the string `"spt_00000000-0000-0000-0000-000000000000"`. All test header values and assertion strings using the old UUID sentinel MUST be updated to the new string sentinel.

**BR-R22**: Test client fixture MUST send `{"X-Tenant-ID": TEST_TENANT_ID}` where `TEST_TENANT_ID` is a plain string (no `str()` conversion needed).
