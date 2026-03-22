# Test Specifications — Narrative
## Unit: registry
## Initiative: Multi-Tenancy Model Implementation
## Scope: happy-path-negative
**Unit abbreviation**: R = registry

---

### TC-R-001 — Alembic migration 004 renames tenant_id to platform_tenant_id and converts UUID to VARCHAR(64) on all three tables

**Context**: The core schema migration for the Registry Service (Alembic revision 004). Must run cleanly using a `::text` cast. The column is both *renamed* (`tenant_id → platform_tenant_id`) and *retyped* (`UUID → VARCHAR(64)`). Composite unique constraints referencing the old column name are dropped before the rename and recreated with the new name. Existing rows must survive intact. Covers FR-2.1, FR-2.2. See also TC-R-011 for the RLS policies that are also applied by this migration.

**Scenario description**: Migration 004 is applied to a PostgreSQL database with an existing pre-migration schema (`UUID tenant_id` columns on `agents`, `events`, `payload_schemas`).

**Steps**:
1. Stand up a PostgreSQL test database with the pre-migration schema (UUID `tenant_id` columns on the three Registry tables)
2. Run `alembic upgrade head` to apply migration 004
3. Inspect the column name and type on `agents`, `events`, `payload_schemas`: confirm column is named `platform_tenant_id` with type `VARCHAR(64)`
4. Verify composite unique constraints have been recreated: `(agent_id, platform_tenant_id)` on `agents`; `(event_name, platform_tenant_id)` on `events`; `(schema_name, version, platform_tenant_id)` on `payload_schemas`
5. Confirm existing rows are intact with tenant ID values as their string representation

**Expected outcome**: All three tables have column `platform_tenant_id` typed as `VARCHAR(64)`. No `tenant_id` column exists. Composite unique constraints reference `platform_tenant_id`. Existing rows present and correct.

**Scope tag**: happy-path
**Priority**: High
**Source**: registry / FR-2.1, FR-2.2
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/registry/
**Technical references**: `aidlc-docs/platform/multi-tenancy/construction/registry/functional-design/business-rules.md` (BR-R10, BR-R11, BR-R12)

---

### TC-R-002 — Registry accepts non-UUID platform tenant ID in all CRUD operations

**Context**: The key driver of this migration — the new `spt_`-prefixed platform tenant ID must be accepted by the Registry. Covers FR-2.7, FR-2.8.

**Scenario description**: A request to register an agent is sent using the new platform tenant ID format (`spt_00000000-0000-0000-0000-000000000000`). The agent is stored and retrievable.

**Steps**:
1. Start the Registry Service with the migrated schema
2. Send `POST /agents` with header `X-Tenant-ID: spt_00000000-0000-0000-0000-000000000000` and agent registration body
3. Send `GET /agents` with the same `X-Tenant-ID` header
4. Verify the agent appears in the response

**Expected outcome**: Registration returns HTTP 201. Retrieval returns HTTP 200 and includes the registered agent. No UUID validation error is raised.

**Scope tag**: happy-path
**Priority**: High
**Source**: registry / FR-2.7, FR-2.8
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/registry/

---

### TC-R-003 — TenancyMiddleware is registered and populates request.state in Registry

**Context**: Ensures the Registry Service correctly adopts the shared middleware from `soorma-service-common`. Covers FR-2.6.

**Scenario description**: A request to the Registry is processed via the middleware stack. The route handler reads `platform_tenant_id` from `request.state`.

**Steps**:
1. Start the Registry Service
2. Send any API request with `X-Tenant-ID: spt_test_tenant`
3. In the route handler (or via a test instrument), confirm `request.state.platform_tenant_id` is set

**Expected outcome**: `request.state.platform_tenant_id equals "spt_test_tenant"`. `TenancyMiddleware` from `soorma-service-common` is responsible for setting it.

**Scope tag**: happy-path
**Priority**: High
**Source**: registry / FR-2.6
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/registry/

---

### TC-R-004 — get_platform_tenant_id dependency replaces get_developer_tenant_id

**Context**: The old UUID-validating `get_developer_tenant_id` is removed and replaced with `get_platform_tenant_id` from `soorma-service-common`. This ensures no code still validates the platform tenant ID as a UUID. Covers FR-2.6.

**Scenario description**: The Registry `dependencies.py` is inspected for absence of `get_developer_tenant_id` and presence of the import from `soorma-service-common`.

**Steps**:
1. Inspect `registry_service/api/dependencies.py` source
2. Confirm `get_developer_tenant_id` is not defined or imported
3. Confirm `get_platform_tenant_id` is imported from `soorma_service_common`

**Expected outcome**: `get_developer_tenant_id` is absent from the file. `get_platform_tenant_id` from `soorma_service_common` is present and acts as the platform tenant ID extractor.

**Scope tag**: happy-path
**Priority**: High
**Source**: registry / FR-2.6
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/registry/

