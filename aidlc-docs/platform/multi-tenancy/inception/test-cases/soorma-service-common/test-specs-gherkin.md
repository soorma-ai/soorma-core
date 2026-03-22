# Test Specifications — Gherkin
## Unit: soorma-service-common
## Initiative: Multi-Tenancy Model Implementation
## Scope: happy-path-negative

Feature: soorma-service-common TenancyMiddleware, RLS activation, and TenantContext bundle
  As a backend service developer
  I want a shared middleware and dependency library
  So that all services consistently extract tenant identity and activate RLS with zero per-service boilerplate

  # Source: soorma-service-common / FR-3a.2
  # Construction: aidlc-docs/platform/multi-tenancy/construction/soorma-service-common/

  @happy-path @TC-SSC-001
  Scenario: TenancyMiddleware extracts all three identity headers to request.state
    Given a FastAPI app with TenancyMiddleware registered
    When a request is sent with X-Tenant-ID "spt_abc", X-Service-Tenant-ID "tenant_xyz", X-User-ID "user_123"
    Then request.state.platform_tenant_id equals "spt_abc"
    And request.state.service_tenant_id equals "tenant_xyz"
    And request.state.service_user_id equals "user_123"

  # Source: soorma-service-common / FR-3a.2
  # Construction: aidlc-docs/platform/multi-tenancy/construction/soorma-service-common/

  @happy-path @TC-SSC-002
  Scenario: Missing X-Tenant-ID defaults to DEFAULT_PLATFORM_TENANT_ID
    Given a FastAPI app with TenancyMiddleware registered
    When a request is sent without the X-Tenant-ID header
    Then request.state.platform_tenant_id equals "spt_00000000-0000-0000-0000-000000000000"

  # Source: soorma-service-common / FR-3a.3
  # Construction: aidlc-docs/platform/multi-tenancy/construction/soorma-service-common/

  @happy-path @TC-SSC-003
  Scenario: get_tenanted_db calls set_config for all three session variables
    Given a FastAPI app with TenancyMiddleware registered and a route using Depends(get_tenanted_db)
    When a request is sent with all three tenant headers
    Then set_config("app.platform_tenant_id", ..., True) is called with the header value
    And set_config("app.service_tenant_id", ..., True) is called with the header value
    And set_config("app.service_user_id", ..., True) is called with the header value

  # Source: soorma-service-common / FR-3a.4
  # Construction: aidlc-docs/platform/multi-tenancy/construction/soorma-service-common/

  @happy-path @TC-SSC-004
  Scenario: get_tenant_context bundles all three identity dims plus tenanted DB session
    Given a FastAPI app with TenancyMiddleware registered and a route using Depends(get_tenant_context)
    When a request is sent with headers X-Tenant-ID "spt_abc", X-Service-Tenant-ID "t1", X-User-ID "u1"
    Then ctx.platform_tenant_id equals "spt_abc"
    And ctx.service_tenant_id equals "t1"
    And ctx.service_user_id equals "u1"
    And ctx.db is a live database session that had set_config called

  # Source: soorma-service-common / FR-3a (ABC)
  # Construction: aidlc-docs/platform/multi-tenancy/construction/soorma-service-common/

  @happy-path @TC-SSC-005
  Scenario: PlatformTenantDataDeletion enforces all three abstract methods
    Given the PlatformTenantDataDeletion ABC is imported from soorma_service_common
    When I define an incomplete subclass without implementing all three abstract methods
    And I attempt to instantiate the incomplete subclass
    Then a TypeError is raised listing the unimplemented abstract methods

  # Source: soorma-service-common / FR-3a.3
  # Construction: aidlc-docs/platform/multi-tenancy/construction/soorma-service-common/

  @happy-path @TC-SSC-006
  Scenario: set_config_for_session activates RLS variables for NATS-path DB sessions
    Given a raw database session is obtained (simulating NATS path)
    When set_config_for_session(db, platform_tenant_id="spt_abc", service_tenant_id="t1", service_user_id="u1") is called
    Then set_config is called for all three app session variables with the provided values and transaction=True

  # Source: soorma-service-common / FR-3a.2
  # Construction: aidlc-docs/platform/multi-tenancy/construction/soorma-service-common/

  @happy-path-negative @TC-SSC-007
  Scenario: Missing optional service tenant headers result in None in request.state
    Given a FastAPI app with TenancyMiddleware registered
    When a request is sent with only X-Tenant-ID "spt_abc" and no service tenant or user headers
    Then request.state.service_tenant_id is None
    And request.state.service_user_id is None
    And the request is processed without error

  # Source: soorma-service-common / FR-3a.3
  # Construction: aidlc-docs/platform/multi-tenancy/construction/soorma-service-common/

  @happy-path-negative @TC-SSC-008
  Scenario: get_tenanted_db does not yield session when set_config raises
    Given a FastAPI route using Depends(get_tenanted_db) and the DB session patched to raise on set_config
    When a request is made to that route
    Then the route handler is NOT called
    And an HTTP 500 error response is returned

  # Source: soorma-service-common / FR-3a.1
  # Construction: aidlc-docs/platform/multi-tenancy/construction/soorma-service-common/

  @happy-path-negative @TC-SSC-009
  Scenario: soorma-service-common is not a dependency of the SDK
    Given the SDK pyproject.toml at sdk/python/pyproject.toml
    When I inspect its dependencies
    Then soorma-service-common is NOT listed as a dependency
    And FastAPI and Starlette are NOT in the SDK dependency tree via soorma-service-common
