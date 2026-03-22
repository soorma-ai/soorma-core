# Units of Work
## Initiative: Multi-Tenancy Model Implementation
**Date**: 2026-03-22

> Defines each unit of work, its construction scope, and integration test boundaries.
> Execution order: Wave-based (Q1=B). Integration tests include completed dependency units per unit (Q2=B).

---

## Execution Waves

```
Wave 1:  U1  (soorma-common)
              └── unblocks everything

Wave 2:  U2  (soorma-service-common)  ∥  U3  (services/registry)
              └── U2 unblocks Wave 3      └── independent of U2

Wave 3:  U4  (services/memory)  ∥  U5  (services/tracker)  ∥  U7  (services/event-service)
              └── all depend on U1 + U2

Wave 4:  U6  (sdk/python)
              └── depends on U4 + U5 API surfaces being stable
```

---

## U1 — `libs/soorma-common`

| Attribute | Value |
|---|---|
| **Wave** | 1 |
| **Change Type** | Minor |
| **Depends On** | — |
| **Unblocks** | U2, U3, U4, U5, U6, U7 |

**Scope**:
- Add `DEFAULT_PLATFORM_TENANT_ID` constant + `SOORMA_PLATFORM_TENANT_ID` env var override in `soorma_common/tenancy.py` (new module)
- Add `platform_tenant_id: Optional[str]` field to `EventEnvelope` with docstring marking it as Event-Service-injected only
- Update `EventEnvelope` field docstrings for `tenant_id` (→ service tenant) and `user_id` (→ service user)

**Construction Stages**:
- Functional Design: YES — new module + field on shared DTO
- NFR Requirements: NO
- NFR Design: NO
- Infrastructure Design: NO
- Code Generation: YES

**Integration Test Scope** (Q2=B):
- No dependency units to integrate with — unit tests only

---

## U2 — `libs/soorma-service-common`

| Attribute | Value |
|---|---|
| **Wave** | 2 |
| **Change Type** | Major — new library |
| **Depends On** | U1 |
| **Unblocks** | U4, U5, U7 |

**Scope**:
- Create new Poetry library at `libs/soorma-service-common/`
- Implement `TenancyMiddleware` (Starlette `BaseHTTPMiddleware`) — header extraction to `request.state`
- Implement `get_tenanted_db` FastAPI dependency — wraps `get_db`, calls `set_config` x3 transaction-scoped
- Implement `get_platform_tenant_id`, `get_service_tenant_id`, `get_service_user_id` dependency functions
- Implement `set_config_for_session` helper for NATS-path DB sessions (no HTTP request object)
- Implement `TenantContext` dataclass + `get_tenant_context` FastAPI dependency (convenience bundle: all 3 identity dims + tenanted DB session)
- Implement `PlatformTenantDataDeletion` abstract base class (3 abstract methods)

**Construction Stages**:
- Functional Design: YES — new middleware contract, `set_config` transaction model, `TenantContext` bundle, ABC interface
- NFR Requirements: YES — RLS activation is a security NFR (set_config must fire before every query)
- NFR Design: YES — `set_config` transaction-scoping pattern, session variable lifecycle, RLS policy activation guarantee
- Infrastructure Design: NO
- Code Generation: YES

**Integration Test Scope** (Q2=B):
- Unit tests: `TenancyMiddleware` header extraction, `get_tenanted_db` set_config calls (mocked DB)
- Integration with U1: `TenancyMiddleware` defaults to `DEFAULT_PLATFORM_TENANT_ID` from `soorma_common` when header absent

---

## U3 — `services/registry`

| Attribute | Value |
|---|---|
| **Wave** | 2 (parallel with U2) |
| **Change Type** | Moderate |
| **Depends On** | U1 |
| **Unblocks** | — |

**Scope**:
- Alembic migration: `tenant_id UUID → VARCHAR(64)` on `AgentTable`, `EventTable`, `SchemaTable` (using `::text` cast)
- Update ORM mapped columns from `Uuid(as_uuid=True)` to `String(64)`
- Remove `get_developer_tenant_id()` from `registry_service/api/dependencies.py`; replace with `get_platform_tenant_id()` imported from `soorma-service-common`
- Register `TenancyMiddleware` from `soorma-service-common` in `main.py`
- Update all CRUD, service layer, and API functions: `tenant_id: UUID` → `platform_tenant_id: str`
- Remove `IS_LOCAL_TESTING` / SQLite path from `config.py` and `database.py`
- Update Registry tests: use `spt_00000000-0000-0000-0000-000000000000` format

