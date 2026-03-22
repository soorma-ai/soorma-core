# Test Specifications — Gherkin
## Unit: registry
## Initiative: Multi-Tenancy Model Implementation
## Scope: happy-path-negative

Feature: Registry Service two-tier tenancy migration and middleware adoption
  As a platform tenant registering agents and event schemas
  I want the Registry to accept opaque string tenant IDs and enforce per-tenant data isolation
  So that the two-tier tenancy model is consistently applied across soorma-core

  # Source: registry / FR-2.1, FR-2.2
  # Construction: aidlc-docs/platform/multi-tenancy/construction/registry/

  @happy-path @TC-R-001
  Scenario: Alembic migration converts tenant_id UUID to VARCHAR(64) on all three tables
    Given a PostgreSQL test database with the pre-migration schema
    When the Alembic migration is applied
    Then AgentTable.tenant_id column type is VARCHAR(64)
    And EventTable.tenant_id column type is VARCHAR(64)
    And SchemaTable.tenant_id column type is VARCHAR(64)
    And existing rows remain intact

  # Source: registry / FR-2.7, FR-2.8
  # Construction: aidlc-docs/platform/multi-tenancy/construction/registry/

  @happy-path @TC-R-002
  Scenario: Registry accepts non-UUID platform tenant ID in CRUD operations
    Given the Registry Service is running with the migrated schema
    When I send POST /agents with X-Tenant-ID "spt_00000000-0000-0000-0000-000000000000"
    Then the response status is 201
    When I send GET /agents with the same X-Tenant-ID
    Then the response status is 200
    And the registered agent appears in the response

  # Source: registry / FR-2.6
  # Construction: aidlc-docs/platform/multi-tenancy/construction/registry/

  @happy-path @TC-R-003
  Scenario: TenancyMiddleware populates request.state.platform_tenant_id in Registry
    Given the Registry Service is running with TenancyMiddleware from soorma-service-common
    When a request is sent with X-Tenant-ID "spt_test_tenant"
    Then request.state.platform_tenant_id equals "spt_test_tenant"

  # Source: registry / FR-2.6
  # Construction: aidlc-docs/platform/multi-tenancy/construction/registry/

  @happy-path @TC-R-004
  Scenario: get_platform_tenant_id dependency replaces get_developer_tenant_id
    Given the Registry Service codebase is built
    When registry_service/api/dependencies.py is inspected
    Then get_developer_tenant_id is NOT defined or imported
    And get_platform_tenant_id from soorma_service_common is present

  # Source: registry / FR-2.9
  # Construction: aidlc-docs/platform/multi-tenancy/construction/registry/

  @happy-path @TC-R-005
  Scenario: IS_LOCAL_TESTING SQLite path is removed from Registry Service
    Given the Registry Service codebase is built
    When registry_service/core/config.py and database.py are inspected
    Then no IS_LOCAL_TESTING references exist
    And no SQLite connection strings or conditional engine selection exist

  # Source: registry / FR-2.3, FR-2.4, FR-2.5
  # Construction: aidlc-docs/platform/multi-tenancy/construction/registry/

  @happy-path @TC-R-006
  Scenario: Registry ORM models use String(64) for tenant_id
    Given the Registry Service codebase is built
    When the SQLAlchemy model for AgentTable, EventTable, and SchemaTable is inspected
    Then each model defines tenant_id as Column(String(64)) with no Uuid type

  # Source: registry / FR-2.6
  # Construction: aidlc-docs/platform/multi-tenancy/construction/registry/

  @happy-path-negative @TC-R-007
  Scenario: Registry handles absent X-Tenant-ID gracefully using default
    Given the Registry Service is running
    When a GET /agents request is sent without X-Tenant-ID
    Then the response status is 200 or 404 (data-dependent)
    And no HTTP 500 or unhandled exception occurs

  # Source: registry / NFR-3.1
  # Construction: aidlc-docs/platform/multi-tenancy/construction/registry/

  @happy-path-negative @TC-R-008
  Scenario: Registry rejects agent registration with tenant_id exceeding 64 chars
    Given the Registry Service is running
    When I send POST /agents with X-Tenant-ID containing 65 characters
    Then the response status is 422 or a database constraint violation is returned
    And no agent is stored

  # Source: registry / NFR-1.3
  # Construction: aidlc-docs/platform/multi-tenancy/construction/registry/

  @happy-path-negative @TC-R-009
  Scenario: Registry does not leak data across platform tenant namespaces
    Given agent A is registered under X-Tenant-ID "spt_tenant_1"
    And agent B is registered under X-Tenant-ID "spt_tenant_2"
    When I send GET /agents with X-Tenant-ID "spt_tenant_1"
    Then only agent A appears in the response
    And agent B is NOT returned
