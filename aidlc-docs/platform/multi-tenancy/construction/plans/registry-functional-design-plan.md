# Functional Design Plan — services/registry (U3)
## Initiative: Multi-Tenancy Model Implementation
**Created**: 2026-03-22T19:03:57Z

---

## Unit Summary

**Unit**: U3 — `services/registry`
**Wave**: 2 (parallel with U2 — soorma-service-common)
**Change Type**: Moderate
**Depends On**: U1 (soorma-common) — COMPLETE
**Functional Design Stages**:
- [x] Step 1: Analyze Unit Context
- [x] Step 2: Create Functional Design Plan (this document)
- [ ] Step 3: Collect Question Answers
- [ ] Step 4: Generate Functional Design Artifacts
- [ ] Step 5: Present Completion Message

---

## Step 1 — Unit Context Analysis

### What U3 Does
Registry Service is the developer-facing agent/event/schema registry. It is **platform-tenant scoped only** — no service tenant or service user concept. After this unit:
- `tenant_id UUID` columns on `agents`, `events`, `payload_schemas` → `platform_tenant_id VARCHAR(64)`
- `get_developer_tenant_id()` dependency removed → replaced by `get_platform_tenant_id()` from `soorma-service-common`
- `TenancyMiddleware` from `soorma-service-common` added to `main.py`
- `IS_LOCAL_TESTING` / SQLite branching removed from `config.py` and `database.py`
- Tests updated to use `spt_00000000-0000-0000-0000-000000000000` sentinel

### Files in Scope (identified from codebase analysis)
| File | Change Type |
|---|---|
| `services/registry/pyproject.toml` | Add `soorma-service-common` dependency |
| `services/registry/src/registry_service/core/config.py` | Remove `IS_LOCAL_TESTING`, remove SQLite defaults, remove `SYNC_DATABASE_URL` |
| `services/registry/src/registry_service/core/database.py` | Simplify `create_db_engine()` / `create_db_url()` — PostgreSQL only |
| `services/registry/src/registry_service/api/dependencies.py` | Remove `get_developer_tenant_id()`; import `get_platform_tenant_id` from `soorma_service_common.dependencies` |
| `services/registry/src/registry_service/main.py` | Register `TenancyMiddleware` from `soorma_service_common.middleware` |
| `services/registry/src/registry_service/models/agent.py` | `tenant_id: Mapped[UUID]` → `platform_tenant_id: Mapped[str]` with `String(64)` |
| `services/registry/src/registry_service/models/event.py` | Same ORM column rename + type change |
| `services/registry/src/registry_service/models/schema.py` | Same ORM column rename + type change |
| `services/registry/src/registry_service/crud/agents.py` | `developer_tenant_id: UUID` → `platform_tenant_id: str` across all CRUD methods |
| `services/registry/src/registry_service/crud/events.py` | Same parameter type change |
| `services/registry/src/registry_service/crud/schemas.py` | Same parameter type change |
| `services/registry/src/registry_service/services/*.py` | `tenant_id: UUID` → `platform_tenant_id: str` in service layer |
| `services/registry/src/registry_service/api/v1/*.py` | Update Depends() from `get_developer_tenant_id` → `get_platform_tenant_id` |
| `services/registry/alembic/versions/004_tenant_id_uuid_to_varchar.py` | New migration: ALTER COLUMN `tenant_id → platform_tenant_id VARCHAR(64)` |
| `services/registry/tests/conftest.py` | Remove SQLite setup; update sentinel to `spt_00000000-0000-0000-0000-000000000000` |
| `services/registry/tests/test_*.py` | Update `TEST_TENANT_ID` format, header values, assertion strings |

---

## Step 2 — Clarifying Questions

**Please provide answers in the `[Answer]:` tags below, then reply "answers provided" in the chat.**

---

### Q1: database.py Simplification Strategy

The current `create_db_engine()` has two paths:
- **IS_LOCAL_TESTING = True**: uses `sqlite+aiosqlite` driver
- **IS_LOCAL_TESTING = False**: assembles a Cloud SQL Unix socket URL from `DB_INSTANCE_CONNECTION_NAME`, `DB_USER`, `DB_NAME`, `DB_PASS_PATH`

After removing `IS_LOCAL_TESTING`, the simplest approach is to drop the URL-assembly logic entirely and always use `settings.DATABASE_URL` directly:

```python
def create_db_engine():
    return create_async_engine(settings.DATABASE_URL, poolclass=NullPool, future=True)
```

Operators (including Cloud Run / Cloud Build) set `DATABASE_URL` to the appropriate `postgresql+asyncpg://...` connection string. SQLite-based tests keep working by setting `DATABASE_URL=sqlite+aiosqlite:///./test.db` in their env.

