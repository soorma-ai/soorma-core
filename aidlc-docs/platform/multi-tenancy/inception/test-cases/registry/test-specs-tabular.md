# Test Specifications — Tabular
## Unit: registry
## Initiative: Multi-Tenancy Model Implementation
## Scope: happy-path-negative

| Test Case ID | Title | Preconditions | Steps | Expected Result | Priority | Source | Construction Path |
|---|---|---|---|---|---|---|---|
| TC-R-001 | Alembic migration converts UUID to VARCHAR(64) on all three tables | PostgreSQL test DB; pre-migration schema with UUID tenant_id columns | 1. Run alembic upgrade head; 2. Inspect column types on AgentTable, EventTable, SchemaTable | All three tables have VARCHAR(64) tenant_id; existing rows intact | High | registry / FR-2.1, FR-2.2 | aidlc-docs/platform/multi-tenancy/construction/registry/ |
| TC-R-002 | Registry accepts non-UUID platform tenant ID in CRUD | Registry running with migrated schema | 1. POST /agents with spt_00000000 tenant ID; 2. GET /agents with same ID | 201 on registration; 200 on retrieval; agent present; no UUID error | High | registry / FR-2.7, FR-2.8 | aidlc-docs/platform/multi-tenancy/construction/registry/ |
| TC-R-003 | TenancyMiddleware populates request.state in Registry | Registry running with soorma-service-common TenancyMiddleware | 1. Send request with X-Tenant-ID "spt_test_tenant"; 2. Read request.state.platform_tenant_id | request.state.platform_tenant_id equals "spt_test_tenant" | High | registry / FR-2.6 | aidlc-docs/platform/multi-tenancy/construction/registry/ |
| TC-R-004 | get_platform_tenant_id replaces get_developer_tenant_id | Registry codebase built | 1. Inspect registry_service/api/dependencies.py | get_developer_tenant_id absent; get_platform_tenant_id from soorma_service_common present | High | registry / FR-2.6 | aidlc-docs/platform/multi-tenancy/construction/registry/ |
| TC-R-005 | IS_LOCAL_TESTING SQLite path removed | Registry codebase built | 1. Inspect config.py; 2. Inspect database.py | No IS_LOCAL_TESTING references; no SQLite connection logic | Medium | registry / FR-2.9 | aidlc-docs/platform/multi-tenancy/construction/registry/ |
| TC-R-006 | Registry ORM models use String(64) for tenant_id | Registry codebase built | 1. Inspect AgentTable, EventTable, SchemaTable model definitions | All three define tenant_id as Column(String(64)); no Uuid type | High | registry / FR-2.3, FR-2.4, FR-2.5 | aidlc-docs/platform/multi-tenancy/construction/registry/ |
| TC-R-007 | Registry handles absent X-Tenant-ID gracefully | Registry running | 1. Send GET /agents without X-Tenant-ID header | HTTP 200 or 404; no 500; default platform tenant used | High | registry / FR-2.6 | aidlc-docs/platform/multi-tenancy/construction/registry/ |
| TC-R-008 | Registry rejects tenant_id exceeding 64 chars | Registry running with migrated schema | 1. POST /agents with 65-char X-Tenant-ID | HTTP 422 or DB constraint error; agent NOT stored | High | registry / NFR-3.1 | aidlc-docs/platform/multi-tenancy/construction/registry/ |
| TC-R-009 | Registry does not leak data across platform tenant namespaces | Registry running; agent A under spt_tenant_1; agent B under spt_tenant_2 | 1. GET /agents with spt_tenant_1 | Only agent A returned; agent B absent | High | registry / NFR-1.3 | aidlc-docs/platform/multi-tenancy/construction/registry/ |
