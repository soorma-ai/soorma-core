# Code Generation Plan — registry (U3)
## Initiative: Multi-Tenancy Model Implementation
**Unit**: U3 — `services/registry`
**Wave**: 2 (parallel with U2)
**Change Type**: Moderate
**Date**: 2026-03-22

---

## Unit Context

**Purpose**: Migrate `services/registry` from UUID-based tenant identity to the platform-wide `VARCHAR(64)` string model. Wire `TenancyMiddleware` and `get_tenanted_db` from `soorma-service-common`. Add PostgreSQL RLS for SOC2 auditability.

**Dependencies**: U1 (soorma-common, complete), U2 (soorma-service-common, complete)

**Design artifacts**: `construction/registry/functional-design/`  
**Requirement traceability**: FR-2.1–FR-2.9, BR-R01–BR-R22

**Test sentinel (post-migration)**: `DEFAULT_PLATFORM_TENANT_ID = "spt_00000000-0000-0000-0000-000000000000"`

---

## Touch List (files to modify or create)

| # | File | Action |
|---|------|--------|
| 1 | `services/registry/pyproject.toml` | Add `soorma-service-common`; move `aiosqlite` to dev deps |
| 2 | `services/registry/src/registry_service/core/config.py` | Remove `IS_LOCAL_TESTING`, `SYNC_DATABASE_URL`, Cloud SQL fields |
| 3 | `services/registry/src/registry_service/core/database.py` | Simplify `create_db_engine()` to single `DATABASE_URL` path |
| 4 | `services/registry/src/registry_service/api/dependencies.py` | Replace with re-export of `get_platform_tenant_id` from `soorma-service-common` |
| 5 | `services/registry/src/registry_service/main.py` | Add `TenancyMiddleware`; remove `IS_LOCAL_TESTING` log reference |
| 6 | `services/registry/src/registry_service/models/agent.py` | `tenant_id: Mapped[UUID]` → `platform_tenant_id: Mapped[str]` with `String(64)` |
| 7 | `services/registry/src/registry_service/models/event.py` | Same ORM rename+retype |
| 8 | `services/registry/src/registry_service/models/schema.py` | Same ORM rename+retype |
| 9 | `services/registry/src/registry_service/crud/agents.py` | `developer_tenant_id: UUID` → `platform_tenant_id: str` throughout |
| 10 | `services/registry/src/registry_service/crud/events.py` | Same CRUD signature rename+retype |
| 11 | `services/registry/src/registry_service/crud/schemas.py` | Same CRUD signature rename+retype |
| 12 | `services/registry/src/registry_service/services/agent_service.py` | `developer_tenant_id: UUID` → `platform_tenant_id: str` throughout |
| 13 | `services/registry/src/registry_service/services/event_service.py` | Same service layer rename+retype |
| 14 | `services/registry/src/registry_service/services/schema_service.py` | Same service layer rename+retype |
| 15 | `services/registry/src/registry_service/api/v1/agents.py` | `Depends(get_db)` → `Depends(get_tenanted_db)`; `get_developer_tenant_id` → `get_platform_tenant_id`; `UUID` → `str` |
| 16 | `services/registry/src/registry_service/api/v1/events.py` | Same API route changes |
| 17 | `services/registry/src/registry_service/api/v1/schemas.py` | Same API route changes |
| 18 | `services/registry/alembic/versions/004_platform_tenant_id.py` | NEW — rename+retype+RLS migration |
| 19 | `services/registry/tests/conftest.py` | Remove `IS_LOCAL_TESTING`/`SYNC_DATABASE_URL` env vars; update sentinel to string format |
| 20 | All test files | Update `TEST_TENANT_ID` / `developer_tenant_id` UUID references to `platform_tenant_id` string |
| 21 | `aidlc-docs/platform/multi-tenancy/construction/registry/code/code-summary.md` | NEW — completion summary |

---

## Steps

### Step 1 — pyproject.toml: add soorma-service-common; move aiosqlite to dev deps
- [x] Add `"soorma-service-common"` to `[project] dependencies`
- [x] Remove `"aiosqlite>=0.19.0"` from main dependencies
- [x] Add `"aiosqlite>=0.19.0"` to `[project.optional-dependencies] dev`

### Step 2 — core/config.py: remove IS_LOCAL_TESTING and Cloud SQL fields
- [x] Remove `IS_LOCAL_TESTING: bool = True`
- [x] Remove `SYNC_DATABASE_URL: str = "sqlite:///./registry.db"`
- [x] Remove `DB_INSTANCE_CONNECTION_NAME`, `DB_USER`, `DB_NAME`, `DB_PASS_PATH` fields
- [x] Keep `DATABASE_URL: str = "postgresql+asyncpg://localhost/registry"` (update default from SQLite to PostgreSQL)
- [x] Remove unused imports (`Optional` if no longer needed; `List` for Cloud SQL settings; `Path` if only used for Cloud SQL)
- [x] Remove `check_required_settings` function (only caller was database.py Cloud SQL path)