**Construction Stages**:
- Functional Design: YES — migration strategy, ORM type changes, UUID→VARCHAR impact
- NFR Requirements: NO
- NFR Design: NO
- Infrastructure Design: NO
- Code Generation: YES

**Integration Test Scope** (Q2=B):
- Unit tests: ORM type changes, dependency injection
- Integration with U1: `get_platform_tenant_id()` returns correct type; `DEFAULT_PLATFORM_TENANT_ID` constant available
- **Note**: U3 does NOT integrate with U2 at test time — Registry adopts `soorma-service-common` for `TenancyMiddleware` + `get_platform_tenant_id`, but both U2 and U3 are in Wave 2. Registry integration tests with U2 middleware are run as part of U3's Build and Test once U2 is complete.

---

## U4 — `services/memory`

| Attribute | Value |
|---|---|
| **Wave** | 3 (parallel with U5, U7) |
| **Change Type** | Major |
| **Depends On** | U1, U2 |
| **Unblocks** | U6 |

**Scope**:
- Alembic migration: drop `tenants` and `users` reference tables; drop all FK constraints; add `platform_tenant_id VARCHAR(64) NOT NULL`; rename `tenant_id UUID FK → service_tenant_id VARCHAR(64)`; rename `user_id UUID FK → service_user_id VARCHAR(64)` on all 8 tables (`semantic_memory`, `episodic_memory`, `procedural_memory`, `working_memory`, `task_context`, `plan_context`, `sessions`, `plans`)
- Update ORM models: replace UUID FK columns with `String(64)` plain columns for all three IDs
- Drop all existing RLS policies (reference `::UUID` — invalid after migration)
- Rebuild RLS policies: string comparison on `current_setting('app.platform_tenant_id', true)` etc. for all 8 tables
- Replace local `TenancyMiddleware` with shared one from `soorma-service-common`; register `TenancyMiddleware` in `main.py`
- Replace existing `TenantContext` / `get_tenant_context` in `memory_service/core/dependencies.py` with re-export from `soorma-service-common`
- Switch all `Depends(get_db)` to `Depends(get_tenanted_db)` in route handlers (via `get_tenant_context`)
- Update all Memory Service service layer functions: `(tenant_id, user_id)` → `(platform_tenant_id, service_tenant_id, service_user_id)`
- Update Memory Service API DTOs and request/response models
- Implement `MemoryDataDeletion` (concrete `PlatformTenantDataDeletion`) covering all 6 memory tables + deletion API endpoint
- Update `settings.default_tenant_id` default to `spt_00000000-0000-0000-0000-000000000000`
- Update all Memory Service tests

**Construction Stages**:
- Functional Design: YES — schema restructure, RLS policy expressions, `MemoryDataDeletion` method contracts
- NFR Requirements: YES — RLS enforcement is a security NFR (previously unenforced)
- NFR Design: YES — RLS policy implementation, `set_config` activation via `get_tenanted_db`, composite key enforcement
- Infrastructure Design: NO
- Code Generation: YES

**Integration Test Scope** (Q2=B):
- Unit tests: ORM models, CRUD logic, service layer, deletion methods
- Integration with U2: real `TenancyMiddleware` + `get_tenanted_db` — verify `set_config` fires and RLS policies enforce correctly (cross-tenant isolation test: query with wrong `platform_tenant_id` returns zero rows)
- Integration with U1: `DEFAULT_PLATFORM_TENANT_ID` constant used in test fixtures

---

## U5 — `services/tracker`

| Attribute | Value |
|---|---|
| **Wave** | 3 (parallel with U4, U7) |
| **Change Type** | Moderate |
| **Depends On** | U1, U2 |
| **Unblocks** | U6 |

**Scope**:
- Alembic migration: rename `tenant_id → service_tenant_id`, `user_id → service_user_id`; add `platform_tenant_id VARCHAR(64) NOT NULL` on `plan_progress` and `action_progress`; enforce `VARCHAR(64)` length
- Update ORM models (`tracker_service/models/db.py`)
- Register `TenancyMiddleware` from `soorma-service-common` in `main.py`
- Replace per-route header parsing (`x_tenant_id: str = Header(...)`) with `TenantContext` / `get_tenant_context` from `soorma-service-common` in all API route handlers
- Update Tracker API query endpoints: filter by `(platform_tenant_id, service_tenant_id, service_user_id)`
- Update NATS event handlers (`event_handlers.py`): extract `platform_tenant_id` from `event.platform_tenant_id` (trusted, from Event Service); call `set_config_for_session` from `soorma-service-common` before DB queries
- Implement `TrackerDataDeletion` (concrete `PlatformTenantDataDeletion`) covering `plan_progress` + `action_progress`
- Update all Tracker tests

