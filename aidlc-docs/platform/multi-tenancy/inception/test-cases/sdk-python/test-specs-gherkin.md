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
Feature: PlatformContext wrappers hide platform_tenant_id and honor explicit overrides
  Scenario: Explicit service identity args override bound metadata defaults
    Given a wrapper call path with bound metadata exists
    When context.memory or context.tracker method is called with explicit service_tenant_id and service_user_id
    Then wrapper APIs expose no platform_tenant_id parameter
    And explicit service identity values are used over metadata defaults

@TC-SP-005 @happy-path @FR-7.5
Feature: soorma init uses env/default platform tenant path without prompt
  Scenario: No new mandatory platform_tenant_id prompt is introduced
    Given soorma init is run in a temp directory
    When SDK clients are initialized without explicit platform tenant
    Then platform tenant resolves through existing env/default behavior

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
Feature: ARCHITECTURE_PATTERNS.md Section 1 includes identity split and injection note
  Scenario: Section 1 shows init-time vs per-call split and Event Service injection model
    Given docs/ARCHITECTURE_PATTERNS.md is opened post-implementation
    When Section 1 is read
    Then it documents init-time platform identity and per-call service identity split
    And it states Event Service injects platform_tenant_id server-side

@TC-SP-009 @negative @FR-7.1
Feature: SDK without explicit platform_tenant_id uses env/default fallback
  Scenario: Client initialised without explicit platform_tenant_id still sends X-Tenant-ID
    Given a client is instantiated without explicit platform_tenant_id
    When any service method is called
    Then the outgoing request includes header "X-Tenant-ID"
    And platform tenant is resolved through env/default path

@TC-SP-010 @negative @FR-7.4 @FR-6.3
Feature: Publish path does not forward platform_tenant_id in envelope payload
  Scenario: Event payload to Event Service contains no client-provided platform_tenant_id
    Given an event is published via context.bus or EventClient
    When the HTTP request body is captured at the Event Service publish endpoint
    Then the EventEnvelope.platform_tenant_id is None or absent
    And no client-provided platform_tenant_id value is forwarded

@TC-SP-011 @happy-path @FR-8.3
Feature: EventClient publish sends X-Tenant-ID for middleware trust boundary
  Scenario: Event publish request includes platform tenant header
    Given EventClient is initialized with platform tenant context
    When publish is called
    Then the HTTP request includes header "X-Tenant-ID"
    And Event Service middleware can derive request.state.platform_tenant_id
```
