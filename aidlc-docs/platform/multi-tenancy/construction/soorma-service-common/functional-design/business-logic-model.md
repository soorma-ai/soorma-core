# Business Logic Model — soorma-service-common (U2)
## Initiative: Multi-Tenancy Model Implementation
**Date**: 2026-03-22

---

## Overview

U2 creates `libs/soorma-service-common`, a new shared FastAPI/Starlette infrastructure library consumed by all backend services (Memory, Tracker, Registry, Event Service). It encapsulates the full multi-tenancy identity pipeline for the HTTP path and provides a NATS-path helper and a GDPR deletion interface.

Five separate business logic concerns:
1. **Header extraction to request state** (`TenancyMiddleware`)
2. **RLS activation via PostgreSQL `set_config`** (`get_tenanted_db`)
3. **NATS-path RLS activation** (`set_config_for_session`)
4. **Identity bundle for route handlers** (`TenantContext` + `get_tenant_context`)
5. **GDPR platform-scoped deletion interface** (`PlatformTenantDataDeletion`)

---

## 1. TenancyMiddleware — Header Extraction

### Responsibility
Extract all three identity dimensions from HTTP request headers and store them on `request.state` so that downstream FastAPI dependency functions can read them without re-parsing headers.

### Flow
```
HTTP request arrives at service
    ↓
TenancyMiddleware.dispatch(request, call_next)
    ↓
    [if health/docs endpoint] → skip, call call_next directly
    ↓
    Extract X-Tenant-ID header
        → present and non-empty: request.state.platform_tenant_id = header value
        → absent or empty: request.state.platform_tenant_id = DEFAULT_PLATFORM_TENANT_ID
    ↓
    Extract X-Service-Tenant-ID header
        → present and non-empty: request.state.service_tenant_id = header value
        → absent or empty: request.state.service_tenant_id = None
    ↓
    Extract X-User-ID header
        → present and non-empty: request.state.service_user_id = header value
        → absent or empty: request.state.service_user_id = None
    ↓
    call_next(request) [proceeds to route handler with state populated]
    ↓
    return response
```

### Key decisions
- **No DB access in middleware** (Q1 resolution — DB connection cannot be safely managed in Starlette async middleware without the FastAPI dependency lifecycle managing cleanup)
- **DEFAULT_PLATFORM_TENANT_ID fallback** imported from `soorma_common.tenancy` (U1 dependency)
- **Registry service** registers this middleware but does NOT use `get_tenanted_db` (no RLS tables on Registry)
- Health/docs paths (`/health`, `/docs`, `/openapi.json`, `/redoc`) are excluded from identity extraction (no tenanting needed for infrastructure endpoints)

---

## 2. get_tenanted_db — RLS Activation Dependency

### Responsibility
FastAPI dependency that opens an `AsyncSession`, executes PostgreSQL `set_config` for all three session variables in the same transaction, and yields the session. This activates RLS policies for every DB query within the route handler's transaction scope.

### Flow
```
Route handler has: db: AsyncSession = Depends(get_tenanted_db)
    ↓
get_tenanted_db(request, db=Depends(get_db)) is invoked
    ↓
    Read from request.state (set by TenancyMiddleware):
        platform_tenant_id = request.state.platform_tenant_id
        service_tenant_id  = request.state.service_tenant_id  (may be None → '')
        service_user_id    = request.state.service_user_id    (may be None → '')
    ↓
    Execute within the open AsyncSession transaction:
        SELECT set_config('app.platform_tenant_id', platform_tenant_id, true)
        SELECT set_config('app.service_tenant_id',  service_tenant_id or '', true)
        SELECT set_config('app.service_user_id',    service_user_id or '', true)
    ↓
    yield db  [RLS policies now active; all subsequent queries in this session see filtered rows]
    ↓
    [after route handler completes] session commits / rolls back / closes (managed by get_db)
```

