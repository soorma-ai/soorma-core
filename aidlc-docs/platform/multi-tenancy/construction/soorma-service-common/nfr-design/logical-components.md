# Logical Components — soorma-service-common (U2)
## Initiative: Multi-Tenancy Model Implementation
**Date**: 2026-03-22

---

## Overview

`soorma-service-common` is a stateless Python library. There are no infrastructure services, queues, caches, or databases owned by this library. Its logical components are code modules within the library itself.

---

## Component Map

```
libs/soorma-service-common/
└── src/soorma_service_common/
    │
    ├── middleware.py         ─── [L1] Header Extraction Layer
    │                             (TenancyMiddleware)
    │
    ├── dependencies.py       ─── [L2] RLS Activation Layer
    │                             (get_platform_tenant_id, get_service_tenant_id,
    │                              get_service_user_id, get_tenanted_db,
    │                              set_config_for_session)
    │
    ├── tenant_context.py     ─── [L3] Identity Bundle Layer
    │                             (TenantContext, get_tenant_context)
    │
    ├── deletion.py           ─── [L4] GDPR Deletion Interface
    │                             (PlatformTenantDataDeletion ABC)
    │
    └── __init__.py           ─── [L0] Public API
                                  (exports from L1–L4)
```

---

## [L1] Header Extraction Layer — `middleware.py`

**Runtime position**: Starlette ASGI middleware stack (executes before FastAPI routing)
**Inputs**: HTTP request headers (`X-Tenant-ID`, `X-Service-Tenant-ID`, `X-User-ID`)
**Outputs**: `request.state.platform_tenant_id`, `request.state.service_tenant_id`, `request.state.service_user_id`
**Dependencies**: `soorma_common.tenancy.DEFAULT_PLATFORM_TENANT_ID`
**No DB interaction**: By design (NFR-U2-SEC-01; Q1 resolution)

**Registration pattern** (in each consuming service's `main.py`):
```python
app.add_middleware(TenancyMiddleware)
```

---

## [L2] RLS Activation Layer — `dependencies.py`

**Runtime position**: FastAPI dependency injection (executes during route handler resolution)
**Sub-components**:

| Function | Inputs | Output | Purpose |
|----------|--------|--------|---------|
| `get_platform_tenant_id` | `request` | `str` | Read `request.state.platform_tenant_id` |
| `get_service_tenant_id` | `request` | `Optional[str]` | Read `request.state.service_tenant_id` |
| `get_service_user_id` | `request` | `Optional[str]` | Read `request.state.service_user_id` |
| `get_tenanted_db` | `request`, `db=Depends(get_db)` | `AsyncGenerator[AsyncSession, None]` | Calls `set_config` x3, yields session |
| `set_config_for_session` | `db`, `platform_tenant_id`, `service_tenant_id`, `service_user_id` | `None` | NATS-path `set_config` helper |

**Dependencies**: `request.state` (set by [L1]), `get_db` (injected by calling service), `sqlalchemy.text`

---

## [L3] Identity Bundle Layer — `tenant_context.py`

**Runtime position**: FastAPI dependency injection (depends on [L2])
**Components**:

| Component | Type | Purpose |
|-----------|------|---------|
| `TenantContext` | `@dataclass` | Bundles platform_tenant_id + service_tenant_id + service_user_id + db |
| `get_tenant_context` | FastAPI async generator dependency | Assembles `TenantContext` from `request.state` + `get_tenanted_db` |

**Usage**: Route handlers in Memory and Tracker services use `ctx: TenantContext = Depends(get_tenant_context)` as their single identity/DB dependency.

---

## [L4] GDPR Deletion Interface — `deletion.py`

**Runtime position**: N/A — abstract base class, not instantiated in this library
**Components**:

| Component | Type | Purpose |
|-----------|------|---------|
| `PlatformTenantDataDeletion` | `ABC` | Defines 3-method deletion contract |

**Concrete impls**:
- `MemoryDataDeletion` (defined in U4 — services/memory)
- `TrackerDataDeletion` (defined in U5 — services/tracker)

---

## External Infrastructure Components Used (NOT owned by U2)

| Component | Owner | Used by U2 via |
|-----------|-------|---------------|
| PostgreSQL | Each service | AsyncSession from caller's `get_db` |
| Connection Pool | Each service | sqlalchemy async_sessionmaker |
| FastAPI app | Each service | Middleware registration, Depends |
| NATS | soorma-nats / event-service | Not used by library itself; pattern documented for consumers |

---

## No New Infrastructure Required

`soorma-service-common` introduces zero new infrastructure components. It is a pure Python library that:
- Reads from HTTP headers (in-process)
- Makes SQL calls over the existing database connection managed by the consuming service
- Defines interfaces for downstream implementations

No additional cloud resources, queues, caches, or services are needed as a result of U2.
