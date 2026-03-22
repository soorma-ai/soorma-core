# Domain Entities — soorma-service-common (U2)
## Initiative: Multi-Tenancy Model Implementation
**Date**: 2026-03-22

---

## Overview

`soorma-service-common` defines three domain entities (data structures) and four function-level interfaces. No persistent state — the library is stateless infrastructure code; all state lives in `request.state` (per-request) and PostgreSQL (via session variables).

---

## Entity: IdentityDimensions (request.state attributes — not a named class)

The three identity dimensions carried on every authenticated request. These are stored as attributes on Starlette's `request.state` object by `TenancyMiddleware` — not as a typed dataclass at the middleware level. They are read by the downstream dependency functions.

| Attribute | Type | Source | Default |
|-----------|------|--------|---------|
| `request.state.platform_tenant_id` | `str` | `X-Tenant-ID` header | `DEFAULT_PLATFORM_TENANT_ID` |
| `request.state.service_tenant_id` | `Optional[str]` | `X-Service-Tenant-ID` header | `None` |
| `request.state.service_user_id` | `Optional[str]` | `X-User-ID` header | `None` |

**Lifetime**: Per HTTP request. Not persisted. Not shared across requests.

---

## Entity: TenantContext (dataclass)

Convenience bundle returned by the `get_tenant_context` FastAPI dependency. Combines all three identity dimensions with a RLS-activated database session into a single object.

```python
@dataclass
class TenantContext:
    platform_tenant_id: str            # Always non-None (DEFAULT fallback guaranteed)
    service_tenant_id:  Optional[str]  # None if X-Service-Tenant-ID not provided
    service_user_id:    Optional[str]  # None if X-User-ID not provided
    db: AsyncSession                   # RLS-activated session (set_config already called)
```

**Lifetime**: Per HTTP request. Created and destroyed within a single FastAPI dependency call scope.
**Invariant**: `db` is always an RLS-activated session — `set_config` x3 has already been called on it by the time `TenantContext` is handed to the route handler.

---

## Entity: PostgreSQL Session Variables (transient, DB-side)

When `get_tenanted_db` or `set_config_for_session` executes, three PostgreSQL session variables are set for the duration of the transaction:

| Variable | PostgreSQL Name | Type | Scope |
|----------|----------------|------|-------|
| Platform tenant | `app.platform_tenant_id` | `TEXT` | Transaction-scoped (`set_config(..., true)`) |
| Service tenant | `app.service_tenant_id` | `TEXT` | Transaction-scoped |
| Service user | `app.service_user_id` | `TEXT` | Transaction-scoped |

**Consumed by**: PostgreSQL RLS policies (via `current_setting('app.platform_tenant_id', true)`)
**Lifetime**: Within the current database transaction only. Cleared on transaction end.
**Empty-string semantics**: When `service_tenant_id` or `service_user_id` is `None` in Python, it is stored as `''` (empty string) in the session variable. RLS policies on services that use these dimensions treat `''` as "no access permitted."

---

## Interface: PlatformTenantDataDeletion (abstract base class)

Abstract contract for GDPR-compliant data deletion. Implementations are per-service.

```python
class PlatformTenantDataDeletion(ABC):
    
    @abstractmethod
    async def delete_by_platform_tenant(
        self,
        db: AsyncSession,
        platform_tenant_id: str,
    ) -> int: ...
    
    @abstractmethod
    async def delete_by_service_tenant(
        self,
        db: AsyncSession,
        platform_tenant_id: str,
        service_tenant_id: str,
    ) -> int: ...
    
    @abstractmethod
    async def delete_by_service_user(
        self,
        db: AsyncSession,
        platform_tenant_id: str,
        service_tenant_id: str,
        service_user_id: str,
    ) -> int: ...
```

**Concrete implementations** (defined in their respective service units):
- `MemoryDataDeletion` — U4 (services/memory)
- `TrackerDataDeletion` — U5 (services/tracker)

**Return value**: All methods return `int` — total rows deleted across all covered tables. Used for audit logging.

---

## Function Signatures (key interfaces)

### TenancyMiddleware.dispatch
```
Input:  request: Request, call_next: Callable
Effect: Reads X-Tenant-ID, X-Service-Tenant-ID, X-User-ID headers → sets request.state
Output: Response (from call_next)
```

### get_tenanted_db
```
Input:  request: Request, db: AsyncSession (Depends(get_db))
Effect: Reads request.state identities → calls set_config x3 on db → yields session
Output: AsyncGenerator[AsyncSession, None]
```

### set_config_for_session
```
Input:  db: AsyncSession, platform_tenant_id: str, service_tenant_id: Optional[str], service_user_id: Optional[str]
Effect: Calls set_config x3 on db
Output: None
```

### get_tenant_context
```
Input:  request: Request, db: AsyncSession (Depends(get_tenanted_db))
Effect: Reads request.state identities → constructs TenantContext
Output: TenantContext
```

---

## Module Structure

```
libs/soorma-service-common/
└── src/
    └── soorma_service_common/
        ├── __init__.py          (public API exports)
        ├── middleware.py        (TenancyMiddleware)
        ├── dependencies.py      (get_platform_tenant_id, get_service_tenant_id,
        │                         get_service_user_id, get_tenanted_db,
        │                         set_config_for_session)
        ├── tenant_context.py    (TenantContext dataclass, get_tenant_context)
        └── deletion.py          (PlatformTenantDataDeletion ABC)
```

---

## Cross-Dependencies

| Entity / Interface | Depends on | Direction |
|---|---|---|
| `TenancyMiddleware` | `soorma_common.tenancy.DEFAULT_PLATFORM_TENANT_ID` | soorma-service-common → soorma-common (U1) |
| `get_tenanted_db` | `get_db` (per-service, injected via `Depends`) | soorma-service-common calls into caller's get_db |
| `get_tenant_context` | `get_tenanted_db` | within soorma-service-common |
| `PlatformTenantDataDeletion` | `AsyncSession` from SQLAlchemy | SQLAlchemy only |

**Note on `get_db`**: `get_tenanted_db` uses `Depends(get_db)` — but `get_db` is not defined in `soorma-service-common`. Each consuming service provides its own `get_db`. This is resolved at FastAPI dependency injection time: `get_tenanted_db` receives the caller's `get_db` via the standard FastAPI `Depends` mechanism. In `soorma-service-common` itself, `get_db` is referenced as a type-compatible callable dependency parameter. The concrete implementation of service-level binding is documented in the Code Generation plan.
