# Code Summary: U3 — services/registry Multi-Tenancy Migration

## Unit Context
- **Unit**: U3 — `services/registry`
- **Stage**: Code Generation
- **Branch**: `dev`
- **Plan**: `construction/plans/registry-code-generation-plan.md`

## Overview
Migrated the Registry service from UUID-based `developer_tenant_id` isolation to the platform-standard `platform_tenant_id: str` pattern, integrated `TenancyMiddleware` and the `create_get_tenanted_db` factory from `soorma-service-common`, and aligned the test suite accordingly. All 80 tests pass.

---

## Files Modified

### Infrastructure
| File | Change |
|------|--------|
| `pyproject.toml` | Added `soorma-service-common` to main deps; moved `aiosqlite` to dev optional |
| `core/config.py` | Removed `IS_LOCAL_TESTING`, `SYNC_DATABASE_URL`, Cloud SQL fields, `check_required_settings()`; updated `DATABASE_URL` default to PostgreSQL |
| `core/database.py` | Removed `create_db_url()`; simplified `create_db_engine()` to single `DATABASE_URL` path with `NullPool` |
| `core/__init__.py` | Removed exports of `check_required_settings` and `create_db_url` |
| `api/dependencies.py` | Full replacement: `create_get_tenanted_db(get_db)` factory + `get_platform_tenant_id` re-export |
| `main.py` | Added `TenancyMiddleware`; fixed log level to use `settings.IS_PROD` |

### Models
| File | Change |
|------|--------|
| `models/schema.py` | Restored `UUID` import (still used for PK); `tenant_id: Mapped[UUID]` → `platform_tenant_id: Mapped[str]` with `String(64)` |
| `models/agent.py` | `tenant_id: Mapped[UUID]` → `platform_tenant_id: Mapped[str]` with `String(64)`; removed `Uuid` import |
| `models/event.py` | Same rename+retype as `agent.py` |

### CRUD
| File | Change |
|------|--------|
| `crud/agents.py` | `developer_tenant_id: UUID` → `platform_tenant_id: str` in all 8 methods; ORM and WHERE clause column references updated; fixed truncated function body (syntax error from prior session) |
| `crud/events.py` | Same rename in all 5 methods |
| `crud/schemas.py` | Same rename in all 5 methods |

### Services
| File | Change |
|------|--------|
| `services/agent_service.py` | All methods: `UUID` → `str` for tenant parameter |
| `services/event_service.py` | Same |
| `services/schema_service.py` | Same |

### API Routes
| File | Change |
|------|--------|
| `api/v1/agents.py` | All 5 endpoints: `get_db` → `get_tenanted_db`, `get_developer_tenant_id` → `get_platform_tenant_id`, `UUID` → `str`; fixed `get_tenanted_tenanted_db` typo |
| `api/v1/events.py` | Same for both endpoints |
| `api/v1/schemas.py` | Same for all 4 endpoints |

### Tests
| File | Change |
|------|--------|
| `tests/conftest.py` | `TEST_TENANT_ID` UUID → `"spt_00000000-..."` str; removed `IS_LOCAL_TESTING`/`SYNC_DATABASE_URL` env vars; added `get_tenanted_db` override (SQLite-safe bypass of `set_config`) |
| `tests/test_schema_endpoints.py` | UUID sentinels → `spt_` prefixed strings; 3 "missing header → 422" → 200/404 (TenancyMiddleware defaults to `DEFAULT_PLATFORM_TENANT_ID`) |
| `tests/test_agent_discovery.py` | UUID sentinels → `spt_` strings; 1 "missing header → 422" → 200 |

---

## Migration (Step 18 — Alembic 004)

**File**: `alembic/versions/004_platform_tenant_id.py`

**upgrade()** performs:
1. Drops old UUID-based unique indexes on `agents`, `events`, `payload_schemas`
2. `ALTER COLUMN tenant_id RENAME TO platform_tenant_id` on all three tables
3. `ALTER COLUMN TYPE VARCHAR(64) USING tenant_id::text` on all three tables
4. Recreates unique indexes with `platform_tenant_id`
5. Drops old RLS policies (reference `::UUID` cast and old `app.tenant_id` setting)
6. `ENABLE/FORCE ROW LEVEL SECURITY` on all three tables
7. Creates new `CREATE POLICY` using `current_setting('app.platform_tenant_id', true)`

**downgrade()**: `pass` (no-op — destructive reversal not supported)

---

## Key Architectural Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Tenant ID type | `str` (`spt_` prefixed) | Aligns with `soorma-common.DEFAULT_PLATFORM_TENANT_ID`; avoids UUID parsing overhead |
| DB dependency injection | `create_get_tenanted_db(get_db)` factory | `soorma-service-common` pattern; binds registry's own `AsyncSessionLocal` |
| SQLite test compatibility | `app.dependency_overrides[get_tenanted_db]` | Bypasses `SELECT set_config()` which is PostgreSQL-only |
| RLS setting key | `app.platform_tenant_id` | Matches `TenancyMiddleware` injection in `soorma-service-common` |

---

## Test Results
```
80 passed in 5.91s
```

All tests pass including:
- Agent CRUD (create, upsert, TTL, deduplication, discovery)
- Event CRUD
- Schema registry endpoints (all 4 endpoints)
- Cross-tenant isolation for agents and schemas
- Missing-header behavior (now defaults to `DEFAULT_PLATFORM_TENANT_ID` via middleware)
