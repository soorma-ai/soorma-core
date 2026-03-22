# Component Dependencies
## Initiative: Multi-Tenancy Model Implementation
**Date**: 2026-03-22

---

## Dependency Matrix

| Consumer | Depends On | What it uses |
|---|---|---|
| `services/registry` | `soorma-service-common` | `TenancyMiddleware`, `get_platform_tenant_id` |
| `services/memory` | `soorma-service-common` | `TenancyMiddleware`, `get_tenanted_db`, `get_platform_tenant_id`, `get_service_tenant_id`, `get_service_user_id`, `PlatformTenantDataDeletion` (ABC) |
| `services/tracker` | `soorma-service-common` | `TenancyMiddleware`, `get_tenanted_db`, `get_platform_tenant_id`, `get_service_tenant_id`, `get_service_user_id`, `PlatformTenantDataDeletion` (ABC) |
| `soorma-service-common` | `soorma-common` | `DEFAULT_PLATFORM_TENANT_ID` constant |
| `sdk/python` | `soorma-common` | `DEFAULT_PLATFORM_TENANT_ID` constant, shared DTOs, `EventEnvelope` |
| `services/memory` | `soorma-common` | Shared DTOs (SemanticMemoryCreate, etc.) |
| `services/tracker` | `soorma-common` | Shared TrackerDTOs, `EventEnvelope` |
| `services/registry` | `soorma-common` | AgentDefinition, EventSchema DTOs |

**Key constraints**:
- `sdk/python` MUST NOT depend on `soorma-service-common` (would introduce FastAPI into SDK)
- `soorma-common` MUST NOT depend on `soorma-service-common` (would contaminate shared DTO lib)
- Services depend on `soorma-service-common` but NEVER import from each other

---

## Dependency Graph (text)

```
soorma-common  (no service or SDK dependencies)
    |
    +--- soorma-service-common  (depends on: soorma-common, FastAPI, SQLAlchemy)
    |       |
    |       +---[TenancyMiddleware, get_tenanted_db, PlatformTenantDataDeletion]
    |       |
    |       +---> services/registry   (TenancyMiddleware + get_platform_tenant_id only)
    |       +---> services/memory     (TenancyMiddleware + get_tenanted_db + deletion ABC)
    |       +---> services/tracker    (TenancyMiddleware + get_tenanted_db + deletion ABC)
    |
    +--- sdk/python  (depends on: soorma-common, httpx — NO FastAPI)
            |
            +--- [MemoryServiceClient, TrackerServiceClient]  (low-level HTTP clients)
            +--- [PlatformContext wrappers]                   (agent-facing API)
```

---

## Update Dependency Sequence

Because this is a breaking change, components must be updated in this order:

```
[1] soorma-common
      └── Add DEFAULT_PLATFORM_TENANT_ID → unblocks everything else

[2a] soorma-service-common  (parallel with [2b])
      └── Implement TenancyMiddleware, get_tenanted_db, PlatformTenantDataDeletion ABC
          → unblocks: memory service, tracker service, registry service middleware adoption

[2b] services/registry  (parallel with [2a])
      └── UUID→VARCHAR migration + adopt soorma-service-common
          → depends on [1] only; independent of soorma-service-common until adoption

[3a] services/memory  (parallel with [3b], after [1] + [2a])
      └── Schema restructure + RLS rebuild + MemoryDataDeletion

[3b] services/tracker  (parallel with [3a], after [1] + [2a])
      └── Column renames + TrackerDataDeletion

[4]  sdk/python  (after [3a] + [3b] API surfaces are stable)
      └── Client init-time platform_tenant_id + per-call service tenant/user rename
```

---

## Communication Patterns

### Pattern 1: HTTP API path (Memory, Tracker, Registry)
```
Client request (X-Tenant-ID, X-Service-Tenant-ID, X-User-ID headers)
    → TenancyMiddleware (request.state populated)
    → FastAPI route dependency (get_tenanted_db → set_config → RLS active)
    → Service/CRUD layer (composite key in all WHERE clauses)
    → PostgreSQL (RLS policy enforced by engine)
```

### Pattern 2: NATS event path (Tracker only)
```
NATS message (EventEnvelope)
    → _dispatch() → handle_action_request/result/plan_event(event, db)
    → platform_tenant_id = DEFAULT_PLATFORM_TENANT_ID
    → service_tenant_id  = event.tenant_id
    → service_user_id    = event.user_id
    → call set_config helper (inline, mirrors get_tenanted_db)
    → CRUD upsert/update with composite key
```

### Pattern 3: SDK agent handler path
```
Agent handler receives EventEnvelope (from NATS subscription)
    → context.memory.store(key, value, service_tenant_id=event.tenant_id, service_user_id=event.user_id)
        → PlatformContext MemoryClient wrapper
        → MemoryServiceClient.set_plan_state(service_tenant_id, service_user_id, ...)
            → HTTP: X-Tenant-ID (from init-time platform_tenant_id)
                    X-Service-Tenant-ID (service_tenant_id)
                    X-User-ID (service_user_id)
```

---

## Data Flow: Identity Dimensions

```
X-Tenant-ID header ──────────────────────────────────────────────────────► platform_tenant_id
                     TenancyMiddleware (request.state)
                     ↓
X-Service-Tenant-ID header ──────────────────────────────────────────────► service_tenant_id
                     ↓
X-User-ID header ────────────────────────────────────────────────────────► service_user_id
                     ↓
         get_tenanted_db (set_config x3)
                     ↓
         PostgreSQL RLS policy enforcement
                     ↓
         All DB rows filtered by (platform_tenant_id, service_tenant_id, service_user_id)
```

---

## Security Constraint: Composite Key Enforcement

**Rule**: ALL database queries on service-tenant-scoped tables MUST include `platform_tenant_id` as a mandatory WHERE condition.

| Query type | Required WHERE columns |
|---|---|
| By service user | `platform_tenant_id AND service_tenant_id AND service_user_id` |
| By service tenant | `platform_tenant_id AND service_tenant_id` |
| By platform tenant | `platform_tenant_id` |
| Public knowledge | `platform_tenant_id AND is_public = TRUE` |

**Violation**: Any query using `service_tenant_id` alone (without `platform_tenant_id`) is a cross-tenant data leakage risk and MUST NOT exist anywhere in the codebase.
