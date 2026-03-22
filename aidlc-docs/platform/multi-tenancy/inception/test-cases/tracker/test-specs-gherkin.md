# Test Specifications — Gherkin
## Unit: tracker
## Initiative: Multi-Tenancy Model Implementation
## Scope: happy-path-negative

Feature: Tracker Service two-tier tenancy column migration, middleware adoption, and GDPR deletion
  As a platform tenant's agentic service
  I want plan and action progress to be correctly namespaced by the three-column identity
  So that tracker data is isolated between platform tenants and service tenants

  # Source: tracker / FR-5.1, FR-5.2, FR-5.3, FR-5.5
  # Construction: aidlc-docs/platform/multi-tenancy/construction/tracker/

  @happy-path @TC-T-001
  Scenario: Alembic migration renames columns and adds platform_tenant_id
    Given a Tracker test database with the pre-migration schema
    When the Alembic migration is applied
    Then plan_progress has service_tenant_id, service_user_id, and platform_tenant_id columns as VARCHAR(64) NOT NULL
    And action_progress has the same three columns
    And the old tenant_id and user_id columns are absent

  # Source: tracker / FR-5.6
  # Construction: aidlc-docs/platform/multi-tenancy/construction/tracker/

  @happy-path @TC-T-002
  Scenario: TenantContext replaces per-route Header parsing in Tracker API handlers
    Given the Tracker Service codebase
    When all API route handler signatures are inspected
    Then no direct Header(...) parameters named x_tenant_id or x_service_tenant_id exist
    And get_tenant_context or get_platform_tenant_id from soorma_service_common is used for identity extraction

  # Source: tracker / FR-5.7, NFR-1.3
  # Construction: aidlc-docs/platform/multi-tenancy/construction/tracker/

  @happy-path @TC-T-003
  Scenario: Tracker API queries filter by all three identity dimensions
    Given a plan_progress row under (spt_1, st1, user1) and another under (spt_2, st1, user1)
    When I query via API with X-Tenant-ID "spt_1", X-Service-Tenant-ID "st1", X-User-ID "user1"
    Then only the row under spt_1 is returned
    And the row under spt_2 is not visible

  # Source: tracker / FR-6.7, FR-5.6
  # Construction: aidlc-docs/platform/multi-tenancy/construction/tracker/

  @happy-path @TC-T-004
  Scenario: NATS handler extracts platform_tenant_id from event envelope
    Given a NATS event with EventEnvelope.platform_tenant_id="spt_from_event_service", tenant_id="st1", user_id="user1"
    When the Tracker NATS event handler processes the event
    Then a plan_progress row is created with platform_tenant_id="spt_from_event_service"
    And service_tenant_id="st1" and service_user_id="user1"

  # Source: tracker / FR-5.6, FR-3a.3
  # Construction: aidlc-docs/platform/multi-tenancy/construction/tracker/

  @happy-path @TC-T-005
  Scenario: set_config_for_session called before DB query in NATS path
    Given a spy on set_config_for_session from soorma_service_common
    When a Tracker NATS event handler is triggered
    Then set_config_for_session is called with the event identity values before any DB write

  # Source: tracker / FR-5.8
  # Construction: aidlc-docs/platform/multi-tenancy/construction/tracker/

  @happy-path @TC-T-006
  Scenario: TrackerDataDeletion removes all rows from both tables for a platform tenant
    Given rows in plan_progress and action_progress under "spt_delete_tracker"
    When delete_by_platform_tenant(platform_tenant_id="spt_delete_tracker") is called
    Then both tables return zero rows for spt_delete_tracker
    And rows for other tenants remain

  # Source: tracker / NFR-3.1
  # Construction: aidlc-docs/platform/multi-tenancy/construction/tracker/

  @happy-path-negative @TC-T-007
  Scenario: Tracker API rejects service_tenant_id exceeding 64 chars
    Given the Tracker Service is running
    When I send a request with X-Service-Tenant-ID containing 65 characters
    Then the response status is 422 or a DB constraint error is returned
    And no data is stored

  # Source: tracker / FR-6.7
  # Construction: aidlc-docs/platform/multi-tenancy/construction/tracker/

  @happy-path-negative @TC-T-008
  Scenario: NATS event with null platform_tenant_id does not create row with NULL identity
    Given a NATS event with EventEnvelope.platform_tenant_id=None
    When the Tracker NATS event handler processes the event
    Then either DEFAULT_PLATFORM_TENANT_ID is used as fallback OR the event is rejected with a warning
    And no DB row with platform_tenant_id=NULL is created
