# Code Summary: soorma-service-common

**Unit**: U2 — soorma-service-common  
**Construction Stage**: Code Generation  
**Status**: Complete ✅

---

## Library Overview

`soorma-service-common` is a new Python library (`libs/soorma-service-common/`) that provides shared FastAPI/Starlette infrastructure for Soorma backend services (Memory, Tracker, and future services). It encapsulates the three-dimension tenancy identity model and PostgreSQL RLS activation pattern so each consuming service gets the same behaviour without duplicating code.

---

## Files Created

### Package Structure

```
libs/soorma-service-common/
├── pyproject.toml                          # Poetry/hatchling project config
├── README.md                               # Usage documentation
└── src/
    └── soorma_service_common/
        ├── __init__.py                     # Public API exports
        ├── py.typed                        # PEP 561 marker
        ├── middleware.py                   # TenancyMiddleware
        ├── dependencies.py                 # FastAPI dependency functions
        ├── tenant_context.py               # TenantContext + factory
        └── deletion.py                     # PlatformTenantDataDeletion ABC
```

### Test Structure

```
libs/soorma-service-common/
└── tests/
    ├── __init__.py
    ├── conftest.py                         # Shared fixtures
    ├── test_middleware.py                  # TenancyMiddleware tests (11 tests)
    ├── test_dependencies.py                # Dependency function tests (19 tests)
    ├── test_tenant_context.py              # TenantContext tests (7 tests)
    └── test_deletion.py                    # PlatformTenantDataDeletion ABC tests (6 tests)
```

**Test result**: 40/40 passed ✅

---

## Module Descriptions

### `middleware.py` — TenancyMiddleware

**Class**: `TenancyMiddleware(BaseHTTPMiddleware)`

Extracts the three identity dimensions from HTTP headers on every request and stores them on `request.state`. Does NOT touch the database — RLS activation is deferred to `get_tenanted_db`.

| Header | `request.state` attribute | Default |
|---|---|---|
| `X-Tenant-ID` | `platform_tenant_id` | `DEFAULT_PLATFORM_TENANT_ID` |
| `X-Service-Tenant-ID` | `service_tenant_id` | `None` |
| `X-User-ID` | `service_user_id` | `None` |

**Bypass paths**: `/health`, `/docs`, `/openapi.json`, `/redoc` — call_next is invoked immediately without populating `request.state`.

**Key design decision**: `DEFAULT_PLATFORM_TENANT_ID` is imported from `soorma_common.tenancy` — never redefined locally (BR-U2-05).

---

### `dependencies.py` — FastAPI Dependency Functions

#### `get_platform_tenant_id(request) -> str`
Reads `request.state.platform_tenant_id`. Simple passthrough for routes that only need the platform tenant.

#### `get_service_tenant_id(request) -> Optional[str]`
Reads `request.state.service_tenant_id`. Returns `None` if not in request state.

#### `get_service_user_id(request) -> Optional[str]`
Reads `request.state.service_user_id`. Returns `None` if not in request state.

#### `create_get_tenanted_db(get_db: Callable) -> Callable`
**Factory function** — takes the consuming service's `get_db` and returns a FastAPI async generator dependency that:
1. Reads identity from `request.state`
2. Calls `set_config` × 3 (transaction-scoped, `is_local=true`)
3. Yields the `AsyncSession`

`None` values for `service_tenant_id` / `service_user_id` are converted to `''` before passing to `set_config`. PostgreSQL's RLS policies treat `''` as a wildcard / no-filter for optional dimensions.

**Usage**:
```python
# In each consuming service's dependencies.py
from soorma_service_common import create_get_tenanted_db
from my_service.core.database import get_db

get_tenanted_db = create_get_tenanted_db(get_db)
```

#### `set_config_for_session(db, platform_tenant_id, service_tenant_id, service_user_id) -> None`
Same `set_config` × 3 logic as `get_tenanted_db` but for the NATS path where no HTTP request object is available. Event subscribers call this directly after opening a DB session.

#### Private `_set_config_dim(db, key, value) -> None`
Internal helper that executes a single `set_config` call using SQLAlchemy's `text()` with named bind parameters (SQL injection safe):
```sql
SELECT set_config(:key, :value, true)
```

