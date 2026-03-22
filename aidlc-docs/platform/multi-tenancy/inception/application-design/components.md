# Components
## Initiative: Multi-Tenancy Model Implementation
**Date**: 2026-03-22

---

## Component Overview

This initiative touches 7 components across 4 packages. One new library is created; all others are modified in-place.

---

## C1 — `libs/soorma-common` (modified)

**Purpose**: Shared constants and DTOs used by both SDK and backend services. No FastAPI/Starlette dependencies (SDK compatibility constraint).

**Responsibilities**:
- Provide the authoritative `DEFAULT_PLATFORM_TENANT_ID` constant
- Allow runtime override via `SOORMA_PLATFORM_TENANT_ID` env var
- Add `platform_tenant_id: Optional[str]` field to `EventEnvelope` — set server-side by Event Service only; SDK agents MUST NOT populate it
- Update `EventEnvelope` field docstrings: `platform_tenant_id` = Event Service injected; `tenant_id` = service tenant; `user_id` = service user
- Carry no format validation on tenant/user IDs — pure opaque strings

**Boundaries**:
- MUST NOT import FastAPI, Starlette, or any HTTP framework dependency
- MUST NOT add middleware or database logic
- Used by: SDK clients, all backend services, event handlers

---

## C2 — `libs/soorma-service-common` (NEW)

**Purpose**: Shared FastAPI/Starlette infrastructure for all backend services. Centralises identity extraction, PostgreSQL session variable activation, and the GDPR deletion interface. Cannot be used by the SDK (would contaminate its dependency graph with FastAPI).

**Responsibilities**:
- `TenancyMiddleware` — extracts all three identity dimensions from HTTP headers; sets `request.state`; calls PostgreSQL `set_config` NOT called here (see Q1 decision: responsibility split)
- `get_tenanted_db` FastAPI dependency — wraps `get_db`; calls `set_config` for all three session variables before yielding the DB session (transaction-scoped)
- FastAPI dependency functions: `get_platform_tenant_id`, `get_service_tenant_id`, `get_service_user_id` — read from `request.state`
- `TenantContext` dataclass + `get_tenant_context` dependency — convenience bundle combining all three identity dimensions with a tenanted DB session; single `Depends()` used in every Memory/Tracker route handler instead of four separate injections
- `PlatformTenantDataDeletion` abstract base class — defines the deletion interface; concrete implementations live in each service

**Boundaries**:
- MAY import FastAPI, Starlette, SQLAlchemy async
- MUST NOT import SDK packages or service-specific code
- Consumed by: Memory Service, Tracker Service, Registry Service

---

## C3 — `services/registry` (modified)

**Purpose**: Developer-facing service registry. Platform tenant scoped only — no service tenant or service user concept. Manages agent, event, and schema registrations.

**Responsibilities**:
- Accept `platform_tenant_id` as an opaque string (was: strict UUID)
- Use `TenancyMiddleware` from `soorma-service-common` for header extraction (no `set_config` — Registry has no RLS tables)
- Use `get_platform_tenant_id()` from `soorma-service-common` as the FastAPI dependency for `X-Tenant-ID`
- Store `platform_tenant_id` as `VARCHAR(64)` on `AgentTable`, `EventTable`, `SchemaTable`
- Remove `IS_LOCAL_TESTING` / SQLite path — PostgreSQL only

**Boundaries**:
- Only extracts `platform_tenant_id`; `service_tenant_id` / `service_user_id` are N/A
- No RLS policies; no `set_config`
- Connects to: PostgreSQL via asyncpg

---

## C4 — `services/memory` (modified)

**Purpose**: CoALA-framework multi-memory service. Stores and retrieves semantic, episodic, procedural, working, task-context, and plan-context memory. Scoped by the full three-column composite key.

**Responsibilities**:
- Accept all three identity dimensions via `TenancyMiddleware` from `soorma-service-common`
- Use `TenantContext` + `get_tenant_context` from `soorma-service-common` as the single `Depends()` bundle in every route handler
- Use `get_tenanted_db` dependency to call `set_config` transaction-scoped before every DB operation (activates RLS)
- Restructure all table schemas: drop `tenants`/`users` reference tables; replace UUID FKs with `(platform_tenant_id, service_tenant_id, service_user_id)` plain columns
- Rebuild all RLS policies using string comparison on `current_setting(...)` (no `::UUID` cast)
- Implement `MemoryDataDeletion` (concrete `PlatformTenantDataDeletion`) covering all 6 memory tables
- Provide internal deletion API endpoint wired to `MemoryDataDeletion`

