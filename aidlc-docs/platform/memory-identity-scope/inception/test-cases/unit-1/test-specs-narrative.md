# Unit Test Specs Narrative - unit-1

Unit abbreviation: U1 = unit-1
Scope profile: happy-path-negative

### TC-U1-001 - Validate and pass through full user identity context
Context: Validates FR-2 core contract that shared dependency accepts requests only when both service tenant and service user are present and returns control for downstream handlers.
Scenario: A user-scoped endpoint request arrives with valid platform tenant, service tenant, and service user in resolved context.
Preconditions:
1. Request context is resolved successfully.
2. `service_tenant_id` is non-empty.
3. `service_user_id` is non-empty.
Steps:
1. Invoke dependency `require_user_context` with resolved context.
2. Observe dependency return value.
Expected outcome: Dependency returns the same context object and does not raise an exception.
Scope: happy-path
Priority: High
Source: unit-1 / FR-2
Construction artifacts: aidlc-docs/platform/memory-identity-scope/construction/unit-1/
Technical references:
- aidlc-docs/platform/memory-identity-scope/inception/requirements/requirements.md
- aidlc-docs/platform/memory-identity-scope/inception/application-design/unit-of-work.md

### TC-U1-002 - Reject missing service tenant context
Context: Validates FR-2 negative path and acceptance criterion coverage for missing service-tenant identity.
Scenario: Request context resolves but `service_tenant_id` is missing while user value may exist.
Preconditions:
1. Request context is resolved.
2. `service_tenant_id` is null/empty.
Steps:
1. Invoke dependency `require_user_context`.
2. Capture raised exception.
Expected outcome: Dependency raises HTTP 400 with generic transport-agnostic error detail.
Scope: negative
Priority: High
Source: unit-1 / FR-2
Construction artifacts: aidlc-docs/platform/memory-identity-scope/construction/unit-1/
Technical references:
- aidlc-docs/platform/memory-identity-scope/inception/requirements/requirements.md
- aidlc-docs/platform/memory-identity-scope/construction/unit-1/nfr-design/nfr-design-patterns.md

### TC-U1-003 - Reject missing service user context
Context: Validates FR-2 and acceptance criterion coverage for missing service-user identity in user-scoped operation paths.
Scenario: Request context resolves but `service_user_id` is missing while service tenant exists.
Preconditions:
1. Request context is resolved.
2. `service_tenant_id` is present.
3. `service_user_id` is null/empty.
Steps:
1. Invoke dependency `require_user_context`.
2. Capture raised exception.
Expected outcome: Dependency raises HTTP 400 with generic transport-agnostic error detail.
Scope: negative
Priority: High
Source: unit-1 / FR-2
Construction artifacts: aidlc-docs/platform/memory-identity-scope/construction/unit-1/
Technical references:
- aidlc-docs/platform/memory-identity-scope/inception/requirements/requirements.md
- aidlc-docs/platform/memory-identity-scope/construction/unit-1/nfr-design/nfr-design-patterns.md

### TC-U1-004 - Reject empty or whitespace identity values
Context: Ensures robust validation behavior for malformed identity inputs and supports NFR-1 generic validation contract.
Scenario: Request contains empty-string or whitespace-only service tenant or user identity values.
Preconditions:
1. Request context resolves.
2. At least one identity dimension is empty or whitespace-only.
Steps:
1. Invoke dependency with empty-string service tenant.
2. Invoke dependency with whitespace-only service user.
3. Observe response behavior for both invocations.
Expected outcome: Each invalid invocation raises HTTP 400 with generic detail and no transport/header internals.
Scope: negative
Priority: Medium
Source: unit-1 / NFR-1
Construction artifacts: aidlc-docs/platform/memory-identity-scope/construction/unit-1/
Technical references:
- aidlc-docs/platform/memory-identity-scope/inception/requirements/requirements.md
- aidlc-docs/platform/memory-identity-scope/construction/unit-1/nfr-design/nfr-design-patterns.md

### TC-U1-005 - Aggregate identity failures and emit structured safe warning log
Context: Adds NFR-design-driven coverage for aggregated fail-closed response behavior and structured logging field policy.
Scenario: Request context is missing both required user-scope dimensions.
Preconditions:
1. Request context resolves and has `platform_tenant_id`.
2. `service_tenant_id` and `service_user_id` are both missing or invalid.
3. Structured warning logging is enabled for validation failure events.
Steps:
1. Invoke dependency `require_user_context` with both dimensions missing.
2. Capture HTTP error and inspect response count.
3. Inspect warning log event fields emitted for the failure.
Expected outcome: Exactly one HTTP 400 response is returned for the request; structured warning includes `event_name`, `severity`, `platform_tenant_id`, and failure reason, and excludes `service_tenant_id` and `service_user_id`.
Scope: negative
Priority: High
Source: unit-1 / NFR-1
Construction artifacts: aidlc-docs/platform/memory-identity-scope/construction/unit-1/code/
Technical references:
- aidlc-docs/platform/memory-identity-scope/construction/unit-1/nfr-design/nfr-design-patterns.md
- aidlc-docs/platform/memory-identity-scope/construction/unit-1/nfr-design/logical-components.md
