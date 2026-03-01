# Action Plan: Phase 2 - Service Implementation (SOOR-DISC-P2)

**Status:** ✅ Phase 2 COMPLETE — all tasks (2A/2B/2C/2D) done, 80 tests passing  
**Parent Plan:** [MASTER_PLAN_Enhanced_Discovery.md](MASTER_PLAN_Enhanced_Discovery.md)  
**Phase:** 2 of 5  
**Estimated Duration:** 3-4 days  
**Target Release:** v0.8.2  
**Created:** March 1, 2026  
**Approved By:** Developer  
**Approval Date:** March 1, 2026

---

## Architecture Compliance (Gate 0)

Per CONTRIBUTING constitution, this plan is submitted AFTER reading ARCHITECTURE_PATTERNS.md sections 1-7.

| Section | Pattern | Application in Phase 2 |
|---------|---------|----------------------|
| §1 Auth | `X-Tenant-ID` custom header (v0.7.x) | `get_developer_tenant_id` dep reused on all new endpoints |
| §2 Two-Layer SDK | `RegistryClient` is the service client; `context.registry` is the wrapper | New schema methods added to `RegistryClient` (service layer); `context.registry` automatically gets them |
| §3 Event Choreography | Not applicable (this is a CRUD service, no pub/sub) | N/A |
| §4 Multi-tenancy | PostgreSQL session variables + RLS | Middleware sets `app.tenant_id` per request; RLS policies from migration 003 enforce isolation |
| §5 State Management | Not applicable | N/A |
| §6 Error Handling | Service client raises; wrapper propagates; handler converts to HTTPException | See Task 3.3 |
| §7 Testing | Unit tests with SQLite mock; no testcontainers for Phase 2 | TestClient (same pattern as Phase 1) |

**SDK Wrapper Completeness Verification:**

`context.registry` is `RegistryClient` directly (not a thin wrapper class). This is the approved pattern for the registry — the registry is developer-scoped, not user-session-scoped, and the client already includes auth headers automatically.

- [x] `RegistryClient.register_schema()` — ✅ Stubbed (Task 1.5); GREEN in Task 3.7
- [x] `RegistryClient.get_schema()` — ✅ Stubbed (Task 1.5); GREEN in Task 3.7
- [x] `RegistryClient.list_schemas()` — ✅ Stubbed (Task 1.5); GREEN in Task 3.7
- [x] `RegistryClient.discover_agents()` — ✅ Stubbed (Task 1.5); GREEN in Task 3.7

**Additional items completed beyond plan:**
- [x] `PayloadSchemaRegistrationRequest` + `PayloadSchemaListResponse` added to `soorma_common/models.py`
- [x] Both exported from `soorma_common/__init__.py`
- [x] `DiscoveredAgent.get_consumed_schemas()` / `get_produced_schemas()` implemented (were already in models.py)
- [x] `AgentRegistryService.discover_agents()` stub added to `agent_service.py`
- [x] `GET /v1/agents/discover` endpoint stub added to `api/v1/agents.py`
- [x] Schema router registered in `api/v1/__init__.py` (Task 3.6 done early)

---

## 1. Requirements & Core Objective

### Phase Objective

Implement the Schema Registry service endpoints and capability-based agent discovery.
Phase 1 laid the foundation (DTOs, database schema, SQLAlchemy models).
Phase 2 makes it operational.

**From Master Plan Phase 2:**
- `POST /v1/schemas` — Register a payload schema
- `GET /v1/schemas/{schema_name}` — Get latest schema version
- `GET /v1/schemas/{schema_name}/versions/{version}` — Get specific version
- `GET /v1/schemas?owner_agent_id={id}` — List schemas by owner
- `GET /v1/agents/discover` — Capability-based agent discovery
- Multi-tenancy RLS middleware (set `app.tenant_id` per request)

### Acceptance Criteria

