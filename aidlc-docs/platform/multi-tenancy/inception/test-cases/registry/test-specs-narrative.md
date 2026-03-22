# Test Specifications — Narrative
## Unit: registry
## Initiative: Multi-Tenancy Model Implementation
## Scope: happy-path-negative
**Unit abbreviation**: R = registry

---

### TC-R-001 — Alembic migration converts tenant_id UUID to VARCHAR(64) on all three tables

**Context**: The core schema migration for the Registry Service — must run cleanly using a `::text` cast, avoiding data loss or errors on existing rows. Covers FR-2.1, FR-2.2.

**Scenario description**: The Alembic migration script for the Registry UUID→VARCHAR change is applied to a database that has an existing `AgentTable`, `EventTable`, and `SchemaTable` with UUID-typed `tenant_id` columns.

**Steps**:
1. Stand up a PostgreSQL test database with the pre-migration schema (UUID `tenant_id` columns)
2. Run `alembic upgrade head` (or the specific migration revision)
3. Inspect the column type on `AgentTable`, `EventTable`, `SchemaTable`

**Expected outcome**: All three tables have `tenant_id` as `VARCHAR(64)` (character varying, max 64). Existing rows remain intact with tenant ID values expressed as their string representation.

**Scope tag**: happy-path
**Priority**: High
**Source**: registry / FR-2.1, FR-2.2
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/registry/

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

### TC-R-006 — Registry ORM models use String(64) for tenant_id after migration

**Context**: Validates that the ORM layer matches the database schema change — `Uuid(as_uuid=True)` replaced with `String(64)`. Covers FR-2.3, FR-2.4, FR-2.5.

**Scenario description**: The ORM model definitions for `AgentTable`, `EventTable`, and `SchemaTable` are inspected.

**Steps**:
1. Inspect the SQLAlchemy model for `AgentTable` — find the `tenant_id` column type
2. Inspect `EventTable` — same check
3. Inspect `SchemaTable` — same check

**Expected outcome**: All three models define `tenant_id` as `Column(String(64), ...)` with no `Uuid` type or UUID-related metadata.

**Scope tag**: happy-path
**Priority**: High
**Source**: registry / FR-2.3, FR-2.4, FR-2.5
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/registry/

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

### TC-R-009 — Registry does not return data from a different platform tenant's namespace

**Context**: Negative/security case: a request from one platform tenant must not return agents registered by a different platform tenant. Covers NFR-1.3.

**Scenario description**: Two agents are registered under different `platform_tenant_id` values. A query using the first tenant's ID should not return the second tenant's agent.

**Steps**:
1. Register agent A under `X-Tenant-ID: spt_tenant_1`
2. Register agent B under `X-Tenant-ID: spt_tenant_2`
3. Send `GET /agents` with `X-Tenant-ID: spt_tenant_1`

**Expected outcome**: Response includes only agent A. Agent B is not returned. No cross-tenant data leakage.

**Scope tag**: happy-path-negative
**Priority**: High
**Source**: registry / NFR-1.3
**Construction artifacts**: aidlc-docs/platform/multi-tenancy/construction/registry/
