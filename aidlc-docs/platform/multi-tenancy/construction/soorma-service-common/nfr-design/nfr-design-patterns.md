# NFR Design Patterns — soorma-service-common (U2)
## Initiative: Multi-Tenancy Model Implementation
**Date**: 2026-03-22

---

## Pattern 1: Transaction-Scoped RLS Activation (addresses NFR-U2-SEC-01, NFR-U2-SEC-02)

### Problem
PostgreSQL RLS policies evaluate `current_setting('app.platform_tenant_id', true)` at query execution time. If this session variable is not set — or is stale from a previous request on a reused connection pool connection — the query either fails or returns wrong data.

### Design Decision
Use PostgreSQL `set_config(key, value, is_local)` with `is_local = true`. This is the **transaction-local** variant:
- The value is active for the current transaction only
- When the transaction commits or rolls back, the session variable reverts to its previous value
- Connection pool connections can be safely reused — the next transaction starts with clean state

### Implementation Model
```
FastAPI request lifecycle:

[1] HTTP request arrives
[2] TenancyMiddleware extracts headers → request.state (no DB)
[3] Route handler invoked via FastAPI
[4] get_tenanted_db dependency:
    [4a] get_db() opens AsyncSession (from connection pool)
    [4b] db.execute(text("SELECT set_config('app.platform_tenant_id', :v, true)"), {"v": ptid})
    [4c] db.execute(text("SELECT set_config('app.service_tenant_id',  :v, true)"), {"v": stid or ''})
    [4d] db.execute(text("SELECT set_config('app.service_user_id',    :v, true)"), {"v": suid or ''})
    [4e] yield db  ← RLS active on this connection/transaction
[5] Route handler executes ORM queries (RLS enforced automatically by PostgreSQL)
[6] Transaction commits (or rolls back on exception)
[7] Session variables revert to pre-transaction state
[8] Connection returned to pool with clean state
```

### Why NOT session-scoped (is_local = false)
Session-scoped `set_config` persists across transaction boundaries. In a connection pool:
- Request A sets `app.platform_tenant_id = 'tenant-A'`; transaction commits
- Connection returned to pool; next connection acquisition picks it up
- Request B uses the connection — `app.platform_tenant_id` is still `'tenant-A'` at the PostgreSQL level
- If Request B's middleware fails before setting the variable, it inherits tenant-A's identity
- **This is a critical cross-tenant data exposure vulnerability**

Transaction-scoped (`is_local = true`) is the only safe choice with connection pooling.

---

## Pattern 2: Responsibility Split — Middleware + Dependency (addresses Q1 design decision)

### Problem
RLS requires a DB session to call `set_config`. Middleware in Starlette runs OUTSIDE the FastAPI dependency lifecycle — there is no clean way to acquire, use, and release a DB session within `BaseHTTPMiddleware.dispatch()` without leaking connections or causing double-commit issues.

### Design Decision
Split responsibility across two layers:
- **`TenancyMiddleware`** (Starlette, pre-dependency): header extraction ONLY → `request.state`
- **`get_tenanted_db`** (FastAPI dependency, post-middleware): reads `request.state` → calls `set_config` → yields session

### Why this is safe
The Starlette middleware chain is guaranteed to run before FastAPI resolves dependencies. By the time `get_tenanted_db` is called, `TenancyMiddleware` has already populated `request.state` with all three identity values. There is no race condition.

### Sequence
```
Request arrives
    ↓ Starlette ASGI middleware stack
TenancyMiddleware.dispatch() → sets request.state
    ↓
FastAPI routing + dependency resolution
get_tenanted_db(request, db=Depends(get_db))
    → reads request.state.platform_tenant_id (guaranteed present from middleware)
    → calls set_config x3
    → yields db
    ↓
Route handler executes
```

---

## Pattern 3: NATS-Path RLS Activation (addresses set_config_for_session design)

### Problem
NATS event handlers (Tracker service) are not HTTP request handlers — there is no Starlette middleware, no `request` object, and no FastAPI dependency injection. But they still need to call `set_config` before any RLS-protected DB query.

### Design Decision
Provide `set_config_for_session(db, platform_tenant_id, service_tenant_id, service_user_id)` — a standalone async function with the same `set_config` logic as `get_tenanted_db`, but accepting a bare `AsyncSession` and the three identity values explicitly.

NATS handlers extract identity values from the `EventEnvelope` fields:
- `event.platform_tenant_id` — injected by Event Service from `X-Tenant-ID` header (trusted)
- `event.tenant_id` → `service_tenant_id`
- `event.user_id` → `service_user_id`

### Implementation model
```python
# NATS handler pattern
async def handle_task_event(event: EventEnvelope):
    async with get_db_session() as db:  # service-local get_db
        await set_config_for_session(
            db,
            platform_tenant_id=event.platform_tenant_id or DEFAULT_PLATFORM_TENANT_ID,
            service_tenant_id=event.tenant_id,
            service_user_id=event.user_id,
        )
        # DB queries now RLS-protected
        await crud.record_progress(db, ...)
```

### Trust model for NATS path
`event.platform_tenant_id` is trusted because:
- It is injected/overwritten by the authenticated Event Service at publish time
- SDK agents cannot fake it (Event Service overwrites any SDK-supplied value)
- For the current architecture (v0.7.x), if `event.platform_tenant_id` is None (e.g., direct NATS publish without Event Service), fall back to `DEFAULT_PLATFORM_TENANT_ID`

---

## Pattern 4: Composite Key Identity Scope (addresses NFR-U2-SEC-03)

### Problem
Using only `service_tenant_id` as the isolation key across services is insufficient — two different platform tenants could have the same `service_tenant_id` value, creating cross-tenant access.

### Design Decision
All DB identity scoping uses the three-column composite: `(platform_tenant_id, service_tenant_id, service_user_id)`. The library enforces this at the contract level:
- `TenantContext` always carries all three dimensions
- `PlatformTenantDataDeletion` methods always require `platform_tenant_id` as the outer scope
- RLS policies (defined per-service, in U4/U5) use all three `current_setting` vars

### Defence-in-Depth
```
Layer 1 (Application code): Service layer functions receive all three IDs explicitly — WHERE clause includes all three
Layer 2 (PostgreSQL RLS): RLS policies enforce isolation via session variables — platform_tenant_id is always checked
```

Both layers must be enforced; neither alone is sufficient (application code can have bugs; RLS is the last line of defence).

---

## Pattern 5: None-to-Empty-String Sentinel Conversion

### Problem
Python's `Optional[str]` allows `None` for absent headers. PostgreSQL's `set_config` does not accept `NULL` — it raises an error. RLS policies need a deterministic string value to compare against.

### Design Decision
Convert `None` to `''` (empty string) at the boundary in `get_tenanted_db` and `set_config_for_session`. RLS policies handle empty string as "no filter applies for this dimension" — appropriate for services (e.g., Registry) that don't use `service_tenant_id`.

### Implementation
```python
service_tenant_id_val = service_tenant_id or ''
service_user_id_val   = service_user_id   or ''
await db.execute(text("SELECT set_config('app.service_tenant_id', :v, true)"), {"v": service_tenant_id_val})
await db.execute(text("SELECT set_config('app.service_user_id',   :v, true)"), {"v": service_user_id_val})
```
