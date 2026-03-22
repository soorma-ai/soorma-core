# Test Specifications — Gherkin
## Unit: event-service
## Initiative: Multi-Tenancy Model Implementation
## Scope: happy-path-negative
**Unit abbreviation**: ES = event-service

---

```gherkin
@TC-ES-001 @happy-path @FR-6.5
Feature: Event Service TenancyMiddleware registration
  Scenario: TenancyMiddleware populates request.state.platform_tenant_id
    Given the Event Service is running with TenancyMiddleware registered
    When a POST /publish request is received with header "X-Tenant-ID: spt_test"
    Then request.state.platform_tenant_id is "spt_test"

@TC-ES-002 @happy-path @FR-6.6
Feature: publish_event injects platform_tenant_id from request.state
  Scenario: Envelope with None platform_tenant_id is overwritten by authenticated value
    Given the Event Service is running
    And a NATS subscriber is listening on the target subject
    When POST /publish is called with "X-Tenant-ID: spt_authentic" and EventEnvelope.platform_tenant_id=None
    Then the envelope delivered to NATS has platform_tenant_id="spt_authentic"

@TC-ES-003 @happy-path @FR-6.3 @FR-6.6
Feature: Event Service rejects client-supplied platform_tenant_id
  Scenario: SDK-supplied platform_tenant_id is overwritten with authenticated value
    Given the Event Service is running
    And a NATS subscriber is listening on the target subject
    When POST /publish is called with "X-Tenant-ID: spt_real" and EventEnvelope.platform_tenant_id="spt_spoofed"
    Then the envelope delivered to NATS has platform_tenant_id="spt_real"
    And platform_tenant_id "spt_spoofed" is not present in any delivered envelope

@TC-ES-004 @happy-path @FR-6.5 @FR-3a.2
Feature: Missing X-Tenant-ID falls back to DEFAULT_PLATFORM_TENANT_ID
  Scenario: Publish without X-Tenant-ID uses default platform tenant
    Given the Event Service is running
    And DEFAULT_PLATFORM_TENANT_ID is configured
    When POST /publish is called without "X-Tenant-ID" header and with a valid EventEnvelope
    Then the envelope delivered to NATS has platform_tenant_id=DEFAULT_PLATFORM_TENANT_ID

@TC-ES-005 @happy-path @FR-6.1 @FR-6.2
Feature: Event Service passes through service tenant fields unmodified
  Scenario: tenant_id and user_id values are preserved after injection
    Given the Event Service is running
    When POST /publish is called with EventEnvelope(tenant_id="svc_xyz", user_id="usr_abc")
    Then the envelope delivered to NATS has tenant_id="svc_xyz"
    And the envelope delivered to NATS has user_id="usr_abc"

@TC-ES-006 @happy-path @FR-6.6
Feature: publish_event route parameter naming is correct
  Scenario: Route handler has distinct parameter names for HTTP request and publish body
    Given the publish_event route handler source is inspected
    Then the handler has parameter "publish_request" of type PublishRequest
    And the handler has parameter "http_request" of type fastapi.Request
    And there is no parameter name collision

@TC-ES-007 @negative @FR-6.6
Feature: Malformed publish request is rejected before injection
  Scenario: Empty EventEnvelope body is rejected with HTTP 422
    Given the Event Service is running
    When POST /publish is called with "X-Tenant-ID: spt_test" and an empty JSON body {}
    Then the response status code is 422
    And no event is published to NATS

@TC-ES-008 @negative @NFR-3.1
Feature: Oversized X-Tenant-ID is not injected
  Scenario: X-Tenant-ID header exceeding 64 characters is rejected or blocked
    Given the Event Service is running
    When POST /publish is called with "X-Tenant-ID: <65-char string>" and a valid EventEnvelope
    Then either the response status code is 422
    Or the oversized platform_tenant_id is never stored by subscribing services
```