- [ ] `POST /v1/schemas` registers a schema, returns 200 with `PayloadSchemaResponse`
- [ ] `GET /v1/schemas/{schema_name}` returns latest version or 404
- [ ] `GET /v1/schemas/{schema_name}/versions/{version}` returns specific version or 404
- [ ] `GET /v1/schemas?owner_agent_id={id}` returns all schemas for an agent
- [ ] `GET /v1/agents/discover?consumed_event={event}` returns `DiscoveredAgent[]` with full capability metadata
- [ ] All endpoints require `X-Tenant-ID` header (existing pattern)
- [ ] Cross-tenant isolation: tenant A cannot see tenant B's schemas
- [ ] `PayloadSchemaTable.tenant_id` uses `Uuid(as_uuid=True)` (same fix as agent/event models)
- [ ] SDK `RegistryClient` has `register_schema`, `get_schema`, `list_schemas`, `discover_agents` methods
- [ ] 40+ tests pass (existing 50 + new ~20 schema + ~10 discovery)

---

## 2. Technical Design

### New Components

| File | Purpose |
|------|---------|
| `services/registry/src/registry_service/crud/schemas.py` | CRUD operations for `payload_schemas` table |
| `services/registry/src/registry_service/services/schema_service.py` | Business logic for schema registration/retrieval |
| `services/registry/src/registry_service/api/v1/schemas.py` | HTTP endpoints for schema management |
| `services/registry/src/registry_service/middleware/tenant.py` | Set `app.tenant_id` PostgreSQL session variable per request |

### Modified Components

| File | Change |
|------|--------|
| `services/registry/src/registry_service/models/schema.py` | Fix `tenant_id` to use `Uuid(as_uuid=True)` (same bug as agent/event models) |
| `services/registry/src/registry_service/api/v1/agents.py` | Add `GET /v1/agents/discover` endpoint |
| `services/registry/src/registry_service/services/agent_service.py` | Add `discover_agents()` static method |
| `services/registry/src/registry_service/main.py` | Register `/v1/schemas` router + tenant middleware |
| `sdk/python/soorma/registry/client.py` | Add `register_schema`, `get_schema`, `list_schemas`, `discover_agents` |
| `libs/soorma-common/src/soorma_common/models.py` | Implement `DiscoveredAgent.get_consumed_schemas()` / `get_produced_schemas()` helpers |

### API Contract

#### Schema Endpoints

```http
POST /v1/schemas
Header: X-Tenant-ID: <uuid>
Body: {"schema": {"schemaName": "...", "version": "1.0.0", "jsonSchema": {...}, "description": "..."}}
Response 200: {"schemaName": "...", "version": "...", "success": true, "message": "..."}
Response 409: {"detail": "Schema '<name>@<version>' already exists for this tenant"}
```

```http
GET /v1/schemas/{schema_name}
Header: X-Tenant-ID: <uuid>
Response 200: EventDefinition with schema metadata
Response 404: {"detail": "Schema '<name>' not found"}
```

```http
GET /v1/schemas/{schema_name}/versions/{version}
Header: X-Tenant-ID: <uuid>
Response 200: PayloadSchema
Response 404: {"detail": "Schema '<name>@<version>' not found"}
```

```http
GET /v1/schemas?owner_agent_id={id}
Header: X-Tenant-ID: <uuid>
Response 200: {"schemas": [...], "count": N}
```

#### Discovery Endpoint

```http
GET /v1/agents/discover?consumed_event={event}&include_schemas=true
Header: X-Tenant-ID: <uuid>
Response 200: {"agents": [DiscoveredAgent], "count": N}
```

### Data Flow: Schema Registration

```
POST /v1/schemas
    → get_developer_tenant_id (extracts UUID from X-Tenant-ID)
    → tenant middleware sets app.tenant_id in db session
    → SchemaRegistryService.register_schema(db, schema, tenant_id)
        → schema_crud.get_schema_by_name_version(db, name, version, tenant_id)
            → None (new) → schema_crud.create_schema(db, schema, tenant_id)
            → exists    → 409 Conflict
    → return PayloadSchemaResponse(success=True)
```

### Multi-Tenancy Middleware

The current `get_developer_tenant_id` dependency extracts the UUID from headers.
Phase 2 adds a middleware layer that sets the PostgreSQL session variable so RLS policies fire:

