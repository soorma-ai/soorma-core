# Requirements Document
## Initiative: Multi-Tenancy Model Implementation
**Repo**: soorma-core  
**INITIATIVE_ROOT**: `aidlc-docs/platform/multi-tenancy/`  
**Date**: 2026-03-21  
**Type**: Architectural Enhancement — System-wide  
**Complexity**: Complex — multiple components, breaking DB schema changes, identity model revision

---

## 1. Intent Analysis

| Attribute | Value |
|---|---|
| **Request Type** | Architectural Enhancement |
| **Scope** | System-wide (libs, sdk, services) |
| **Complexity** | Complex |
| **Brownfield** | Yes — existing UUID-based single-tier tenancy model |
| **Breaking Change** | Yes — pre-production system; data migration simplicity preferred over backward compatibility |

**Summary**: Replace soorma-core's current single-tier UUID-based tenancy model with a two-tier model that distinguishes *platform tenants* (the builders of agentic systems, managed by soorma-core) from *service tenants* (the platform tenant's customers, managed by the platform tenant). All tenant and user IDs change from UUID format to opaque strings (max 64 chars).

---

## 2. Background and Current State

### Current Model (to be replaced)
- Single tenancy tier: one `tenant_id UUID` identifies any tenant everywhere
- `user_id UUID` identifies a user, managed assumed to be by Soorma
- Memory service has `tenants` and `users` reference tables with UUID PKs and FK cascades
- Registry service `tenant_id: UUID` on `AgentTable` and `EventTable`
- Tracker service `tenant_id: String(255)`, `user_id: String(255)` (already string, no FK tables)
- Memory service middleware: single-tenant mode, hardcoded default UUID `00000000-0000-0000-0000-000000000000`
- Registry `dependencies.py`: validates `X-Tenant-ID` as strictly UUID format — rejects all non-UUIDs
- `EventEnvelope`: carries `tenant_id: Optional[str]` and `user_id: Optional[str]`

### Known Problems
- UUID enforcement in Registry `dependencies.py` will reject the new `spt_`-prefixed platform tenant ID
- Memory service `tenants`/`users` FK reference tables assume Soorma owns identity — it doesn't for service tenants or users
- No way to distinguish *which namespace* a `service_tenant_id` or `service_user_id` belongs to — all IDs are globally unique UUIDs today; under the new model they are only unique *within a platform tenant's namespace*
- Memory table `tenant_id UUID FK → tenants.id` cannot accommodate opaque string service tenant IDs

---

## 3. Two-Tier Tenancy Model

### Tier 1: Platform Tenant (`platform_tenant_id`)
- **Who**: Builders / owners of agentic systems who interact with soorma-core infrastructure (registry, memory, tracker, event service)
- **Managed by**: soorma-core Identity Service (future scope)
- **Current scope**: Single hardcoded tenant `spt_00000000-0000-0000-0000-000000000000`
- **Format**: Opaque string, max 64 chars. No prefix enforcement — validation rules deferred to future Identity Service
- **Flows via**: HTTP authentication channel only (`X-Tenant-ID` header → future API Key/JWT). NEVER carried in `EventEnvelope`
- **Service scope**: Registry Service (developer/builder facing); Memory, Tracker, Event Service (injected server-side)

### Tier 2: Service Tenant (`service_tenant_id`) + Service User (`service_user_id`)
- **Who**: End-customers of the platform tenant's agentic services
- **Managed by**: Platform tenant — soorma-core does not own, validate, or maintain a registry of these identifiers
- **Uniqueness guarantee**: Unique within the platform tenant's namespace (NOT globally unique across soorma-core)
- **Format**: Opaque string, max 64 chars. No type or format constraints enforced by soorma-core
- **Trust model**: soorma-core trusts the service tenant ID and service user ID as provided by the authenticated platform tenant's services
- **Flows via**: `EventEnvelope.tenant_id` (service tenant) and `EventEnvelope.user_id` (service user); also via direct API headers `X-Service-Tenant-ID` / `X-User-ID` for direct memory/tracker API calls
- **Service scope**: Memory Service, Tracker Service, Event Service