### PostgreSQL set_config semantics
- Third argument `true` = transaction-scoped (value cleared when transaction ends — prevents leakage across requests on a connection pool connection)
- `None` sentinel values are converted to empty string `''` — RLS policies use `current_setting('app.service_tenant_id', true)` and treat `''` as "no filter" (permissive for services that don't use service_tenant_id, e.g., Registry)
- `set_config` must be called BEFORE any SELECT/INSERT/UPDATE/DELETE on RLS-protected tables

### Contract
- `get_tenanted_db` MUST be preferred over bare `get_db` in any route that touches RLS-protected tables
- Services with no RLS tables (Registry) use `get_db` directly (no `set_config` needed)
- `get_tenanted_db` assumes `TenancyMiddleware` has already populated `request.state` — this is guaranteed by Starlette's middleware chain executing before route handlers

---

## 3. set_config_for_session — NATS-Path RLS Activation

### Responsibility
Identical `set_config` logic as `get_tenanted_db` but invoked directly on an `AsyncSession` — for NATS event handler code paths where no HTTP `request` object is present.

### Flow
```
NATS event subscriber receives event envelope
    ↓
    Extract from event envelope:
        platform_tenant_id ← event.platform_tenant_id (authoritative — injected by Event Service)
        service_tenant_id  ← event.tenant_id          (service tenant — unchanged through bus)
        service_user_id    ← event.user_id            (service user — unchanged through bus)
    ↓
    Open AsyncSession via get_db() (no HTTP request, so get_tenanted_db not usable)
    ↓
    await set_config_for_session(db, platform_tenant_id, service_tenant_id, service_user_id)
        → same set_config x3 calls as get_tenanted_db
    ↓
    Execute DB queries (RLS active for this session)
```

### Key decisions
- This function is a lower-level helper — callers are responsible for passing correct values
- `platform_tenant_id` defaults to `DEFAULT_PLATFORM_TENANT_ID` in Tracker's NATS path (current architecture — NATS subscriptions have no auth channel yet; event.platform_tenant_id is trusted from Event Service injection)
- Not a FastAPI dependency — a plain async function

---

## 4. TenantContext + get_tenant_context — Identity Bundle

### Responsibility
Convenience bundle reducing route handler boilerplate from four separate `Depends()` calls (platform_tenant_id, service_tenant_id, service_user_id, db) to a single `Depends(get_tenant_context)`.

### Flow
```
Route handler has: ctx: TenantContext = Depends(get_tenant_context)
    ↓
get_tenant_context(request, db=Depends(get_tenanted_db)) is invoked
    ↓
    db is already yielded by get_tenanted_db (set_config already called)
    ↓
    Read from request.state (set by TenancyMiddleware):
        platform_tenant_id = request.state.platform_tenant_id
        service_tenant_id  = request.state.service_tenant_id
        service_user_id    = request.state.service_user_id
    ↓
    Construct and return:
        TenantContext(
            platform_tenant_id=platform_tenant_id,
            service_tenant_id=service_tenant_id,
            service_user_id=service_user_id,
            db=db
        )
```

### TenantContext dataclass
```
TenantContext
  ├── platform_tenant_id: str          (always present — DEFAULT fallback guaranteed by TenancyMiddleware)
  ├── service_tenant_id:  Optional[str] (None if not provided)
  ├── service_user_id:    Optional[str] (None if not provided)
  └── db: AsyncSession                 (RLS-activated session from get_tenanted_db)
```

### Usage pattern in Memory / Tracker services
```python
@router.post("/memory")
async def store_memory(
    payload: MemoryCreate,
    ctx: TenantContext = Depends(get_tenant_context),
):
    result = await crud.create(ctx.db, ctx.platform_tenant_id, ctx.service_tenant_id, ctx.service_user_id, payload)
    return result
```

---

## 5. PlatformTenantDataDeletion — GDPR Deletion Interface

### Responsibility
Defines the abstract deletion contract for GDPR "right to erasure" scoped to the platform tenant namespace. Concrete implementations live in Memory and Tracker services.

### Deletion levels (three-tier granularity)
```
delete_by_platform_tenant(db, platform_tenant_id)
    → removes ALL data for the platform tenant across ALL covered tables
    → use case: platform tenant offboarding / account closure

delete_by_service_tenant(db, platform_tenant_id, service_tenant_id)
    → removes data for one service tenant within a platform tenant namespace
    → always requires platform_tenant_id as the outer scope (partial-key-only deletion is a security violation)
    → use case: service-tenant deprovisioning within a platform account

delete_by_service_user(db, platform_tenant_id, service_tenant_id, service_user_id)
    → removes data for one user within a service tenant within a platform tenant namespace
    → use case: individual user data erasure request
```

### Deletion contract invariants
- All three methods execute within a single DB transaction (the `db` session passed in)
- Each method returns `int` — the total number of rows deleted across all covered tables (for audit/logging)
- Implementations MUST delete from ALL tables covered by the service; no partial coverage
- Composite key rule: partial-key deletion (e.g., deleting by service_tenant_id without platform_tenant_id) is **prohibited**

### Design rationale (Q3 — Application Design Decision)
The ABC lives in `soorma-service-common` (shared) rather than per-service so a future GDPR coordinator service can accept a list of `PlatformTenantDataDeletion` implementations and call them uniformly without knowing service internals.