**Construction Stages**:
- Functional Design: YES — column rename migration, NATS-path tenant extraction, `TrackerDataDeletion` contracts
- NFR Requirements: NO (no new RLS — Tracker tables don't have RLS policies today; composite key enforcement is in CRUD layer)
- NFR Design: NO
- Infrastructure Design: NO
- Code Generation: YES

**Integration Test Scope** (Q2=B):
- Unit tests: ORM models, query filters, NATS handler logic, deletion methods
- Integration with U2: real `TenancyMiddleware` + `get_tenant_context` — verify three identity dims extracted and routed correctly in API path; `set_config_for_session` called in NATS path
- Integration with U1: `DEFAULT_PLATFORM_TENANT_ID` in test fixtures; `EventEnvelope.platform_tenant_id` field available

---

## U6 — `sdk/python`

| Attribute | Value |
|---|---|
| **Wave** | 4 |
| **Change Type** | Moderate |
| **Depends On** | U4, U5 |
| **Unblocks** | — |

**Scope**:
- Update `MemoryServiceClient.__init__`: accept `platform_tenant_id: Optional[str]`; default to `DEFAULT_PLATFORM_TENANT_ID` / `SOORMA_PLATFORM_TENANT_ID` env var; send as `X-Tenant-ID` on every request
- Rename per-call params: `tenant_id → service_tenant_id`, `user_id → service_user_id` across all `MemoryServiceClient` methods; send as `X-Service-Tenant-ID` / `X-User-ID` headers
- Apply same changes to `TrackerServiceClient`
- Update PlatformContext `MemoryClient` wrapper (`context.memory`): rename `tenant_id → service_tenant_id`, `user_id → service_user_id` on all wrapper methods; `platform_tenant_id` is never a parameter — set on the underlying client at init time
- Update `cli/commands/init.py` to use `DEFAULT_PLATFORM_TENANT_ID` constant
- Update all SDK tests to use new two-parameter tenant model
- Update `docs/ARCHITECTURE_PATTERNS.md` Section 1: two-tier tenancy model, header table, `platform_tenant_id` injection note for EventEnvelope

**Construction Stages**:
- Functional Design: YES — client init vs per-call parameter boundary, wrapper parameter renaming
- NFR Requirements: NO
- NFR Design: NO
- Infrastructure Design: NO
- Code Generation: YES

**Integration Test Scope** (Q2=B):
- Unit tests: client init, header construction, wrapper delegation
- Integration with U4 (Memory Service): end-to-end store + retrieve with two-tier tenant context; verify `X-Tenant-ID` + `X-Service-Tenant-ID` + `X-User-ID` headers accepted by updated Memory Service
- Integration with U5 (Tracker Service): end-to-end plan/action progress query with two-tier context

---

## U7 — `services/event-service`

| Attribute | Value |
|---|---|
| **Wave** | 3 (parallel with U4, U5) |
| **Change Type** | Minor |
| **Depends On** | U1, U2 |
| **Unblocks** | — |

**Scope**:
- Register `TenancyMiddleware` from `soorma-service-common` in `services/event-service/src/main.py`
- Update `publish_event` route signature: add `http_request: Request` parameter alongside existing `request: PublishRequest`; rename existing param to `publish_request` to avoid collision
- Inject `event.platform_tenant_id = get_platform_tenant_id(http_request)` before publishing to NATS — overwrites any SDK-supplied value
- Update Event Service tests to verify `platform_tenant_id` injection

**Construction Stages**:
- Functional Design: YES — route signature change, injection point, trust model
- NFR Requirements: YES — `platform_tenant_id` injection is a security requirement (prevents SDK from forging a different platform tenant)
- NFR Design: YES — trust boundary design: Event Service as sole authority for `platform_tenant_id` in event bus
- Infrastructure Design: NO
- Code Generation: YES

**Integration Test Scope** (Q2=B):
- Unit tests: `platform_tenant_id` injection, overwrite of SDK-supplied value
- Integration with U2: real `TenancyMiddleware` extracts `X-Tenant-ID` → `request.state.platform_tenant_id`; verify injection onto published `EventEnvelope`
- Integration with U1: `EventEnvelope.platform_tenant_id` field exists and is settable