### Composite Data Namespace
Because service tenant and user IDs are only unique within a platform tenant's namespace, all service-tenant-scoped data in soorma-core databases MUST be stored and queried using the **composite key**: `(platform_tenant_id, service_tenant_id, service_user_id)`.

### Tenancy Tier by Service

| Service | Tenancy Tier | `platform_tenant_id` source | `service_tenant_id` source | `service_user_id` source |
|---|---|---|---|---|
| Registry Service | Platform Tenant only | `X-Tenant-ID` header | N/A | N/A |
| Memory Service | Platform + Service | `X-Tenant-ID` header (server-injected) | `X-Service-Tenant-ID` header or event envelope `tenant_id` | `X-User-ID` header or event envelope `user_id` |
| Tracker Service | Platform + Service | `X-Tenant-ID` header (server-injected) | `X-Service-Tenant-ID` header or event envelope `tenant_id` | `X-User-ID` header or event envelope `user_id` |
| Event Service | Platform + Service | `X-Tenant-ID` header | Carried in published `EventEnvelope.tenant_id` | Carried in `EventEnvelope.user_id` |

---

## 4. Functional Requirements

### FR-1: Shared Constants (`libs/soorma-common`)
- **FR-1.1**: Define `DEFAULT_PLATFORM_TENANT_ID = "spt_00000000-0000-0000-0000-000000000000"` as a named constant in `soorma_common`
- **FR-1.2**: The constant MUST be overridable at runtime via environment variable `SOORMA_PLATFORM_TENANT_ID`
- **FR-1.3**: Add a deprecation/warning marker to the constant indicating it MUST NOT be used once the Identity Service is implemented
- **FR-1.4**: Do NOT add any format or prefix validation to tenant/user ID strings in `soorma_common` — keep IDs as opaque strings

### FR-2: Registry Service — Tenant ID Type Change
- **FR-2.1**: Change `tenant_id` column type from `UUID` (PostgreSQL native UUID) to `VARCHAR(64)` on `AgentTable`, `EventTable`, and `SchemaTable`
- **FR-2.2**: Alembic migration using `ALTER COLUMN TYPE ... USING tenant_id::text` (lossless cast)
- **FR-2.3**: Update `AgentTable.tenant_id` SQLAlchemy mapped column type from `Uuid(as_uuid=True)` to `String(64)`
- **FR-2.4**: Update `EventTable.tenant_id` SQLAlchemy mapped column type from `Uuid(as_uuid=True)` to `String(64)`
- **FR-2.5**: Update `SchemaTable.tenant_id` (if present) similarly
- **FR-2.6**: Remove `get_developer_tenant_id()` from `registry_service/api/dependencies.py`; replace with `get_platform_tenant_id()` from `soorma-service-common`. Register `TenancyMiddleware` from `soorma-service-common` in the Registry Service (same pattern as Memory + Tracker — no `set_config` needed in Registry as it has no RLS-protected tables, but consistent middleware adoption is required)
- **FR-2.7**: Update all Registry CRUD, service layer, and API functions that typed `tenant_id` as `UUID` to use `str`
- **FR-2.8**: Update Registry tests to use the new platform tenant ID format (e.g., `spt_00000000-0000-0000-0000-000000000000`)
- **FR-2.9**: Remove the `IS_LOCAL_TESTING` SQLite path from `registry_service/core/database.py` and `registry_service/core/config.py`; standardize Registry to PostgreSQL-only (matching Memory + Tracker). Unit tests use mocks, not a real DB; Docker Compose dev already uses PostgreSQL.