### Step 3 — core/database.py: simplify engine creation
- [x] Replace entire `create_db_url()` function with single `create_db_engine()` that calls `create_async_engine(settings.DATABASE_URL, poolclass=NullPool, future=True, echo=False)`
- [x] Remove import of `URL` from sqlalchemy since URL assembly is gone
- [x] Remove import of `check_required_settings` from config
- [x] Keep `get_db` for use by conftest/tests (tests override `DATABASE_URL` env var to SQLite)

### Step 4 — api/dependencies.py: create get_tenanted_db via factory; re-export get_platform_tenant_id
- [x] Remove `get_developer_tenant_id` function entirely
- [x] Import `create_get_tenanted_db, get_platform_tenant_id` from `soorma_service_common`
- [x] Import `get_db` from `..core.database`
- [x] Call `get_tenanted_db = create_get_tenanted_db(get_db)` to bind the registry's session factory
- [x] Export both `get_platform_tenant_id` (re-export) and `get_tenanted_db` (bound instance)
- [x] Update module docstring: note `get_tenanted_db` activates RLS via `set_config` x3 on PostgreSQL

### Step 5 — main.py: add TenancyMiddleware; clean IS_LOCAL_TESTING references
- [x] Add import: `from soorma_service_common.middleware import TenancyMiddleware`
- [x] Add `app.add_middleware(TenancyMiddleware)` after CORS middleware
- [x] Remove `IS_LOCAL_TESTING` reference in logging level (use `settings.IS_PROD` or hardcode `logging.INFO`)

### Step 6 — models/agent.py: rename tenant_id → platform_tenant_id with String(64)
- [x] Remove `from uuid import UUID` (no longer used)
- [x] Remove `Uuid` from the sqlalchemy imports
- [x] Add `String` to imports (already present) — confirm `String` is imported
- [x] Rename column: `tenant_id: Mapped[UUID]` → `platform_tenant_id: Mapped[str]`
- [x] Change column type: `Uuid(as_uuid=True, native_uuid=True)` → `String(64)`

### Step 7 — models/event.py: same ORM changes
- [x] Same changes as Step 6 applied to `EventTable.tenant_id`

### Step 8 — models/schema.py: same ORM changes
- [x] Same changes as Step 6 applied to `PayloadSchemaTable.tenant_id` (or `SchemaTable`)

### Step 9 — crud/agents.py: developer_tenant_id: UUID → platform_tenant_id: str
- [x] Remove `from uuid import UUID`
- [x] Update `create_agent` signature: `developer_tenant_id: UUID` → `platform_tenant_id: str`
- [x] Update assignment: `tenant_id=developer_tenant_id` → `platform_tenant_id=platform_tenant_id`
- [x] Update all other methods in `AgentCRUD` that accept `developer_tenant_id: UUID` — same rename+retype
- [x] Update WHERE clauses: `AgentTable.tenant_id == developer_tenant_id` → `AgentTable.platform_tenant_id == platform_tenant_id`

### Step 10 — crud/events.py: same CRUD changes
- [x] Same changes as Step 9 applied to `EventCRUD` methods

### Step 11 — crud/schemas.py: same CRUD changes
- [x] Same changes as Step 9 applied to schema CRUD class

### Step 12 — services/agent_service.py: propagate rename through service layer
- [x] `developer_tenant_id: UUID` → `platform_tenant_id: str` in all method signatures
- [x] Remove `from uuid import UUID` if no longer used
- [x] Update all downstream CRUD calls to pass `platform_tenant_id=platform_tenant_id`

### Step 13 — services/event_service.py: same service layer changes
- [x] Same as Step 12 for `EventRegistryService`

### Step 14 — services/schema_service.py: same service layer changes
- [x] Same as Step 12 for schema service

### Step 15 — api/v1/agents.py: switch to get_tenanted_db + get_platform_tenant_id
- [x] Remove `from uuid import UUID`
- [x] Change import: `from ...core.database import get_db` → `from soorma_service_common.dependencies import get_tenanted_db`
- [x] Change import: `from ..dependencies import get_developer_tenant_id` → `from ..dependencies import get_platform_tenant_id`
- [x] Update all route handler signatures: `db: AsyncSession = Depends(get_db)` → `Depends(get_tenanted_db)`
- [x] Update all route handler signatures: `developer_tenant_id: UUID = Depends(get_developer_tenant_id)` → `platform_tenant_id: str = Depends(get_platform_tenant_id)`
- [x] Update all service calls: `developer_tenant_id` → `platform_tenant_id`

### Step 16 — api/v1/events.py: same API route changes
- [x] Same as Step 15 for events router

### Step 17 — api/v1/schemas.py: same API route changes
- [x] Same as Step 15 for schemas router

