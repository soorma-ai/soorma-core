Feature: Unit-1 shared identity dependency validation

@happy-path @TC-U1-001
Scenario: Validate and pass through full user identity context
  # Source: unit-1 / FR-2
  # Construction: aidlc-docs/platform/memory-identity-scope/construction/unit-1/
  Given a resolved request context with non-empty service_tenant_id and service_user_id
  When require_user_context is invoked
  Then the same context object is returned
  And no HTTP error is raised

@negative @TC-U1-002
Scenario: Reject missing service tenant context
  # Source: unit-1 / FR-2
  # Construction: aidlc-docs/platform/memory-identity-scope/construction/unit-1/
  Given a resolved request context with missing service_tenant_id
  When require_user_context is invoked
  Then an HTTP 400 error is raised
  And the error detail is generic and transport-agnostic

@negative @TC-U1-003
Scenario: Reject missing service user context
  # Source: unit-1 / FR-2
  # Construction: aidlc-docs/platform/memory-identity-scope/construction/unit-1/
  Given a resolved request context with missing service_user_id
  When require_user_context is invoked
  Then an HTTP 400 error is raised
  And the error detail is generic and transport-agnostic

@negative @TC-U1-004
Scenario: Reject empty or whitespace identity values
  # Source: unit-1 / NFR-1
  # Construction: aidlc-docs/platform/memory-identity-scope/construction/unit-1/
  Given a resolved request context where one required identity value is empty or whitespace-only
  When require_user_context is invoked
  Then an HTTP 400 error is raised
  And no header implementation detail appears in the error detail

@negative @TC-U1-005
Scenario: Aggregate identity failures and emit structured safe warning log
  # Source: unit-1 / NFR-1
  # Construction: aidlc-docs/platform/memory-identity-scope/construction/unit-1/code/
  Given a resolved request context with platform_tenant_id and both required identity dimensions missing
  When require_user_context is invoked
  Then exactly one HTTP 400 error is returned for the request
  And a structured warning log is emitted with event_name severity platform_tenant_id and failure_reason
  And the log does not include service_tenant_id or service_user_id