---

### TC-R-005 — IS_LOCAL_TESTING SQLite path is removed from Registry Service

**Context**: Removes the legacy test bypass that caused the Registry to use SQLite in a `IS_LOCAL_TESTING` mode, standardizing it to PostgreSQL. Covers FR-2.9.

**Scenario description**: The Registry configuration and database setup are inspected for any SQLite or `IS_LOCAL_TESTING` references.

**Steps**:
1. Inspect `registry_service/core/config.py` for `IS_LOCAL_TESTING`
2. Inspect `registry_service/core/database.py` for SQLite connection logic

**Expected outcome**: Neither file contains references to `IS_LOCAL_TESTING`, SQLite, or any conditional database engine selection. The Registry always uses the PostgreSQL `DATABASE_URL` config.

**Scope tag**: happy-path
**Priority**: Medium
**Source**: registry / FR-2.9
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/registry/

---

### TC-R-006 — Registry ORM models rename tenant_id to platform_tenant_id with String(64) type

**Context**: Validates that the ORM layer matches both the rename and the type change from migration 004. The mapped attribute name changes from `tenant_id` to `platform_tenant_id`, the Python annotation changes from `Mapped[UUID]` to `Mapped[str]`, and the column type changes from `Uuid(as_uuid=True)` to `String(64)`. Covers FR-2.3, FR-2.4, FR-2.5.

**Scenario description**: The ORM model definitions for `AgentTable`, `EventTable`, and `PayloadSchemaTable` are inspected for both the correct attribute name and the correct column type.

**Steps**:
1. Inspect `AgentTable`: confirm attribute `platform_tenant_id: Mapped[str]` with `String(64)` column type; confirm no `tenant_id` attribute; confirm no `Uuid` import used for this column
2. Inspect `EventTable`: same checks
3. Inspect `PayloadSchemaTable`: same checks

**Expected outcome**: All three ORM models define `platform_tenant_id: Mapped[str]` backed by `String(64)`. No `tenant_id` attribute exists on any model. No `Uuid(as_uuid=True)` type usage for the tenant column.

**Scope tag**: happy-path
**Priority**: High
**Source**: registry / FR-2.3, FR-2.4, FR-2.5
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/registry/
**Technical references**: `aidlc-docs/platform/multi-tenancy/construction/registry/functional-design/business-rules.md` (BR-R15)

---

### TC-R-007 — Registry rejects a request with no X-Tenant-ID and falls back to default

**Context**: Negative case: ensures the Registry handles absent `X-Tenant-ID` gracefully via the `TenancyMiddleware` default fallback — no crash or 500 error. Covers FR-2.6.

**Scenario description**: A request to the Registry without `X-Tenant-ID` is processed. The handler uses the default platform tenant ID.

**Steps**:
1. Send `GET /agents` to Registry Service with no `X-Tenant-ID` header
2. Observe the response

**Expected outcome**: Request is processed (HTTP 200 or 404 depending on data) using `DEFAULT_PLATFORM_TENANT_ID`. No HTTP 500 or unhandled exception.

**Scope tag**: happy-path-negative
**Priority**: High
**Source**: registry / FR-2.6
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/registry/

---

### TC-R-008 — Registry rejects agent registration with tenant_id exceeding 64 chars

**Context**: Negative case: the 64-character VARCHAR constraint must prevent oversized tenant IDs from being stored. Covers NFR-3.1 as applied to Registry.

**Scenario description**: An agent registration request is sent with an `X-Tenant-ID` value of 65 characters.

**Steps**:
1. Send `POST /agents` with `X-Tenant-ID: {65-character string}` and a valid agent body to the Registry Service

**Expected outcome**: HTTP 422 (validation error) or HTTP 500 with a database constraint violation message. The agent is NOT stored.

**Scope tag**: happy-path-negative
**Priority**: High
**Source**: registry / NFR-3.1
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/registry/

---

### TC-R-009 — Registry enforces cross-tenant isolation at the database layer (SOC2 evidence)

**Context**: Negative/security case: a request from one platform tenant must not return agents registered by a different platform tenant. Covers NFR-1.3. **This is the primary SOC2 auditability test for Registry tenant isolation** (BR-R07b). Isolation is enforced at *two* layers: (1) application-layer `WHERE platform_tenant_id = :val`, and (2) PostgreSQL RLS policy activated via `get_tenanted_db` → `set_config('app.platform_tenant_id', ...)`. This test validates both layers in combination. Must be run against a real PostgreSQL instance (SQLite does not enforce RLS).

**Scenario description**: Two agents are registered under different `platform_tenant_id` values via separate requests. A query using the first tenant's ID must not return the second tenant's data — enforced at DB level by the RLS policy.