### FR-3a: Shared Service Tenancy Middleware (`libs/soorma-service-common`) — NEW LIBRARY
- **FR-3a.1**: Create a new shared library `libs/soorma-service-common` consumed by backend services only (NOT by the SDK — to avoid pulling FastAPI/Starlette into SDK's dependency graph)
- **FR-3a.2**: Implement `TenancyMiddleware` (Starlette `BaseHTTPMiddleware`) in `soorma-service-common` with the following extraction logic, applied consistently across all infrastructure services:
  - Extract `platform_tenant_id` from `X-Tenant-ID` header; default to `DEFAULT_PLATFORM_TENANT_ID` from `soorma_common` if absent
  - Extract `service_tenant_id` from `X-Service-Tenant-ID` header (optional — `None` if absent)
  - Extract `service_user_id` from `X-User-ID` header (optional — `None` if absent)
  - Store all three on `request.state` for downstream use
- **FR-3a.3**: The middleware MUST call PostgreSQL `set_config` for each request to activate RLS session variables:
  - `set_config('app.platform_tenant_id', platform_tenant_id, true)` — transaction-scoped
  - `set_config('app.service_tenant_id', service_tenant_id or '', true)`
  - `set_config('app.service_user_id', service_user_id or '', true)`
  - This must execute within the same DB transaction/connection as the subsequent query so RLS policies enforce correctly
- **FR-3a.4**: Implement corresponding FastAPI dependency functions in `soorma-service-common`:
  - `get_platform_tenant_id(request: Request) -> str`
  - `get_service_tenant_id(request: Request) -> Optional[str]`
  - `get_service_user_id(request: Request) -> Optional[str]`
- **FR-3a.5**: Memory Service, Tracker Service (and any future services) MUST use the shared `TenancyMiddleware` from `soorma-service-common` — no per-service re-implementation of header extraction or `set_config` logic

### FR-3b: Memory Service — RLS Policy Rebuild (SECURITY — previously unenforced)

> **Note**: Codebase analysis revealed that the existing RLS policies were never enforced at runtime — no `set_config` call exists anywhere in application code. The DB schema has RLS DDL, but session variables `app.current_tenant` and `app.current_user` were never populated by the application, meaning RLS silently passed (service likely runs as DB owner, bypassing policies). Additionally, all existing policies cast `::UUID` which will break with VARCHAR columns. This must be fixed as part of this initiative.

- **FR-3b.1**: Drop all existing RLS policies on all memory tables (they reference `app.current_tenant::UUID` and `app.current_user::UUID` — both invalid under the new model)
- **FR-3b.2**: Recreate RLS policies using the new three-variable session model with string comparison (no `::UUID` cast):
  - Tenant-scoped tables: `USING (platform_tenant_id = current_setting('app.platform_tenant_id', true) AND service_tenant_id = current_setting('app.service_tenant_id', true))`
  - User-scoped tables: additionally `AND service_user_id = current_setting('app.service_user_id', true)`
- **FR-3b.3**: All memory tables that had RLS enabled MUST have updated policies: `semantic_memory`, `episodic_memory`, `procedural_memory`, `working_memory`, `task_context`, `plan_context`, `sessions`, `plans`
- **FR-3b.4**: The `set_config` calls in the shared `TenancyMiddleware` (FR-3a.3) are what activate these policies — the middleware and RLS policies are a matched pair; neither is useful without the other

### FR-3: Memory Service — Schema Restructure
- **FR-3.1**: Drop `tenants` reference table and `users` reference table from the memory service database
- **FR-3.2**: Remove all FK constraints referencing `tenants.id` and `users.id` from all memory tables
- **FR-3.3**: For all memory tables (`semantic_memory`, `episodic_memory`, `procedural_memory`, `working_memory`, `task_context`, `plan_context`):
  - Add `platform_tenant_id VARCHAR(64) NOT NULL` column
  - Rename/replace existing `tenant_id UUID FK` → `service_tenant_id VARCHAR(64) NOT NULL`
  - Rename/replace existing `user_id UUID FK` → `service_user_id VARCHAR(64) NOT NULL` (where present; use `nullable=True` where user scoping is optional per existing design)
- **FR-3.4**: Update ORM models (`memory_service/models/memory.py`) to use `String(64)` for all three columns, no `ForeignKey` references
- **FR-3.5**: Update Alembic migration to be a breaking migration (drop old tables, add new columns — no data migration needed)
- **FR-3.6**: Replace Memory Service's existing per-service `TenancyMiddleware` with the shared `TenancyMiddleware` from `libs/soorma-service-common` (see FR-3a). Remove the local `middleware.py` implementation.
- **FR-3.7**: Update `settings.default_tenant_id` default value to `spt_00000000-0000-0000-0000-000000000000`
- **FR-3.8**: Update all Memory Service service layer functions to use `platform_tenant_id`, `service_tenant_id`, `service_user_id` in all queries and inserts
- **FR-3.9**: Update Memory Service API DTOs and request/response models to reflect renamed fields
- **FR-3.10**: Update Memory SDK client (`sdk/python/soorma/memory/client.py`) to pass `X-Tenant-ID` (platform), `X-Service-Tenant-ID` (service tenant), `X-User-ID` (service user) headers

### FR-4: Memory Service — GDPR Data Deletion
- **FR-4.1**: Implement `PlatformTenantDataDeletion` service class/method in the Memory Service with the following deletion scopes executed in a single database transaction:
  - `delete_by_platform_tenant(platform_tenant_id: str)` — deletes ALL rows across ALL memory tables for a given platform tenant
  - `delete_by_service_tenant(platform_tenant_id: str, service_tenant_id: str)` — deletes all rows for a service tenant within a platform tenant's namespace
  - `delete_by_service_user(platform_tenant_id: str, service_tenant_id: str, service_user_id: str)` — deletes all rows for a specific service user
- **FR-4.2**: The deletion service must cover all tables: `semantic_memory`, `episodic_memory`, `procedural_memory`, `working_memory`, `task_context`, `plan_context`
- **FR-4.3**: Expose an internal API endpoint (or prepare the interface) for the deletion method — callable by a future GDPR compliance API; not required to be publicly exposed in this scope

### FR-5: Tracker Service — Schema Restructure
- **FR-5.1**: Rename `tenant_id String(255)` → `service_tenant_id VARCHAR(64)` on `PlanProgress` and `ActionProgress` tables
- **FR-5.2**: Rename `user_id String(255)` → `service_user_id VARCHAR(64)` on same tables
- **FR-5.3**: Add `platform_tenant_id VARCHAR(64) NOT NULL` to `PlanProgress` and `ActionProgress` tables
- **FR-5.4**: Update ORM models (`tracker_service/models/db.py`) accordingly
- **FR-5.5**: Alembic migration: column renames + length enforcement + new `platform_tenant_id` column (no type cast needed — already String)
- **FR-5.6**: Register the shared `TenancyMiddleware` from `libs/soorma-service-common` in the Tracker Service (see FR-3a). Update service layer and event subscribers to inject `platform_tenant_id` from `request.state` (set by middleware)
- **FR-5.7**: Update Tracker API query endpoints to filter by `(platform_tenant_id, service_tenant_id, service_user_id)`
- **FR-5.8**: Extend the GDPR deletion concept from FR-4 to also cover `plan_progress` and `action_progress` tables (same deletion scopes)

### FR-6: EventEnvelope — No Change
- **FR-6.1**: `EventEnvelope.tenant_id` field remains as-is — semantically it represents the *service tenant ID*
- **FR-6.2**: `EventEnvelope.user_id` field remains as-is — semantically it represents the *service user ID*
- **FR-6.3**: `platform_tenant_id` MUST NOT be added to `EventEnvelope` — it flows only via HTTP authentication headers and is injected server-side
- **FR-6.4**: Update `EventEnvelope` field docstrings to clearly document the new semantic meaning (service tenant / service user, not platform tenant)

### FR-7: SDK Clients Update
- **FR-7.1**: Update `sdk/python/soorma/memory/client.py` to set `platform_tenant_id` at **client initialization time** (from `DEFAULT_PLATFORM_TENANT_ID` constant or `SOORMA_PLATFORM_TENANT_ID` env var — future: from API key auth). `platform_tenant_id` MUST NOT be a per-call parameter; it is authentication context, not request context.
- **FR-7.2**: Per-call parameters on Memory client methods change from `tenant_id: str` → `service_tenant_id: str` and `user_id: str` → `service_user_id: str`. These represent "on whose behalf" (the end customer's tenant and user) and remain per-request.
- **FR-7.3**: Update `sdk/python/soorma/tracker/client.py` with the same initialization-time `platform_tenant_id` pattern and per-call `service_tenant_id` / `service_user_id` parameters.
- **FR-7.4**: Update PlatformContext wrappers (`context.memory`, `context.bus`, `context.registry`) — wrappers pass `service_tenant_id` and `service_user_id` extracted from the event envelope; `platform_tenant_id` is never visible to or passed by agent handler code.
- **FR-7.5**: Update `cli/commands/init.py` to use new default tenant ID constant
- **FR-7.6**: Update all SDK tests to reflect new two-parameter tenant model

### FR-8: ARCHITECTURE_PATTERNS.md Update
- **FR-8.1**: Update Section 1 of `docs/ARCHITECTURE_PATTERNS.md` to document the new two-tier tenancy model with accurate terminology: Platform Tenant, Service Tenant, Service User
- **FR-8.2**: Update header table showing `X-Tenant-ID` = platform tenant, `X-Service-Tenant-ID` = service tenant, `X-User-ID` = service user
- **FR-8.3**: Document that `platform_tenant_id` is NEVER carried in `EventEnvelope`; always server-injected from auth context

---

## 5. Non-Functional Requirements

### NFR-1: Security
- **NFR-1.1**: `platform_tenant_id` MUST always be extracted from the authenticated channel (HTTP header validated by middleware) — NEVER from user-controlled payload or event envelope
- **NFR-1.2**: Service tenant and user IDs are trusted values within an authenticated platform tenant context — no cross-platform-tenant leakage is possible because all queries include `platform_tenant_id` as a mandatory filter
- **NFR-1.3**: All database queries on service-tenant-scoped tables MUST include `platform_tenant_id` as a WHERE clause condition — partial keys (service_tenant_id alone) MUST NOT be used without platform_tenant_id

### NFR-2: Backward Compatibility
- **NFR-2.1**: This is a **breaking change** — pre-production system; no data migration required
- **NFR-2.2**: All existing dev/test data in local databases may be invalidated by migrations
- **NFR-2.3**: All existing tests must be updated to use new field names and types

### NFR-3: Constraints
- **NFR-3.1**: All tenant and user ID columns: `VARCHAR(64)` maximum length
- **NFR-3.2**: No UUID format validation anywhere in the codebase for tenant or user IDs — pure opaque strings
- **NFR-3.3**: Default platform tenant constant in `soorma_common` must carry a clear code comment warning against use in production / after Identity Service is introduced

---

## 6. Out of Scope (Current Initiative)

- Identity Service implementation (tenant registration, API key / client-secret management for platform tenants)
- Platform user IDs (admin, developer users of soorma-core) — no current workflow/use case
- JWT / API Key authentication for platform tenants (v0.8.0+ future work)
- Event Service schema or middleware changes (EventEnvelope unchanged; Event Service passes `tenant_id`/`user_id` through transparently)
- Multi-tenant RLS (Row Level Security) policy changes in PostgreSQL (existing RLS based on session variables — **brought into scope; see FR-3a and FR-3b**)
- soorma-portal or soorma-cloud changes

---

## 7. Affected Components

| Component | Change Type | Severity |
|---|---|---|
| `libs/soorma-common` | Add constant, update docstrings | Minor |
| `libs/soorma-service-common` | **New library** — shared `TenancyMiddleware` + `set_config` RLS activation + dependency functions | **Major** |
| `services/registry` | DB migration (UUID→VARCHAR), API deps update, ORM update | Moderate |
| `services/memory` | DB restructure (drop tables, rename columns, new columns), use shared middleware, RLS policy rebuild, service layer, GDPR deletion | **Major** |
| `services/tracker` | Column renames, add column, migration, use shared middleware, service layer update | Moderate |
| `sdk/python/soorma/memory/client.py` | Initialization-time platform tenant ID; per-call service tenant/user params | Moderate |
| `sdk/python/soorma/tracker/client.py` | Same as memory client | Moderate |
| `sdk/python` PlatformContext wrappers | Tenant ID routing update | Moderate |
| `sdk/python` tests | Update to new two-parameter model | Moderate |
| `docs/ARCHITECTURE_PATTERNS.md` | Documentation update | Minor |
| `services/event-service` | No code changes (EventEnvelope unchanged) | None |
