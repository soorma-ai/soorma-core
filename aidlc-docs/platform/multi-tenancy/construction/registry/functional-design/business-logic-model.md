# Business Logic Model — services/registry (U3)
## Initiative: Multi-Tenancy Model Implementation
**Date**: 2026-03-22

---

## Overview

U3 is a structural migration of `services/registry`. There is no new business logic — the change replaces a strict UUID type contract with an opaque string contract for the platform tenant identifier, removes the SQLite/local-testing infrastructure fork, and wires up the shared `soorma-service-common` middleware and dependency function.

Four distinct logic concerns:

1. **Identity extraction** — replace custom `get_developer_tenant_id()` with `get_platform_tenant_id()` from `soorma-service-common`
2. **DB engine simplification** — collapse the two-path `create_db_engine()` into a single `DATABASE_URL`-driven path
3. **Schema migration** — rename and retype `tenant_id UUID → platform_tenant_id VARCHAR(64)` across three tables; add PostgreSQL RLS policies
4. **RLS activation** — wire `get_tenanted_db` into route handlers for DB-layer tenant enforcement

---

## Design Decision: Adding RLS to Registry

**Why this deviates from the inception spec**

The original inception spec (`components.md` C3) explicitly stated *"No RLS policies; no `set_config`"* for Registry, treating application-layer `WHERE platform_tenant_id = :val` clauses as sufficient isolation.

During functional design this decision was revisited in light of **SOC2 Type II certification** requirements. The conclusion: RLS should be added.

**Rationale**

| Control type | Application-layer WHERE | PostgreSQL RLS |
|---|---|---|
| Trust boundary | Application code — developer discipline | Database engine — enforced regardless of app bug |
| Auditability | Every query path must be individually verified | Single policy definition, proven by one cross-tenant test |
| SOC2 evidence | "We have a code review process" | "Here is the RLS policy; here is the test proving cross-tenant isolation" |
| Defense in depth | No — a missed WHERE leaks data | Yes — DB refuses even if app forgets WHERE |

In a SOC2 Type II audit or customer security review, a DB-layer control (RLS) is categorically stronger evidence than an application-layer convention. Registry holds tenant agent topology, event schemas, and capability registrations — not PII, but still confidential multi-tenant data. A customer's security team would flag the absence of DB-level isolation even on developer tooling infrastructure.

The incremental cost (one RLS policy per table, `get_tenanted_db` wiring, one cross-tenant test) is small relative to the audit and correctness benefit. Consistency across all services (Memory, Tracker, Registry all using the same RLS model) also simplifies the security posture narrative.

---

## 1. Identity Extraction — Before vs After

### Before (current)
```
HTTP request arrives
    ↓
No middleware — no request.state population
    ↓
Route handler declares: developer_tenant_id: UUID = Depends(get_developer_tenant_id)
    ↓
get_developer_tenant_id reads X-Tenant-ID header directly
    ↓
Parses to UUID — raises HTTP 400 if not a valid UUID format
    ↓
Passes developer_tenant_id: UUID to service layer → CRUD layer → ORM (Uuid column)
```

### After (this unit)
```
HTTP request arrives
    ↓
TenancyMiddleware.dispatch() (from soorma-service-common)
    → X-Tenant-ID header present → request.state.platform_tenant_id = header value
    → X-Tenant-ID absent         → request.state.platform_tenant_id = DEFAULT_PLATFORM_TENANT_ID
    → (service/user headers not used by Registry — stored as None but ignored)
    ↓
Route handler declares: platform_tenant_id: str = Depends(get_platform_tenant_id)
    ↓
get_platform_tenant_id reads request.state.platform_tenant_id (set by middleware)
    → No UUID parsing — opaque string, any format accepted
    ↓
Passes platform_tenant_id: str to service layer → CRUD layer → ORM (String(64) column)
    ↓
get_tenanted_db calls set_config('app.platform_tenant_id', platform_tenant_id, true)
    → RLS policy on agents/events/payload_schemas activates
    → All queries in this transaction see only rows matching platform_tenant_id
```

### Key behavioural differences
| Aspect | Before | After |
|---|---|---|
| Format enforcement | UUID only — 400 on non-UUID | Opaque string — any value accepted |
| Default when header absent | Error (header required) | `DEFAULT_PLATFORM_TENANT_ID` |
| Where header is read | Inside `get_developer_tenant_id()` | Inside `TenancyMiddleware` |
| Dependency parameter type | `UUID` | `str` |
| DB session dependency | `Depends(get_db)` | `Depends(get_tenanted_db)` |
| DB-layer tenant isolation | None (app WHERE only) | RLS policy enforced by PostgreSQL |

---

## 2. DB Engine Simplification

### Before
```
create_db_engine() branches on settings.IS_LOCAL_TESTING:
    IS_LOCAL_TESTING = True  → driver = "sqlite+aiosqlite" → settings.DATABASE_URL
    IS_LOCAL_TESTING = False → driver = "postgresql+asyncpg"
                             → assemble Cloud SQL Unix socket URL from:
                               DB_INSTANCE_CONNECTION_NAME, DB_USER, DB_NAME,
                               DB_PASS_PATH (reads password from file)
```