**Steps**:
1. Start the Registry Service connected to a PostgreSQL instance with migration 004 applied (RLS policies active)
2. Register agent A under `X-Tenant-ID: spt_tenant_1`
3. Register agent B under `X-Tenant-ID: spt_tenant_2`
4. Send `GET /agents` with `X-Tenant-ID: spt_tenant_1`
5. Confirm agent A is returned and agent B is absent
6. (Optional deeper verification) Execute a raw query in the same DB session with `app.platform_tenant_id` set to `spt_tenant_1` using `set_config` — confirm zero rows from `spt_tenant_2` are visible

**Expected outcome**: Response includes only agent A. Agent B is not returned. No cross-tenant data leakage at either the API or DB level. The PostgreSQL RLS policy (`FORCE ROW LEVEL SECURITY`) is the DB-layer enforcement mechanism: even if an application bug omitted the `WHERE` clause, the DB would return zero rows for the wrong tenant.

**Scope tag**: happy-path-negative
**Priority**: High
**Source**: registry / NFR-1.3
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/registry/
**Technical references**: `aidlc-docs/platform/multi-tenancy/construction/registry/functional-design/business-rules.md` (BR-R07b), `aidlc-docs/platform/multi-tenancy/construction/registry/functional-design/business-logic-model.md` (Design Decision: Adding RLS to Registry)

---

### TC-R-010 — All Registry v1 route handlers use get_tenanted_db, not bare get_db

**Context**: BR-R06 mandates that every route handler accessing `agents`, `events`, or `payload_schemas` must declare `db: AsyncSession = Depends(get_tenanted_db)`. This is the wiring that causes `set_config('app.platform_tenant_id', ...)` to fire before every query, activating the RLS policies deployed by migration 004. Without this, RLS policies exist in the DB schema but are never activated at query time — cross-tenant data would be visible. This is a structural code-inspection test.

**Scenario description**: Every endpoint in `api/v1/agents.py`, `api/v1/events.py`, and `api/v1/schemas.py` is inspected to verify the database session dependency.

**Steps**:
1. Inspect all `@router` endpoint functions in `registry_service/api/v1/agents.py`
2. Inspect all `@router` endpoint functions in `registry_service/api/v1/events.py`
3. Inspect all `@router` endpoint functions in `registry_service/api/v1/schemas.py`
4. For each endpoint, confirm the DB session parameter is typed as `db: AsyncSession = Depends(get_tenanted_db)`
5. Confirm `get_tenanted_db` is imported from `soorma_service_common`

**Expected outcome**: All DB-accessing route handlers in all three v1 route files use `Depends(get_tenanted_db)`. No bare `Depends(get_db)` is present in any v1 route handler. The import of `get_tenanted_db` references `soorma_service_common.dependencies`.

**Scope tag**: happy-path
**Priority**: High
**Source**: registry / BR-R06
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/registry/code/
**Technical references**: `aidlc-docs/platform/multi-tenancy/construction/registry/functional-design/business-rules.md` (BR-R06)

---

### TC-R-011 — Migration 004 deploys ENABLE and FORCE ROW LEVEL SECURITY with isolation policies on all three Registry tables

**Context**: The functional design adds RLS to Registry as a SOC2 auditability control (deviation from inception spec — see `business-logic-model.md`). BR-R07 requires RLS policies to be created by migration 004; BR-R07a requires `FORCE ROW LEVEL SECURITY` so that even the DB table owner (used by Alembic) is subject to the policy during application queries. This test verifies the structural presence of RLS configuration in the database schema after migration runs — it is the complement to TC-R-001 (column rename/retype) and TC-R-009 (runtime isolation).

**Scenario description**: After migration 004 is applied, the PostgreSQL system catalog is queried to confirm that RLS is enabled, forced, and that the correct isolation policy expressions are present on all three tables.

**Steps**:
1. Apply migration 004 to a clean PostgreSQL test database
2. Query `pg_class` where `relname IN ('agents', 'events', 'payload_schemas')` — confirm `relrowsecurity = true` and `relforcerowsecurity = true` for all three
3. Query `pg_policies` where `tablename IN ('agents', 'events', 'payload_schemas')` — confirm at least one isolation policy exists per table
4. Confirm isolation policy expressions reference `current_setting('app.platform_tenant_id', true)` — no UUID cast present (which would indicate old 003 policies were not replaced)

**Expected outcome**: All three tables have `relrowsecurity = true` and `relforcerowsecurity = true`. Each table has an isolation policy referencing `current_setting('app.platform_tenant_id', true)`. No policy contains a `::UUID` cast. The migration is idempotent — running `alembic upgrade head` again does not raise an error.

**Scope tag**: happy-path
**Priority**: High
**Source**: registry / BR-R07, BR-R07a
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/registry/code/
**Technical references**: `aidlc-docs/platform/multi-tenancy/construction/registry/functional-design/business-rules.md` (BR-R07, BR-R07a), `aidlc-docs/platform/multi-tenancy/construction/registry/functional-design/business-logic-model.md` (Design Decision: Adding RLS to Registry)
