# Test Specifications — Gherkin
## Unit: memory
## Initiative: Multi-Tenancy Model Implementation
## Scope: happy-path-negative

Feature: Memory Service two-tier tenancy schema migration, RLS enforcement, and GDPR deletion
  As a platform tenant's agentic service
  I want memory operations to be correctly namespaced by the three-column identity
  So that data is isolated between platform tenants and service tenants

  # Source: memory / FR-3.1, FR-3.2
  # Construction: aidlc-docs/platform/multi-tenancy/construction/memory/

  @happy-path @TC-M-001
  Scenario: Alembic migration drops tenants and users reference tables
    Given the Memory Service pre-migration schema exists
    When the Alembic breaking migration is applied
    Then the "tenants" table does not exist
    And the "users" table does not exist
    And no foreign key constraints reference either table

  # Source: memory / FR-3.3, FR-3.5
  # Construction: aidlc-docs/platform/multi-tenancy/construction/memory/

  @happy-path @TC-M-002
  Scenario: All 8 memory tables have three-column identity after migration
    Given the Alembic migration has been applied
    When each of the 8 memory tables is inspected
    Then each table has platform_tenant_id VARCHAR(64) NOT NULL
    And each table has service_tenant_id VARCHAR(64) NOT NULL
    And each table has service_user_id VARCHAR(64) (nullable per design)

  # Source: memory / FR-3b.2, FR-3b.4
  # Construction: aidlc-docs/platform/multi-tenancy/construction/memory/

  @happy-path @TC-M-003
  Scenario: RLS policies prevent cross-tenant data access
    Given two rows in semantic_memory under different platform_tenant_ids
    When I set session variable app.platform_tenant_id to "spt_tenant_1" via set_config
    And I query semantic_memory
    Then only the row with platform_tenant_id "spt_tenant_1" is returned
    And the row for "spt_tenant_2" is invisible

  # Source: memory / FR-3.8, FR-3.9
  # Construction: aidlc-docs/platform/multi-tenancy/construction/memory/

  @happy-path @TC-M-004
  Scenario: Memory API stores and retrieves semantic memory with three-column identity
    Given the Memory Service running with migrated schema and TenancyMiddleware
    When I POST /semantic-memory with X-Tenant-ID "spt_abc", X-Service-Tenant-ID "tenant_xyz", X-User-ID "user_123"
    Then the response status is 201
    When I GET /semantic-memory with the same headers
    Then the response status is 200
    And the stored item appears in the response

  # Source: memory / FR-4.1, FR-4.2
  # Construction: aidlc-docs/platform/multi-tenancy/construction/memory/

  @happy-path @TC-M-005
  Scenario: MemoryDataDeletion.delete_by_platform_tenant removes all rows for that platform tenant
    Given rows in semantic_memory, episodic_memory, and task_context under "spt_delete_me"
    When delete_by_platform_tenant(platform_tenant_id="spt_delete_me") is called
    Then all three tables return zero rows for platform_tenant_id="spt_delete_me"
    And rows under other platform_tenant_id values remain

  # Source: memory / FR-4.1, NFR-1.3
  # Construction: aidlc-docs/platform/multi-tenancy/construction/memory/

  @happy-path @TC-M-006
  Scenario: delete_by_service_tenant only deletes within the specified platform tenant namespace
    Given rows (spt_1, st1, u1) and (spt_2, st1, u1) in semantic_memory
    When delete_by_service_tenant(platform_tenant_id="spt_1", service_tenant_id="st1") is called
    Then the row (spt_1, st1, u1) is deleted
    And the row (spt_2, st1, u1) remains

  # Source: memory / FR-3.6
  # Construction: aidlc-docs/platform/multi-tenancy/construction/memory/

  @happy-path @TC-M-007
  Scenario: Memory Service uses shared TenancyMiddleware from soorma-service-common
    Given the Memory Service codebase
    When memory_service/main.py is inspected
    Then TenancyMiddleware is imported from soorma_service_common
    And no local TenancyMiddleware class exists in memory_service

  # Source: memory / FR-3b.1, FR-3b.2
  # Construction: aidlc-docs/platform/multi-tenancy/construction/memory/

  @happy-path @TC-M-008
  Scenario: Rebuilt RLS policies use string comparison without ::UUID cast
    Given the Alembic migration has been applied
    When pg_policies is queried for memory table policies
    Then no policy qualification contains "::uuid"
    And each policy uses string equality on current_setting values

  # Source: memory / FR-3b.2, FR-3b.4
  # Construction: aidlc-docs/platform/multi-tenancy/construction/memory/

  @happy-path-negative @TC-M-009
  Scenario: Query without RLS session variables returns no rows
    Given rows exist in semantic_memory under a known platform_tenant_id
    When a direct database query is run without calling set_config first
    Then zero rows are returned from semantic_memory

  # Source: memory / FR-3.8
  # Construction: aidlc-docs/platform/multi-tenancy/construction/memory/

  @happy-path-negative @TC-M-010
  Scenario: Memory API rejects request with missing service tenant for user-scoped operations
    Given the Memory Service is running
    When I POST /semantic-memory with X-Tenant-ID and X-User-ID but without X-Service-Tenant-ID
    Then the response status is 400 or 422
    And the error message indicates service_tenant_id is required

  # Source: memory / FR-4.1, NFR-1.3
  # Construction: aidlc-docs/platform/multi-tenancy/construction/memory/

  @happy-path-negative @TC-M-011
  Scenario: delete_by_service_user only deletes the specific user within the service tenant
    Given rows (spt_1, st1, user_A) and (spt_1, st1, user_B) in working_memory
    When delete_by_service_user(platform_tenant_id="spt_1", service_tenant_id="st1", service_user_id="user_A") is called
    Then the row for user_A is deleted
    And the row for user_B remains