### After
```
create_db_engine():
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool, echo=False)
    return engine
```

`settings.DATABASE_URL` defaults to `postgresql+asyncpg://soorma:soorma@localhost:5432/registry`.
Operators override `DATABASE_URL` env var for all environments (local dev, CI, Cloud Run).
Tests override `DATABASE_URL=sqlite+aiosqlite:///./test_registry.db` in `conftest.py` before app import — the simplified engine reads it transparently.

### Settings fields removed
- `IS_LOCAL_TESTING: bool`
- `SYNC_DATABASE_URL: str` (only needed for Alembic CLI; Alembic test runs can be skipped)
- `DB_INSTANCE_CONNECTION_NAME: Optional[str]`
- `DB_USER: Optional[str]`
- `DB_NAME: Optional[str]`
- `DB_PASS_PATH: Optional[str]`

### Settings field added / updated
- `DATABASE_URL: str` — default changed from `sqlite+aiosqlite:///./registry.db` to `postgresql+asyncpg://soorma:soorma@localhost:5432/registry`

---

## 3. Schema Migration Flow

```
Alembic migration 004_tenant_id_uuid_to_varchar executes:

For each table in [agents, events, payload_schemas]:

    Step 1 — Drop composite unique constraints that reference tenant_id column:
        agents:          (agent_id, tenant_id) unique — drop
        events:          (event_name, tenant_id) unique — drop
        payload_schemas: (schema_name, version, tenant_id) unique — drop

    Step 2 — Rename column:
        ALTER TABLE <table> RENAME COLUMN tenant_id TO platform_tenant_id

    Step 3 — Change type:
        ALTER TABLE <table>
            ALTER COLUMN platform_tenant_id TYPE VARCHAR(64)
            USING platform_tenant_id::text

    Step 4 — Recreate composite unique constraints with new column name:
        agents:          (agent_id, platform_tenant_id) unique
        events:          (event_name, platform_tenant_id) unique
        payload_schemas: (schema_name, version, platform_tenant_id) unique

    Step 5 — Create RLS policies on all three tables:
        ALTER TABLE agents          ENABLE ROW LEVEL SECURITY;
        ALTER TABLE events          ENABLE ROW LEVEL SECURITY;
        ALTER TABLE payload_schemas ENABLE ROW LEVEL SECURITY;

        CREATE POLICY registry_platform_tenant_isolation ON agents
            USING (platform_tenant_id = current_setting('app.platform_tenant_id', true));

        CREATE POLICY registry_platform_tenant_isolation ON events
            USING (platform_tenant_id = current_setting('app.platform_tenant_id', true));

        CREATE POLICY registry_platform_tenant_isolation ON payload_schemas
            USING (platform_tenant_id = current_setting('app.platform_tenant_id', true));

        -- Service role bypass (superuser / migration user must not be blocked):
        ALTER TABLE agents          FORCE ROW LEVEL SECURITY;
        ALTER TABLE events          FORCE ROW LEVEL SECURITY;
        ALTER TABLE payload_schemas FORCE ROW LEVEL SECURITY;

Downgrade: no-op (pre-release — no production data; rollback via new forward migration if needed)
```

---

## 4. RLS Activation via get_tenanted_db

```
Route handler has: db: AsyncSession = Depends(get_tenanted_db)
    ↓
get_tenanted_db(request, db=Depends(get_db)) invoked
    ↓
    Read from request.state (set by TenancyMiddleware):
        platform_tenant_id = request.state.platform_tenant_id
        service_tenant_id  = request.state.service_tenant_id  (will be None for Registry callers)
        service_user_id    = request.state.service_user_id    (will be None for Registry callers)
    ↓
    Execute within the open AsyncSession transaction:
        SELECT set_config('app.platform_tenant_id', platform_tenant_id, true)
        SELECT set_config('app.service_tenant_id',  '', true)   ← None → ''
        SELECT set_config('app.service_user_id',    '', true)   ← None → ''
    ↓
    yield db  [RLS policies on agents/events/payload_schemas now active]
    ↓
    All SELECT/INSERT/UPDATE/DELETE constrained by RLS: only rows where
    platform_tenant_id = current_setting('app.platform_tenant_id', true) are visible
```

**Note**: `service_tenant_id` and `service_user_id` are set to empty string for Registry — RLS policies only filter on `platform_tenant_id`, so the empty values are harmless. The `get_tenanted_db` function from `soorma-service-common` always sets all three variables.

---

## 4. Test Fixture Simplification

### Before
```
conftest.py:
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_registry.db"
    os.environ["IS_LOCAL_TESTING"] = "true"
    → create_db_engine() branches to SQLite path via IS_LOCAL_TESTING
```

### After
```
conftest.py:
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_registry.db"
    # IS_LOCAL_TESTING env var removed — no longer exists
    → create_db_engine() reads settings.DATABASE_URL → gets SQLite URL → works transparently
```

Sentinel updated: `TEST_TENANT_ID = "spt_00000000-0000-0000-0000-000000000000"` (string, not UUID).
Header in `client` fixture: `{"X-Tenant-ID": TEST_TENANT_ID}` (no UUID conversion).