**Option A**: Use `settings.DATABASE_URL` directly (drop Cloud SQL socket assembly code — clean, simple, relies on operator-provided URL)
**Option B**: Keep the Cloud SQL socket assembly path for production (read from `DB_INSTANCE_CONNECTION_NAME`, `DB_USER`, etc.) but drop the IS_LOCAL_TESTING/SQLite branch

[Answer]: **A** — Use `settings.DATABASE_URL` directly. Rationale: consistent with memory service pattern. All major platforms (Cloud Run, GKE, ECS, EKS) support injecting secrets as a single env var — store the full `DATABASE_URL` (including password) in Secret Manager and inject it. File-based password delivery (`DB_PASS_PATH`) is not required in our deployment model. Removing the Cloud SQL URL assembly code eliminates dead complexity.

---

### Q2: aiosqlite in pyproject.toml

`aiosqlite` is currently a main dependency (used for local development). After removing IS_LOCAL_TESTING and SQLite as a production concern, it is only needed if tests continue to use SQLite.

**Option A**: Move `aiosqlite` to `[project.optional-dependencies] dev` section (keep SQLite for tests, but don't ship it as a required production dependency)  
**Option B**: Remove `aiosqlite` entirely (switch tests to use mock sessions or a real test-PostgreSQL; no more SQLite in tests)  
**Option C**: Keep `aiosqlite` as a main dependency (status quo — minimal change, SQLite still available)

[Answer]: **A** — Move `aiosqlite` to `[project.optional-dependencies] dev`. Rationale: consistent with memory service pattern (same version comment: "SQLite async driver for testing"). Not a production dependency — no reason to ship it in the production image.

---

### Q3: Alembic Migration Downgrade Path

The migration changes `tenant_id UUID` → `platform_tenant_id VARCHAR(64)` using a `USING tenant_id::text` cast.

**Option A**: Implement a real downgrade (ALTER COLUMN back to UUID with `USING platform_tenant_id::uuid` cast). This works only if all stored values are valid UUIDs — during the transition period this will be true.  
**Option B**: No-op downgrade (`pass`) — once run, the column rename is not reversed automatically.

[Answer]: **B** — No-op downgrade. Rationale: pre-release, no production data exists. If rollback is ever needed, a new forward migration is sufficient. No value in implementing a reversal that will never be used.

---

### Q4: Test Strategy Post-SQLite-Removal

The current `conftest.py` creates a fresh on-disk SQLite DB for each test using `Base.metadata.create_all()`. After removing IS_LOCAL_TESTING:

**Option A (Recommended)**: Keep SQLite in tests via `DATABASE_URL` env override. `conftest.py` continues to override `DATABASE_URL` to `sqlite+aiosqlite:///...` before importing the app. `create_db_engine()` reads `DATABASE_URL` from settings (now simplified to just read the env var), so SQLite-based tests continue working. The `SYNC_DATABASE_URL` env var can be dropped (only needed for Alembic in tests; Alembic can be told the URL directly).

**Option B**: Switch to mock-based tests (no real DB, use `AsyncMock` sessions). This is lighter weight but loses the relational/constraint-level integration coverage the current tests provide.

**Option C**: Require a real PostgreSQL for tests (`pytest-postgresql` or a Docker fixture). Most production-accurate but adds infrastructure dependency.

[Answer]: A

---

### Q5: Column Rename vs Type-Only Change

The inception spec says "rename `tenant_id` → `platform_tenant_id`" across ORM models and all call sites. The Alembic migration would:
1. `ALTER TABLE agents RENAME COLUMN tenant_id TO platform_tenant_id`
2. `ALTER TABLE agents ALTER COLUMN platform_tenant_id TYPE VARCHAR(64) USING platform_tenant_id::text`
3. Same for `events` and `payload_schemas`

But the existing unique constraints reference the `tenant_id` column name (e.g., `UniqueConstraint("event_name", "tenant_id")` on `EventTable`). These constraints need to be dropped and recreated with the new column name.

**This is already our plan** — just confirming: should the migration also drop and recreate the composite unique constraints using the new `platform_tenant_id` column name?

A) Yes — drop and recreate constraints with new column name (correct approach)
B) No — leave constraint names as-is (would be broken after column rename)

[Answer]: A

---

## Step 3 — Complete ✓

All Q1–Q5 answers collected.

---

## Artifact Output Plan

Once questions are answered, the following artifacts will be generated:

| Artifact | Path |
|---|---|
| Business Logic Model | `construction/registry/functional-design/business-logic-model.md` |
| Business Rules | `construction/registry/functional-design/business-rules.md` |
| Domain Entities | `construction/registry/functional-design/domain-entities.md` |
