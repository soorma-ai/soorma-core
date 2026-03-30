Feature: Unit-2 memory runtime alignment and identity-scope enforcement

@happy-path @TC-U2-001
Scenario: Enforce require_user_context on user-scoped routers
  # Source: unit-2 / FR-3
  # Construction: aidlc-docs/platform/memory-identity-scope/construction/unit-2/
  Given a user-scoped memory router has require_user_context attached
  When a request is sent with missing service tenant or service user identity
  Then the router returns HTTP 400
  And handler business logic is not executed

@negative @TC-U2-002
Scenario: Keep admin endpoints exempt from user-context dependency
  # Source: unit-2 / NFR-2
  # Construction: aidlc-docs/platform/memory-identity-scope/construction/unit-2/
  Given an admin endpoint without require_user_context
  When called without service_user_id
  Then no dependency-driven HTTP 400 is raised
  And endpoint-level admin authorization guard is enforced

@negative @TC-U2-003
Scenario: Enforce full identity tuple in plans and sessions CRUD
  # Source: unit-2 / FR-4
  # Construction: aidlc-docs/platform/memory-identity-scope/construction/unit-2/
  Given records owned by identity A
  When identity B tries list get update or delete on those records
  Then the operation does not expose or mutate identity A data

@negative @TC-U2-004
Scenario: Align upsert conflict targets to scoped identity
  # Source: unit-2 / FR-6
  # Construction: aidlc-docs/platform/memory-identity-scope/construction/unit-2/
  Given an existing upsert record for identity A
  When identity B upserts with matching business key fields
  Then no cross-identity overwrite occurs

@negative @TC-U2-005
Scenario: Enforce service-layer fail-closed identity backstop
  # Source: unit-2 / NFR-4
  # Construction: aidlc-docs/platform/memory-identity-scope/construction/unit-2/code/
  Given an internal service invocation path that bypasses route-level guard
  When the service receives a missing identity dimension
  Then the service raises a validation exception before CRUD execution
  And a warning log event includes platform_tenant_id only
