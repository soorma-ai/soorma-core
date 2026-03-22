# Test Specifications — Gherkin
## Unit: sdk-python
## Initiative: Multi-Tenancy Model Implementation
## Scope: happy-path-negative
**Unit abbreviation**: SP = sdk-python

---

```gherkin
@TC-SP-001 @happy-path @FR-7.1
Feature: SDK client sends X-Tenant-ID on every request
  Scenario: SoormaClient initialised with platform_tenant_id injects X-Tenant-ID header
    Given a SoormaClient is instantiated with platform_tenant_id="spt_acme"
    When any service method is called (e.g., memory.store_task_context)
    Then the outgoing HTTP request includes header "X-Tenant-ID: spt_acme"

@TC-SP-002 @happy-path @FR-7.2
Feature: Memory client sends per-call X-Service-Tenant-ID and X-User-ID
  Scenario: MemoryServiceClient.store_task_context sends per-call service identity headers
    Given a MemoryServiceClient is instantiated with platform_tenant_id="spt_acme"
    When store_task_context is called with service_tenant_id="t1" and service_user_id="u1"
    Then the outgoing request includes "X-Tenant-ID: spt_acme"
    And the outgoing request includes "X-Service-Tenant-ID: t1"
    And the outgoing request includes "X-User-ID: u1"

@TC-SP-003 @happy-path @FR-7.3
Feature: Tracker client sends per-call X-Service-Tenant-ID and X-User-ID
  Scenario: TrackerServiceClient.create_plan sends per-call service identity headers
    Given a TrackerServiceClient is instantiated with platform_tenant_id="spt_acme"
    When create_plan is called with service_tenant_id="t2" and service_user_id="u2"
    Then the outgoing request includes "X-Tenant-ID: spt_acme"
    And the outgoing request includes "X-Service-Tenant-ID: t2"
    And the outgoing request includes "X-User-ID: u2"

@TC-SP-004 @happy-path @FR-7.4
Feature: PlatformContext wrappers do not expose platform_tenant_id to agent code
  Scenario: PlatformContext.memory.store_task_context has no platform_tenant_id parameter
    Given the PlatformContext class is inspected
    When the signature of context.memory.store_task_context is examined
    Then the method has no parameter named "platform_tenant_id"
    And calling the method from an agent handler without platform_tenant_id succeeds
    And the X-Tenant-ID header is still sent on the outgoing request

@TC-SP-005 @happy-path @FR-7.5
Feature: soorma init CLI prompts for platform_tenant_id
  Scenario: soorma init stores platform_tenant_id in config file
    Given soorma init is run in a temp directory
    When the user enters "spt_myorg" at the platform_tenant_id prompt
    Then the generated config file contains platform_tenant_id: spt_myorg

@TC-SP-006 @happy-path @FR-7.6
Feature: SDK tests cover new per-call header parameters
  Scenario: SDK test suite includes header injection tests for Memory and Tracker clients
    Given the SDK test suite is executed
    Then at least one test per service client asserts X-Tenant-ID header is present
    And at least one test per service client asserts X-Service-Tenant-ID header is present
    And at least one test per service client asserts X-User-ID header is present
    And all tests pass

@TC-SP-007 @happy-path @FR-8.1
Feature: ARCHITECTURE_PATTERNS.md Section 1 documents two-tier model
  Scenario: Section 1 mentions all three identity header fields
    Given docs/ARCHITECTURE_PATTERNS.md is opened post-implementation
    When Section 1 (Authentication & Authorization) is read
    Then it mentions platform_tenant_id and X-Tenant-ID
    And it mentions service_tenant_id and X-Service-Tenant-ID
    And it mentions service_user_id and X-User-ID

@TC-SP-008 @happy-path @FR-8.2
Feature: ARCHITECTURE_PATTERNS.md Section 2 shows per-call identity
  Scenario: Section 2 code example shows platform_tenant_id at init and per-call service identity
    Given docs/ARCHITECTURE_PATTERNS.md is opened post-implementation
    When Section 2 (SDK Two-Layer Architecture) is read
    Then it contains a code example with platform_tenant_id at client construction
    And the code example shows service_tenant_id and service_user_id as per-call parameters

@TC-SP-009 @negative @FR-7.1 @FR-3a.2
Feature: SDK without platform_tenant_id uses DEFAULT_PLATFORM_TENANT_ID
  Scenario: SoormaClient initialised without platform_tenant_id falls back to default
    Given a SoormaClient is instantiated without platform_tenant_id
    When any service method is called
    Then the outgoing request includes "X-Tenant-ID: DEFAULT_PLATFORM_TENANT_ID"
    And no exception is raised at instantiation time

@TC-SP-010 @negative @FR-7.4 @FR-6.3
Feature: PlatformContext.bus.publish does not forward platform_tenant_id
  Scenario: Agent-supplied platform_tenant_id is not forwarded to Event Service
    Given an agent handler calls context.bus.publish with platform_tenant_id="spt_attempt"
    When the HTTP request body is captured at the Event Service publish endpoint
    Then the EventEnvelope.platform_tenant_id is None or absent
    And the value "spt_attempt" is not present in the published envelope
```