```python
# services/registry/src/registry_service/middleware/tenant.py
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

class TenantMiddleware(BaseHTTPMiddleware):
    """Set app.tenant_id PostgreSQL session variable for RLS policy enforcement."""

    async def dispatch(self, request: Request, call_next):
        tenant_id = request.headers.get("X-Tenant-ID")
        if tenant_id:
            # Attach tenant_id to request state for downstream use
            request.state.tenant_id = tenant_id
        return await call_next(request)
```

**Note:** PostgreSQL session variables for RLS must be set within the DB session, not the middleware (middleware doesn't have DB access). The correct pattern is to set them in `get_db` or via an async dependency — see ARCHITECTURE_PATTERNS.md §4.

**FDE Decision for RLS:** The registry service currently runs on SQLite for testing and may run on SQLite locally. RLS session variable setting is a no-op on SQLite. The implementation must guard:
```python
if not settings.IS_LOCAL_TESTING:
    await db.execute(text(f"SET app.tenant_id = '{tenant_id}'"))
```

---

## 3. Task Tracking Matrix

**Phase 2A: Fix + Stub (Pre-condition)** ✅ COMPLETE

- [x] **Task 1.1:** Fix `PayloadSchemaTable` — `Uuid(as_uuid=True, native_uuid=True)` + `default=uuid4` (Decision D4) ✅
- [x] **Task 1.2:** STUB — `crud/schemas.py` with `NotImplementedError` stubs ✅
- [x] **Task 1.3:** STUB — `services/schema_service.py` with `NotImplementedError` stubs ✅
- [x] **Task 1.4:** STUB — `api/v1/schemas.py` with placeholder endpoints ✅
- [x] **Task 1.5:** STUB — SDK `RegistryClient` schema/discover method stubs ✅
- [x] **Task 1.6:** `DiscoveredAgent.get_consumed_schemas()` / `get_produced_schemas()` — already implemented ✅
- [x] **Task 1.6b (extra):** `PayloadSchemaRegistrationRequest` + `PayloadSchemaListResponse` added to soorma-common ✅
- [x] **Task 1.6c (extra):** `AgentRegistryService.discover_agents()` stub + `GET /v1/agents/discover` endpoint stub ✅
- [x] **Task 3.6 (done early):** Schema router registered in `api/v1/__init__.py` ✅

**Phase 2B: RED (Write Failing Tests)** ✅ COMPLETE

- [x] **Task 2.1:** `tests/test_schema_endpoints.py` — 20 tests (17 schema CRUD + 3 cross-tenant isolation) ✅
  - `test_register_schema_success`, `test_register_schema_returns_message`
  - `test_register_schema_duplicate_409`, `test_register_schema_different_versions_ok`
  - `test_register_schema_requires_tenant_header` (PASSES — auth guard)
  - `test_register_schema_with_owner_agent_id`, `test_register_multiple_schemas`
  - `test_get_schema_by_name_success`, `test_get_schema_not_found_404`
  - `test_get_schema_returns_latest_version`, `test_get_schema_requires_tenant_header` (PASSES)
  - `test_get_specific_version_success`, `test_get_specific_version_not_found_404`
  - `test_list_schemas_by_owner`, `test_list_schemas_all_for_tenant`
  - `test_list_schemas_empty_without_owner_filter`, `test_list_schemas_requires_tenant_header` (PASSES)
  - `test_schema_cross_tenant_isolation`, `test_same_schema_name_different_tenants`
  - `test_list_schemas_tenant_scoped`
- [x] **Task 2.2:** `tests/test_agent_discovery.py` — 10 discovery tests ✅
  - `test_discover_agents_by_consumed_event`, `test_discover_agents_returns_count`
  - `test_discover_agents_no_match_returns_empty`, `test_discover_agents_returns_full_capability_metadata`
  - `test_discover_agents_no_filter_returns_all_active`, `test_discover_agents_requires_tenant_header` (PASSES)
  - `test_discover_agents_multiple_consumers`, `test_discover_agents_cross_tenant_isolation`
  - `test_discover_agents_response_schema_structure`, `test_discover_endpoint_is_separate_from_query`
- [x] **Task 2.3:** RED verified — 26 fail on `NotImplementedError`, 4 pass (auth-only), 0 `ImportError` ✅

**Phase 2C: GREEN (Implement)** ✅ Tasks 3.1–3.2 complete; Task 3.4, 3.7 pending

- [x] **Task 3.1:** Implement `crud/schemas.py` — SQLAlchemy async queries for all 5 SchemaCRUD methods. Fixed `created_at` to use Python-side `datetime.now(timezone.utc)` for microsecond precision (SQLite's `func.now()` has second resolution; two rapid inserts in same test would be unorderable) ✅
- [x] **Task 3.2:** Implement `services/schema_service.py` — `_table_to_dto()` helper + 4 static methods (register with duplicate detection → 409, get_by_name, get_by_name_version, list_schemas). 20/20 schema tests pass ✅
- [x] **Task 3.3:** `api/v1/schemas.py` — HTTP layer already correct (delegates to service); no changes needed ✅
- [x] **Task 3.4:** Implement `services/agent_service.py::discover_agents()` — delegates to `query_agents(consumed_event=..., include_expired=False)`. 10/10 discovery tests pass ✅
- [x] **Task 3.5:** `api/v1/agents.py` discover endpoint already correct (delegates to service); no changes needed ✅
- [x] **Task 3.6:** Schema router registered in `api/v1/__init__.py` ✅ (done in Phase 2A)
- [x] **Task 3.7:** Implement SDK `RegistryClient` schema/discover methods — `register_schema` (POST), `get_schema` (GET with optional version), `list_schemas` (GET with owner filter), `discover_agents` (GET with event filter) ✅
- [x] **Task 3.8:** Full test suite — 80 passed, 0 failed, 1 warning (benign Pydantic field name shadow) ✅

**Phase 2D: REFACTOR** ✅ COMPLETE

- [x] **Task 4.1:** CRUD layer reviewed — no significant duplication; `SchemaCRUD` follows same clean pattern as `AgentCRUD`. Removed all STUB phase comments from production source files (×5 files) ✅
- [x] **Task 4.2:** `services/registry/CHANGELOG.md` updated with v0.8.2 entry: all new endpoints, SDK methods, SQLite precision fix ✅
- [x] **Task 4.3:** `docs/discovery/MIGRATION_GUIDE_v0.8.1.md` updated with v0.8.2 addendum: new endpoints table, SDK usage examples, duplicate-409 behavior, discover agents pattern ✅

**48-Hour Filter Decision:**

All components are critical and interdependent. No FDE deferrals:
- Schema endpoints → SDK wrapper → examples (Phase 5 depends on this)
- Discovery endpoint → `DiscoveredAgent` → Planner can find workers (core DisCo use case)

---

## 4. TDD Strategy

### Test Files Structure

```
services/registry/tests/
    conftest.py                     # ✅ Existing (TEST_TENANT_ID, client fixture)
    test_schema_endpoints.py        # 🆕 Phase 2 — schema CRUD endpoints
    test_agent_discovery.py         # 🆕 Phase 2 — discovery endpoint
    test_agent_ttl.py               # ✅ Existing (50 passing)
    ... (existing files)
```

### Key Test Patterns

```python
# test_schema_endpoints.py — example test
def test_register_schema_success(client):
    """Register a new schema returns 200 with success=True."""
    response = client.post("/v1/schemas", json={
        "schema": {
            "schemaName": "research_request_v1",
            "version": "1.0.0",
            "jsonSchema": {"type": "object", "properties": {"query": {"type": "string"}}},
            "description": "Research task input schema"
        }
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["schemaName"] == "research_request_v1"
    assert data["version"] == "1.0.0"


def test_register_schema_duplicate_409(client):
    """Registering the same schema name+version+tenant twice returns 409."""
    payload = {
        "schema": {
            "schemaName": "dup_schema_v1",
            "version": "1.0.0",
            "jsonSchema": {"type": "object"},
            "description": "Test"
        }
    }
    client.post("/v1/schemas", json=payload)  # first registration
    response = client.post("/v1/schemas", json=payload)  # duplicate
    assert response.status_code == 409
```

### Cross-Tenant Isolation Test

```python
TENANT_A = UUID("11111111-1111-1111-1111-111111111111")
TENANT_B = UUID("22222222-2222-2222-2222-222222222222")

def test_schema_cross_tenant_isolation():
    """Tenant A schemas are not visible to Tenant B."""
    client_a = TestClient(app, headers={"X-Tenant-ID": str(TENANT_A)})
    client_b = TestClient(app, headers={"X-Tenant-ID": str(TENANT_B)})

    # Register schema as Tenant A
    client_a.post("/v1/schemas", json={"schema": {"schemaName": "secret_v1", "version": "1.0.0", "jsonSchema": {}, "description": ""}})

    # Tenant B should NOT see it
    response = client_b.get("/v1/schemas/secret_v1")
    assert response.status_code == 404
```

---

## 5. SDK Layer Verification

### Wrapper Completeness (Pre-condition before Task 3.7)

**Service Client:** `sdk/python/soorma/registry/client.py` — `RegistryClient`  
**Context Wrapper:** `context.registry` → directly exposes `RegistryClient` (approved pattern for registry)

New methods needed in `RegistryClient`:

```python
async def register_schema(self, schema: PayloadSchema) -> PayloadSchemaResponse:
    """Register a payload schema with the registry."""
    # POST /v1/schemas
    ...

async def get_schema(self, schema_name: str, version: Optional[str] = None) -> Optional[PayloadSchema]:
    """Get a schema by name (latest version) or by name+version."""
    # GET /v1/schemas/{schema_name} or GET /v1/schemas/{schema_name}/versions/{version}
    ...

async def list_schemas(self, owner_agent_id: Optional[str] = None) -> List[PayloadSchema]:
    """List schemas, optionally filtered by owner agent."""
    # GET /v1/schemas?owner_agent_id={id}
    ...

async def discover_agents(
    self,
    consumed_event: Optional[str] = None,
    include_schemas: bool = False
) -> List[DiscoveredAgent]:
    """Discover agents by capability (consumed event)."""
    # GET /v1/agents/discover
    ...
```

**Common Models needed in soorma_common:**
- `PayloadSchemaRegistrationRequest` — wraps `PayloadSchema` for `POST /v1/schemas` body
- `PayloadSchemaListResponse` — `{"schemas": [...], "count": N}`
- `DiscoveredAgent` — currently stubbed in models.py (needs `get_consumed_schemas()` impl)

---

## 6. Decisions & Risks

| # | Decision | Rationale | Status |
|---|----------|-----------|--------|
| D1 | No upsert for schemas — `POST` with same `(name, version, tenant)` = 409 Conflict. Schemas are immutable once registered. | Versioned schemas must not be silently overwritten. New version = new registration. | ✅ Approved |
| D2 | Discovery returns `AgentDefinition[]` in Phase 2, `DiscoveredAgent[]` in Phase 3 | Avoids re-implementing agent-to-dto logic; `DiscoveredAgent` is a richer wrapper added in Phase 3 | ✅ Approved |
| D3 | RLS session var set via `get_db` dependency (not middleware) | Middleware has no DB access; dependency injection pattern is cleaner | ✅ Approved |
| D4 | `PayloadSchemaTable.id` uses `default=uuid4` (Python-side) instead of `server_default=func.gen_random_uuid()` (DB-side) | `gen_random_uuid()` is PostgreSQL-only and fails on SQLite. Python-side `uuid4()` generates the UUID before INSERT and passes it as a bind parameter — PostgreSQL stores it in the native UUID column identically. Same compatibility guarantee as the Phase 1 `Uuid(as_uuid=True)` column type fix. | ✅ Approved |

---

## 7. Open Questions

All questions resolved. No blockers.

| # | Question | Resolution |
|---|----------|------------|
| Q1 | `PayloadSchemaTable.id` — Python-side `uuid4` vs DB-side `gen_random_uuid()`? | ✅ Use `default=uuid4` (Python-side). PostgreSQL-compatible: SQLAlchemy passes UUID as bind parameter; native UUID column stores it identically. |
| Q2 | Duplicate `(schema_name, version, tenant_id)` on `POST /v1/schemas` — upsert or 409? | ✅ 409 Conflict. Schemas are immutable once registered; new version = new registration. |

---

**This plan is APPROVED.** Implementation begins with Task 1.1 (Phase 2A — Fix + Stub).
