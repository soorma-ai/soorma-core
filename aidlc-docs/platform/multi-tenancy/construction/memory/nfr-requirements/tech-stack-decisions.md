# Tech Stack Decisions — U4: services/memory
## Initiative: Multi-Tenancy Model Implementation
**Date**: 2026-03-23

---

## Existing Stack (unchanged)

| Component | Technology | Version / Details | Decision |
|-----------|-----------|------------------|----------|
| API framework | FastAPI | existing | No change |
| ASGI / middleware | Starlette `BaseHTTPMiddleware` | existing | Inherit from soorma-service-common |
| ORM | SQLAlchemy (async) | existing | No change |
| DB driver | asyncpg (PostgreSQL) | existing | No change |
| Vector extension | pgvector | existing | No change |
| Migrations | Alembic | existing | Add migration 008 |
| Settings | pydantic-settings | existing | Remove is_local_testing |
| Test framework | pytest + pytest-asyncio | existing | No change |

---

## New Dependencies

| Dependency | Source | Purpose |
|-----------|--------|---------|
| `soorma-service-common` | `libs/soorma-service-common/` (workspace) | `TenancyMiddleware`, `create_get_tenanted_db`, `TenantContext`, `PlatformTenantDataDeletion` |

**Add to `pyproject.toml`**:
```toml
[tool.poetry.dependencies]
soorma-service-common = {path = "../../libs/soorma-service-common", develop = true}
```

---

## Removed Dependencies

| Component | Reason |
|-----------|--------|
| Local `TenancyMiddleware` (`memory_service/core/middleware.py`) | Replaced by shared implementation from soorma-service-common |
| Local `TenantContext` / `get_tenant_context` (`memory_service/core/dependencies.py`) | Replaced by re-exports from soorma-service-common |
| `ensure_tenant_exists()` / `set_session_context()` in `database.py` | No tenants table; set_config handled by get_tenanted_db |

---

## Security Controls in Use

| Control | Implementation | Activation |
|---------|---------------|-----------|
| PostgreSQL RLS | Policy per table using `current_setting` | `ENABLE ROW LEVEL SECURITY` + `FORCE ROW LEVEL SECURITY` |
| Transaction-scoped `set_config` | `get_tenanted_db` from soorma-service-common | Per HTTP request, via `get_tenant_context` dependency |
| Platform tenant isolation | `platform_tenant_id` WHERE clause in all queries | Enforced at CRUD layer |
| Composite key enforcement | `(platform_tenant_id, service_tenant_id, service_user_id)` | All queries include platform_tenant_id minimum |
