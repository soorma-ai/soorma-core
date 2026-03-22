# Test Case Index
## Unit: registry
## Initiative: Multi-Tenancy Model Implementation

**Unit abbreviation**: R = registry

| Test Case ID | Title | Source | Scope | Priority |
|---|---|---|---|---|
| TC-R-001 | Alembic migration 004 renames tenant_id to platform_tenant_id and converts UUID to VARCHAR(64) | registry / FR-2.1, FR-2.2 | happy-path | High |
| TC-R-002 | Registry accepts non-UUID platform tenant ID in CRUD | registry / FR-2.7, FR-2.8 | happy-path | High |
| TC-R-003 | TenancyMiddleware populates request.state in Registry | registry / FR-2.6 | happy-path | High |
| TC-R-004 | get_platform_tenant_id replaces get_developer_tenant_id | registry / FR-2.6 | happy-path | High |
| TC-R-005 | IS_LOCAL_TESTING SQLite path removed | registry / FR-2.9 | happy-path | Medium |
| TC-R-006 | Registry ORM models rename tenant_id to platform_tenant_id with String(64) type | registry / FR-2.3, FR-2.4, FR-2.5 | happy-path | High |
| TC-R-007 | Registry handles absent X-Tenant-ID gracefully | registry / FR-2.6 | happy-path-negative | High |
| TC-R-008 | Registry rejects tenant_id exceeding 64 chars | registry / NFR-3.1 | happy-path-negative | High |
| TC-R-009 | Registry enforces cross-tenant isolation at the database layer (SOC2 evidence) | registry / NFR-1.3 | happy-path-negative | High |
| TC-R-010 | All Registry v1 route handlers use get_tenanted_db not bare get_db | registry / BR-R06 | happy-path | High |
| TC-R-011 | Migration 004 deploys ENABLE and FORCE ROW LEVEL SECURITY with isolation policies | registry / BR-R07, BR-R07a | happy-path | High |