---

### `tenant_context.py` — TenantContext Bundle

#### `TenantContext` (dataclass)

Convenience bundle combining all identity dimensions and an RLS-activated `AsyncSession`. Route handlers use a single `Depends(get_tenant_context)` instead of four separate dependencies.

```python
@dataclass
class TenantContext:
    platform_tenant_id: str
    service_tenant_id: Optional[str]
    service_user_id: Optional[str]
    db: AsyncSession  # already RLS-activated by get_tenanted_db
```

#### `create_get_tenant_context(get_tenanted_db: Callable) -> Callable`
**Factory function** — takes the consuming service's `get_tenanted_db` (itself produced by `create_get_tenanted_db`) and returns a FastAPI dependency that assembles a `TenantContext` from `request.state` + the RLS-activated session.

**Usage**:
```python
from soorma_service_common import create_get_tenant_context
from my_service.core.dependencies import get_tenanted_db

get_tenant_context = create_get_tenant_context(get_tenanted_db)

# In route handlers:
async def my_handler(ctx: TenantContext = Depends(get_tenant_context)):
    results = await ctx.db.execute(...)  # RLS already active
```

---

### `deletion.py` — PlatformTenantDataDeletion ABC

Abstract base class for GDPR-compliant platform-scoped data deletion. Concrete implementations live in each service (`MemoryDataDeletion`, `TrackerDataDeletion`).

Three abstract methods enforce the full deletion scope hierarchy:

| Method | Scope | Use case |
|---|---|---|
| `delete_by_platform_tenant(db, platform_tenant_id)` | Entire platform tenant | Organisation offboarding |
| `delete_by_service_tenant(db, platform_tenant_id, service_tenant_id)` | Service-level tenant | Tenant-scoped erasure |
| `delete_by_service_user(db, platform_tenant_id, service_tenant_id, service_user_id)` | Individual user | GDPR Article 17 right-to-erasure |

All methods return `int` (total rows deleted) for audit logging.

---

## Public API

```python
from soorma_service_common import (
    # Middleware
    TenancyMiddleware,

    # Dependency functions (HTTP path)
    get_platform_tenant_id,
    get_service_tenant_id,
    get_service_user_id,
    create_get_tenanted_db,     # factory

    # NATS path
    set_config_for_session,

    # Identity bundle
    TenantContext,
    create_get_tenant_context,  # factory

    # GDPR deletion ABC
    PlatformTenantDataDeletion,
)
```

---

## Key Design Decisions

1. **Factory pattern** (`create_get_tenanted_db`, `create_get_tenant_context`): `get_db` is service-specific and cannot be defined in the shared library. Factories accept `get_db` at binding time and return a ready FastAPI dependency. Each consuming service calls the factory once at module level.

2. **`None → ''` conversion**: PostgreSQL `set_config` requires string values. `None` for optional dimensions is converted to `''` before the SQL call. RLS policies are designed to interpret `''` as "no filter" for optional dimensions.

3. **Transaction-scoped `set_config`** (`is_local=true`): All three session variables are set with transaction scope, not session scope. This ensures RLS variables are isolated per-request even if connection pooling reuses DB connections.

4. **Middleware never touches DB**: `TenancyMiddleware.dispatch` reads only HTTP headers. All DB interactions are in `get_tenanted_db`. This eliminates DB access from the middleware layer (BR-U2-01).

5. **SQLAlchemy `text()` with named bind params**: SQL injection safety — `set_config` key and value are always passed as bound parameters, never interpolated into the SQL string.

6. **`DEFAULT_PLATFORM_TENANT_ID` imported, not redefined**: Sourced from `soorma_common.tenancy` to avoid divergence across services (BR-U2-05).

---

## TDD Summary

| Phase | Result |
|---|---|
| STUB | All 4 modules created with `NotImplementedError` stubs |
| RED | 29 failed (all `NotImplementedError`), 11 passed (structural/ABC) |
| GREEN | 40/40 passed |
| REFACTOR | `__init__.py` docstring cleaned up; no logic changes needed |
