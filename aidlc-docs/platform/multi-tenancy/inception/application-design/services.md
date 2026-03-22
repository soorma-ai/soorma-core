# Services
## Initiative: Multi-Tenancy Model Implementation
**Date**: 2026-03-22

> Service definitions, responsibilities, and orchestration patterns for the multi-tenancy model.

---

## S1 — `TenancyMiddleware` (soorma-service-common)

**Type**: Starlette BaseHTTPMiddleware (shared infrastructure service)

**Responsibility**: Per-request identity extraction from HTTP headers. Stores all three identity dimensions on `request.state` for downstream FastAPI dependency functions.

**Interaction pattern**:
```
HTTP Request
    → TenancyMiddleware.dispatch()
        → extract X-Tenant-ID         → request.state.platform_tenant_id
        → extract X-Service-Tenant-ID → request.state.service_tenant_id
        → extract X-User-ID           → request.state.service_user_id
    → call_next(request)  [next middleware or route handler]
```

**Registered in**: Memory Service, Tracker Service, Registry Service `main.py` via `app.add_middleware(TenancyMiddleware)`

**Notes**:
- Does NOT open a DB connection — header extraction only
- Any absent header uses a safe default (platform = `DEFAULT_PLATFORM_TENANT_ID`; service tenant/user = `None`)
- Registry Service registers this middleware but does not use `get_tenanted_db` (no RLS)

---

## S2 — `get_tenanted_db` dependency (soorma-service-common)

**Type**: FastAPI async dependency (DB session provider with RLS activation)

**Responsibility**: Bridges HTTP identity context into PostgreSQL row-level security. Wraps the standard `get_db` session generator; before yielding the session, executes `set_config` for all three session variables so RLS policies enforce on every subsequent query in the same transaction.

**Interaction pattern**:
```
Route handler depends on get_tenanted_db
    → reads request.state.{platform,service_tenant,service_user}_id
    → opens AsyncSession via get_db
    → executes:
        SELECT set_config('app.platform_tenant_id', ..., true)
        SELECT set_config('app.service_tenant_id',  ..., true)
        SELECT set_config('app.service_user_id',    ..., true)
    → yields session [RLS now active for this transaction]
    → route handler runs DB queries (RLS enforced automatically by PostgreSQL)
    → session commits / rolls back
```

**Used by**: Memory Service CRUD endpoints, Tracker Service query endpoints
**Not used by**: Registry Service (no RLS tables), Tracker NATS event handlers (no HTTP context)

---

## S3 — `PlatformTenantDataDeletion` service (soorma-service-common + per-service impls)

**Type**: Abstract service interface + per-service concrete implementations

**Responsibility**: GDPR-compliant data deletion across service data stores, scoped to the platform tenant namespace. Ensures complete erasure at three granularities: platform tenant, service tenant, service user.

**Interaction pattern**:
```
GDPR deletion request (future API endpoint or internal call)
    → MemoryDataDeletion.delete_by_service_user(db, platform_tenant_id, service_tenant_id, service_user_id)
        → DELETE FROM semantic_memory   WHERE platform_tenant_id = ? AND service_tenant_id = ? AND service_user_id = ?
        → DELETE FROM episodic_memory   WHERE ...
        → DELETE FROM procedural_memory WHERE ...
        → DELETE FROM working_memory    WHERE ...
        → DELETE FROM task_context      WHERE ...
        → DELETE FROM plan_context      WHERE ...
        → return total rows deleted
    → TrackerDataDeletion.delete_by_service_user(db, ...)
        → DELETE FROM plan_progress   WHERE ...
        → DELETE FROM action_progress WHERE ...
        → return total rows deleted
```

**Concrete implementations**:
- `MemoryDataDeletion` in `services/memory/src/memory_service/services/data_deletion.py`
- `TrackerDataDeletion` in `services/tracker/src/tracker_service/services/data_deletion.py`

**Exposed via**: Internal API endpoints in Memory Service and Tracker Service (callable by a future GDPR coordinator; not publicly exposed in this scope)

---

## S4 — Registry Service (identity layer update)

**Type**: Existing FastAPI service (modified)

**Responsibility**: Manage agent, event, and schema registrations scoped to a platform tenant. The only tenancy dimension relevant to Registry is `platform_tenant_id`.

**Changes**:
- Remove UUID validation from `X-Tenant-ID` header processing
- Replace `get_developer_tenant_id()` with `get_platform_tenant_id()` from `soorma-service-common`
- `TenancyMiddleware` registered but `get_tenanted_db` NOT used (no RLS)
- Alembic migration: `tenant_id UUID → VARCHAR(64)` on all tables

**Interaction pattern** (unchanged shape, updated types):
```
POST /v1/agents  →  platform_tenant_id: str = Depends(get_platform_tenant_id)
                 →  AgentCRUD.create(db, platform_tenant_id, agent_data)
```

---

## S5 — Memory Service (schema + RLS service)

**Type**: Existing FastAPI service (modified)

**Responsibility**: CoALA memory operations scoped by three-column composite key. RLS policies enforce isolation at DB level. `TenancyMiddleware` + `get_tenanted_db` together ensure policies are always active before any query.

**Orchestration sequence per request**:
```
POST /v1/memory/semantic
    → TenancyMiddleware: extract headers → request.state
    → get_tenant_context(request, db=Depends(get_tenanted_db)):
        → get_tenanted_db: set_config x3 → session with active RLS
        → build TenantContext(platform_tenant_id, service_tenant_id, service_user_id, db)
    → SemanticCRUD.create(db, platform_tenant_id, service_tenant_id, service_user_id, data)
        → INSERT INTO semantic_memory (platform_tenant_id, service_tenant_id, service_user_id, ...)
        → PostgreSQL RLS policy checks current_setting('app.platform_tenant_id') == row.platform_tenant_id
```

---

## S6 — Tracker Service (schema + event subscriber update)

**Type**: Existing FastAPI service + NATS event subscriber (modified)

**Responsibility**: Record and query plan/action execution state. Two inbound paths: HTTP API (uses middleware + `get_tenanted_db`) and NATS event subscriptions (uses `EventEnvelope` fields for service tenant/user; `platform_tenant_id` defaults to `DEFAULT_PLATFORM_TENANT_ID`).

**Dual-path orchestration**:

*API path*:
```
GET /v1/tracker/plans/{plan_id}
    → TenancyMiddleware: headers → request.state
    → get_tenanted_db: set_config → active RLS session
    → TrackerQueryCRUD.get_plan(db, platform_tenant_id, service_tenant_id, service_user_id, plan_id)
```

*NATS event path*:
```
NATS: soorma.events.action-requests
    → EventEnvelope.model_validate(message)
    → platform_tenant_id = DEFAULT_PLATFORM_TENANT_ID  (NATS has no auth channel today)
    → service_tenant_id  = event.tenant_id
    → service_user_id    = event.user_id
    → ActionProgressCRUD.upsert(db, platform_tenant_id, service_tenant_id, service_user_id, ...)
    → NOTE: set_config must also be called on the NATS-path DB session (no middleware here)
            → handled by a helper that mimics get_tenanted_db behavior inline
```
