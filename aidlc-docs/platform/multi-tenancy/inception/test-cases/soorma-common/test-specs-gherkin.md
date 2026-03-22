# Test Specifications — Gherkin
## Unit: soorma-common
## Initiative: Multi-Tenancy Model Implementation
## Scope: happy-path-negative

Feature: soorma-common two-tier tenancy constants and EventEnvelope fields
  As a service or SDK consumer
  I want the shared tenancy constants and EventEnvelope fields to be correctly defined
  So that all services and the SDK can use a consistent, opaque-string tenancy model

  # Source: soorma-common / FR-1.1
  # Construction: aidlc-docs/platform/multi-tenancy/construction/soorma-common/

  @happy-path @TC-SC-001
  Scenario: DEFAULT_PLATFORM_TENANT_ID constant is accessible with correct value
    Given the soorma_common package is installed
    When I import DEFAULT_PLATFORM_TENANT_ID from soorma_common.tenancy
    Then its value equals "spt_00000000-0000-0000-0000-000000000000"

  # Source: soorma-common / FR-1.2
  # Construction: aidlc-docs/platform/multi-tenancy/construction/soorma-common/

  @happy-path @TC-SC-002
  Scenario: SOORMA_PLATFORM_TENANT_ID env var overrides the default constant
    Given the environment variable SOORMA_PLATFORM_TENANT_ID is set to "spt_custom_tenant_abc123"
    When the effective platform tenant ID is read from soorma_common.tenancy
    Then the returned value equals "spt_custom_tenant_abc123"

  # Source: soorma-common / FR-1.3
  # Construction: aidlc-docs/platform/multi-tenancy/construction/soorma-common/

  @happy-path @TC-SC-003
  Scenario: DEFAULT_PLATFORM_TENANT_ID has deprecation warning comment in source
    Given the source file soorma_common/tenancy.py exists
    When I read the constant definition for DEFAULT_PLATFORM_TENANT_ID
    Then a comment or docstring adjacent to the constant warns against production use
    And the warning mentions waiting for the Identity Service

  # Source: soorma-common / FR-6.3
  # Construction: aidlc-docs/platform/multi-tenancy/construction/soorma-common/

  @happy-path @TC-SC-004
  Scenario: EventEnvelope gains platform_tenant_id field as Optional[str]
    Given the soorma_common package is installed
    When I construct EventEnvelope(topic="test", data={}) without specifying platform_tenant_id
    Then envelope.platform_tenant_id is None
    When I construct EventEnvelope(topic="test", data={}, platform_tenant_id="spt_abc")
    Then envelope.platform_tenant_id equals "spt_abc"

  # Source: soorma-common / FR-6.4
  # Construction: aidlc-docs/platform/multi-tenancy/construction/soorma-common/

  @happy-path @TC-SC-005
  Scenario: EventEnvelope field docstrings describe two-tier semantics
    Given the EventEnvelope model is defined in soorma_common
    When I inspect the field definitions for platform_tenant_id, tenant_id, and user_id
    Then platform_tenant_id description states it is injected by the Event Service
    And tenant_id description references "service tenant"
    And user_id description references "service user"

  # Source: soorma-common / FR-1.4
  # Construction: aidlc-docs/platform/multi-tenancy/construction/soorma-common/

  @happy-path @TC-SC-006
  Scenario: soorma_common imposes no UUID format validation on tenant/user IDs
    Given the soorma_common package is installed
    When I construct EventEnvelope with non-UUID values for tenant_id, user_id, and platform_tenant_id
    Then no ValidationError is raised
    And all three fields store the provided strings verbatim

  # Source: soorma-common / FR-1.2
  # Construction: aidlc-docs/platform/multi-tenancy/construction/soorma-common/

  @happy-path-negative @TC-SC-007
  Scenario: Absent SOORMA_PLATFORM_TENANT_ID env var falls back to hardcoded default
    Given the environment variable SOORMA_PLATFORM_TENANT_ID is not set
    When the effective platform tenant ID is read from soorma_common.tenancy
    Then the returned value equals "spt_00000000-0000-0000-0000-000000000000"

  # Source: soorma-common / NFR-3.1
  # Construction: aidlc-docs/platform/multi-tenancy/construction/soorma-common/

  @happy-path-negative @TC-SC-008
  Scenario: EventEnvelope rejects platform_tenant_id longer than 64 characters
    Given the soorma_common package is installed
    When I attempt to construct EventEnvelope with a platform_tenant_id of 65 characters
    Then a ValidationError is raised indicating the value exceeds the maximum allowed length

  # Source: soorma-common / FR-1.2
  # Construction: aidlc-docs/platform/multi-tenancy/construction/soorma-common/

  @happy-path-negative @TC-SC-009
  Scenario: Empty string SOORMA_PLATFORM_TENANT_ID does not override to empty value
    Given the environment variable SOORMA_PLATFORM_TENANT_ID is set to an empty string
    When the effective platform tenant ID is read from soorma_common.tenancy
    Then the result is either the hardcoded default or a configuration error is raised
    And the effective platform tenant ID is never an empty string