**Boundaries**:
- All DB queries MUST include `platform_tenant_id` as a WHERE condition — partial keys are a security violation
- Service layer functions receive `(platform_tenant_id, service_tenant_id, service_user_id)` as explicit parameters — never inferred from global state

---

## C5 — `services/tracker` (modified)

**Purpose**: Plan and action progress tracking. Subscribes to NATS events (action-requests, action-results, system-events) to record execution state. Also supports direct API queries.

**Responsibilities**:
- Accept all three identity dimensions via `TenancyMiddleware` from `soorma-service-common`
- Use `TenantContext` + `get_tenant_context` from `soorma-service-common` as the single `Depends()` bundle in API route handlers
- Use `get_tenanted_db` dependency for `set_config` activation (consistent with Memory Service)
- Rename columns: `tenant_id → service_tenant_id`, `user_id → service_user_id`; add `platform_tenant_id VARCHAR(64) NOT NULL`
- Event subscribers extract `platform_tenant_id` from `event.platform_tenant_id` (trusted: injected by Event Service from `X-Tenant-ID` auth header before publishing to NATS). Service tenant/user from `event.tenant_id` / `event.user_id`. `set_config` called on the NATS-path DB session via `set_config_for_session` helper.
- Implement `TrackerDataDeletion` (concrete `PlatformTenantDataDeletion`) covering `plan_progress` and `action_progress` tables
- All query endpoints filter by `(platform_tenant_id, service_tenant_id, service_user_id)`

**Boundaries**:
- NATS event-driven path: `platform_tenant_id` defaults to `DEFAULT_PLATFORM_TENANT_ID` for now (no auth channel on NATS subscriptions in current architecture)
- API-driven path: `platform_tenant_id` comes from `request.state` (middleware-set)

---

## C6 — `sdk/python` — Service Clients (modified)

**Purpose**: Low-level HTTP clients (`MemoryServiceClient`, `TrackerServiceClient`) that call service APIs. Used directly by PlatformContext wrappers; agent handlers never import them.

**Responsibilities**:
- Set `platform_tenant_id` at client **init time** (`__init__` parameter; default from `DEFAULT_PLATFORM_TENANT_ID` / `SOORMA_PLATFORM_TENANT_ID` env var)
- Send `X-Tenant-ID: {platform_tenant_id}` on every request automatically (no per-call override)
- Accept `service_tenant_id` and `service_user_id` as per-call parameters (renaming `tenant_id` / `user_id`)
- Send `X-Service-Tenant-ID` and `X-User-ID` headers per request

**Boundaries**:
- No FastAPI/Starlette imports — pure `httpx` async HTTP
- `platform_tenant_id` is never a per-call parameter on any method

---

## C7 — `sdk/python` — PlatformContext Wrappers (modified)

**Purpose**: High-level agent-facing API wrapping service clients. Agent handlers interact exclusively with PlatformContext (`context.memory`, `context.tracker`, `context.registry`). Platform internals are never visible to handler code.

**Responsibilities**:
- `MemoryClient` (context.memory wrapper): update all method signatures to pass `service_tenant_id` / `service_user_id` extracted from event envelope; remove direct `tenant_id` / `user_id` params
- `TrackerClient` wrapper (context.tracker): same pattern — envelope-extracted service tenant/user; no platform_tenant_id parameter exposure
- Agent handlers continue passing nothing — context extracts from current event envelope automatically

---

## C8 — `services/event-service` (modified)

**Purpose**: Event routing hub. Receives events from SDK agents via HTTP POST and fans out to NATS. Also streams events to subscribers via SSE. Acts as the authentication boundary for `platform_tenant_id` in the event bus.

**Responsibilities**:
- Register `TenancyMiddleware` from `soorma-service-common` to extract `X-Tenant-ID` → `request.state.platform_tenant_id`
- At publish time: inject `event.platform_tenant_id` from `request.state` — discard/overwrite any value the SDK may have sent. This is the trust boundary: downstream consumers (Tracker, future services) treat `event.platform_tenant_id` as authoritative.
- `tenant_id` and `user_id` in the envelope are SDK-supplied (service tenant / service user) and are passed through unchanged
- No database; no RLS; no `get_tenanted_db` needed

**Boundaries**:
- Only `TenancyMiddleware` from `soorma-service-common` is used (no `get_tenanted_db` — no DB in Event Service)
- SDK agents MUST NOT set `platform_tenant_id` on outbound envelopes; Event Service overwrites it regardless
