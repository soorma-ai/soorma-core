# Test Specifications — Gherkin
## Unit: memory
## Initiative: Multi-Tenancy Model Implementation
## Scope: happy-path-negative

Feature: Memory Service two-tier tenancy schema migration, RLS enforcement, and GDPR deletion
  As a platform tenant's agentic service
  I want memory operations to be correctly namespaced by the three-column identity
  So that data is isolated between platform tenants and service tenants

  # Source: memory / FR-3.1, FR-3.2
  # Migration file: services/memory/alembic/versions/008_multi_tenancy_three_column_identity.py
  # Construction: aidlc-docs/platform/multi-tenancy/construction/memory/

  @happy-path @TC-M-001
  Scenario: Alembic migration drops tenants and users reference tables
    Given the Memory Service pre-migration schema exists in a test database
    When migration 008_multi_tenancy_three_column_identity.py is applied
    Then information_schema.tables contains no row for "tenants"
    And information_schema.tables contains no row for "users"
    And pg_constraint contains no FK referencing tenants.id or users.id

  # Source: memory / FR-3.3, FR-3.5
  # ORM model: services/memory/src/memory_service/models/memory.py
  # Construction: aidlc-docs/platform/multi-tenancy/construction/memory/

  @happy-path @TC-M-002
  Scenario: All 8 memory tables have three-column identity after migration
    Given migration 008_multi_tenancy_three_column_identity.py has been applied
    When information_schema.columns is queried for each of the 8 memory tables
    Then each table has platform_tenant_id VARCHAR(64) NOT NULL
    And each table has service_tenant_id VARCHAR(64) nullable
    And each table has service_user_id VARCHAR(64) nullable
    And no UUID-typed tenant or user columns remain on any of the 8 tables

  # Source: memory / FR-3b.2, FR-3b.4
  # get_tenanted_db: services/memory/src/memory_service/core/dependencies.py
  # RLS policy pattern: {table_name}_platform_rls
  # Construction: aidlc-docs/platform/multi-tenancy/construction/memory/

  @happy-path @TC-M-003
  Scenario: RLS policy semantic_memory_platform_rls prevents cross-tenant data access
    Given two rows in semantic_memory under platform_tenant_id "spt_tenant_1" and "spt_tenant_2"
    When get_tenanted_db sets session variable app.platform_tenant_id to "spt_tenant_1" via set_config with transaction=true
    And semantic_memory is queried
    Then only the row with platform_tenant_id "spt_tenant_1" is returned
    And the row for "spt_tenant_2" is invisible (filtered by RLS)

  # Source: memory / FR-3.8, FR-3.9
  # TenancyMiddleware: soorma_service_common.TenancyMiddleware
  # Router: services/memory/src/memory_service/api/v1/semantic.py
  # Construction: aidlc-docs/platform/multi-tenancy/construction/memory/

  @happy-path @TC-M-004
  Scenario: Memory API stores and retrieves semantic memory with three-column identity
    Given the Memory Service running with migrated schema and TenancyMiddleware from soorma_service_common
    When I POST /semantic-memory with X-Tenant-ID "spt_abc", X-Service-Tenant-ID "tenant_xyz", X-User-ID "user_123"
    Then the response status is 201
    When I GET /semantic-memory with the same three headers
    Then the response status is 200
    And the stored item appears in the response with platform_tenant_id, service_tenant_id, service_user_id fields

  # Source: memory / FR-4.1, FR-4.2
  # Class: MemoryDataDeletion in services/memory/src/memory_service/services/data_deletion.py
  # Covered tables (6): semantic_memory, episodic_memory, procedural_memory, working_memory, task_context, plan_context
  # Construction: aidlc-docs/platform/multi-tenancy/construction/memory/

  @happy-path @TC-M-005
  Scenario: MemoryDataDeletion.delete_by_platform_tenant removes all rows across 6 covered tables
    Given rows in semantic_memory, episodic_memory, and task_context under platform_tenant_id "spt_delete_me"
    When MemoryDataDeletion.delete_by_platform_tenant(db, platform_tenant_id="spt_delete_me") is called
    Then all three tables return zero rows for platform_tenant_id "spt_delete_me"
    And rows under other platform_tenant_id values remain unaffected

  # Source: memory / FR-4.1, NFR-1.3
  # WHERE pattern: Model.platform_tenant_id == p AND Model.service_tenant_id == st
  # Construction: aidlc-docs/platform/multi-tenancy/construction/memory/

  @happy-path @TC-M-006
  Scenario: delete_by_service_tenant only deletes within the specified platform tenant namespace
    Given rows (spt_1, st1, u1) and (spt_2, st1, u1) in semantic_memory
    When MemoryDataDeletion.delete_by_service_tenant(db, platform_tenant_id="spt_1", service_tenant_id="st1") is called
    Then the row (spt_1, st1, u1) is deleted
    And the row (spt_2, st1, u1) remains

  # Source: memory / FR-3.6
  # Deleted file: services/memory/src/memory_service/core/middleware.py
  # Import: from soorma_service_common import TenancyMiddleware
  # Construction: aidlc-docs/platform/multi-tenancy/construction/memory/

  @happy-path @TC-M-007
  Scenario: Memory Service uses shared TenancyMiddleware from soorma-service-common
    Given the Memory Service codebase after migration
    When services/memory/src/memory_service/core/middleware.py is checked for existence
    Then the file does not exist (deleted entirely)
    When services/memory/src/memory_service/main.py is inspected
    Then TenancyMiddleware is imported from soorma_service_common
    And app.add_middleware(TenancyMiddleware) is present

  # Source: memory / FR-3b.1, FR-3b.2
  # Policy name: {table_name}_platform_rls; FORCE ROW LEVEL SECURITY applied to all 8 tables
  # Construction: aidlc-docs/platform/multi-tenancy/construction/memory/

  @happy-path @TC-M-008
  Scenario: Rebuilt RLS policies use string comparison without ::UUID cast and enforce FORCE RLS
    Given migration 008_multi_tenancy_three_column_identity.py has been applied
    When pg_policies is queried for the 8 memory table policies
    Then 8 policies exist named {table_name}_platform_rls (one per table)
    And no policy qualification contains "::uuid"
    And each policy qual is: platform_tenant_id = current_setting('app.platform_tenant_id', true)
    And rowsecurity and forcersls are both true for each of the 8 tables

  # Source: memory / FR-3b.2, FR-3b.4
  # current_setting missing_ok=true returns '' when unset; '' matches no platform_tenant_id
  # Construction: aidlc-docs/platform/multi-tenancy/construction/memory/

  @happy-path-negative @TC-M-009
  Scenario: Query without RLS session variables returns zero rows due to empty current_setting
    Given a row exists in semantic_memory under platform_tenant_id "spt_test_rls"
    When a raw AsyncSession is obtained directly (bypassing get_tenanted_db, no set_config called)
    And semantic_memory is queried on that raw connection
    Then zero rows are returned
    And no PostgreSQL error is raised (missing_ok=true prevents error)

  # Source: memory / FR-3.8
  # TenancyMiddleware sets service_tenant_id="" when X-Service-Tenant-ID is absent
  # Construction: aidlc-docs/platform/multi-tenancy/construction/memory/

  @happy-path-negative @TC-M-010
  Scenario: Memory API rejects request with missing service tenant for user-scoped operations
    Given the Memory Service is running with TenancyMiddleware from soorma_service_common
    When I POST /semantic-memory with X-Tenant-ID "spt_abc" and X-User-ID "user_123" but without X-Service-Tenant-ID
    Then the response status is 422 or 400
    And the error message references service_tenant_id as required for user-scoped operations

  # Source: memory / FR-4.1, NFR-1.3
  # WHERE pattern: platform_tenant_id AND service_tenant_id AND service_user_id (Pattern 3)
  # Construction: aidlc-docs/platform/multi-tenancy/construction/memory/

  @happy-path-negative @TC-M-011
  Scenario: delete_by_service_user only deletes the specific user triplet within the service tenant
    Given rows (spt_1, st1, user_A) and (spt_1, st1, user_B) in working_memory
    When MemoryDataDeletion.delete_by_service_user(db, platform_tenant_id="spt_1", service_tenant_id="st1", service_user_id="user_A") is called
    Then the row for user_A is deleted
    And the row for user_B remains

  # Source: memory / BR-U4-06
  # MemoryDataDeletion covers exactly 6 tables; Plan and Session are NOT included
  # Construction: aidlc-docs/platform/multi-tenancy/construction/memory/

  @happy-path @TC-M-012
  Scenario: MemoryDataDeletion does not delete plans or sessions rows when deleting by platform tenant
    Given a row in plans and a row in sessions under platform_tenant_id "spt_delete_me"
    And a row in semantic_memory under platform_tenant_id "spt_delete_me"
    When MemoryDataDeletion.delete_by_platform_tenant(db, platform_tenant_id="spt_delete_me") is called
    Then semantic_memory returns zero rows for "spt_delete_me"
    And the plans row for "spt_delete_me" still exists
    And the sessions row for "spt_delete_me" still exists

  # Source: memory / BR-U4-08, Pattern 4
  # Admin router: services/memory/src/memory_service/api/v1/admin.py
  # Uses Depends(get_db) + set_config_for_session from soorma_service_common
  # Construction: aidlc-docs/platform/multi-tenancy/construction/memory/

  @happy-path @TC-M-013
  Scenario: Admin deletion endpoint activates RLS session via set_config_for_session before bulk delete
    Given rows in semantic_memory and episodic_memory under platform_tenant_id "spt_admin_delete"
    When the admin deletion endpoint is called for platform_tenant_id "spt_admin_delete"
    Then the response status is 200
    And the response includes a rows-deleted count greater than zero
    And semantic_memory returns zero rows for "spt_admin_delete"
    And episodic_memory returns zero rows for "spt_admin_delete"
    And set_config_for_session from soorma_service_common was used (not get_tenanted_db)