### Step 18 — alembic 004 migration: rename+retype+RLS
- [x] Create `services/registry/alembic/versions/004_platform_tenant_id.py`
- [x] `upgrade()`:
  - Drop composite unique constraints on `agents`, `events`, `payload_schemas` that reference `tenant_id`
  - Rename column `tenant_id → platform_tenant_id` on all three tables using `op.alter_column` with `new_column_name`
  - Alter column type `UUID → VARCHAR(64)` using `USING tenant_id::text` (needs `postgresql_using` clause)
  - Recreate composite unique constraints with `platform_tenant_id`
  - Drop existing RLS policies from migration 003 (they reference `::UUID` cast — now invalid)
  - `ALTER TABLE agents ENABLE ROW LEVEL SECURITY; ALTER TABLE agents FORCE ROW LEVEL SECURITY`
  - Repeat for `events` and `payload_schemas`
  - Create isolation policies: `CREATE POLICY ... USING (platform_tenant_id = current_setting('app.platform_tenant_id', true))`
- [x] `downgrade()`: `pass` (no-op per BR-R13)

### Step 19 — tests/conftest.py: update sentinel, remove IS_LOCAL_TESTING, add get_tenanted_db override
- [x] Remove `os.environ["IS_LOCAL_TESTING"] = "true"` line
- [x] Remove `os.environ["SYNC_DATABASE_URL"] = ...` line
- [x] Keep `os.environ["DATABASE_URL"] = TEST_DATABASE_URL` (SQLite via env override)
- [x] Change `TEST_TENANT_ID = UUID("00000000-0000-0000-0000-000000000000")` → `TEST_TENANT_ID = "spt_00000000-0000-0000-0000-000000000000"`
- [x] Remove `from uuid import UUID` (no longer needed)
- [x] Change `headers={"X-Tenant-ID": str(TEST_TENANT_ID)}` → `headers={"X-Tenant-ID": TEST_TENANT_ID}` (already a str now)
- [x] Add `from registry_service.api.dependencies import get_tenanted_db` import
- [x] Add SQLite-safe override function:
  ```python
  async def _test_get_tenanted_db():
      """Test override: yield SQLite session without set_config (PostgreSQL-only)."""
      async with AsyncSessionLocal() as session:
          yield session
  app.dependency_overrides[get_tenanted_db] = _test_get_tenanted_db
  ```
- [x] This override must be set at module load time (top-level, not inside a fixture)

### Step 20 — test files: update tenant sentinels and behavior assertions
- [x] `test_schema_endpoints.py` (own UUID definitions):
  - Change `TEST_TENANT_ID = UUID(...)` → `TEST_TENANT_ID = "spt_00000000-0000-0000-0000-000000000000"`
  - Change `TENANT_A = UUID("11111111-...")` → `TENANT_A = "spt_11111111-1111-1111-1111-111111111111"`
  - Change `TENANT_B = UUID("22222222-...")` → `TENANT_B = "spt_22222222-2222-2222-2222-222222222222"`
  - Remove `from uuid import UUID`
  - Update `str(TENANT_A)` → `TENANT_A` in headers (already string)
  - Update 3 "without X-Tenant-ID returns 422" assertions → now defaults to `DEFAULT_PLATFORM_TENANT_ID` via middleware; requests succeed (change to 200 assertion)
- [x] `test_agent_ttl.py`: `TEST_TENANT_ID` imported from conftest — no change needed once conftest updated; direct service calls accept `str` type
- [x] `test_orphaned_capability_bug.py`, `test_expired_agent_cascade_delete.py`, `test_background_cleanup.py`: same — import from conftest; direct service/CRUD calls accept `str`
- [x] `test_agent_deduplication.py`, `test_agent_discovery.py`, `test_agent_dto.py`, `test_agent_ttl_api.py`, `test_event_dto.py`: check for any UUID/tenant references and update if needed
- [x] Run full test suite and confirm all pass

### Step 21 — code-summary.md
- [x] Create `aidlc-docs/platform/multi-tenancy/construction/registry/code/code-summary.md`
- [x] Document: files changed, test count, key design decisions applied

---

## TDD Cycle Notes

This is a **brownfield refactor** — no new business logic. The TDD cycle is:

1. **Modify source files** (Steps 1–18) — make changes that will break existing tests (type errors, missing attrs)
2. **RED** — run `pytest` from `services/registry/` — expect failures due to UUID→str type mismatches and IS_LOCAL_TESTING removal
3. **GREEN** — update tests (Steps 19–20) to use string sentinel and remove IS_LOCAL_TESTING setup
4. **All pass** — full suite green

Note: Migration (Step 18) is not exercised by unit tests directly (SQLite in tests); TC-R-001/R-011 require PostgreSQL integration test environment.

---

## Security Compliance

| Rule | Status |
|------|--------|
| SECURITY-01: No secrets in code | Compliant — DATABASE_URL from env |
| SECURITY-02: Input validation | Compliant — `get_platform_tenant_id` is opaque string; no UUID parsing |
| SECURITY-03: RLS enforcement | Compliant — `get_tenanted_db` activates RLS on every request |
| SECURITY-04: No cross-tenant data | Compliant — RLS + app-layer WHERE both enforce isolation |
