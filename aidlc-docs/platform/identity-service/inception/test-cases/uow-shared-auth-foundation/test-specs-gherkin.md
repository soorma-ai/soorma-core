Feature: Shared auth context coexistence

@happy-path @TC-USAF-001
Scenario: Resolve JWT auth context
  Given a request with valid JWT claims
  When auth context dependency resolves request identity
  Then JWT context is set for downstream processing
  # Source: uow-shared-auth-foundation / FR-11
  # Construction: aidlc-docs/platform/identity-service/construction/uow-shared-auth-foundation/

@happy-path @TC-USAF-002
Scenario: Translate legacy context in coexistence mode
  Given coexistence mode is enabled
  And a request has legacy headers only
  When compatibility adapter runs
  Then a valid internal auth context is produced
  # Source: uow-shared-auth-foundation / FR-11
  # Construction: aidlc-docs/platform/identity-service/construction/uow-shared-auth-foundation/

@happy-path-negative @TC-USAF-003
Scenario: Deny request without auth context
  Given a request has no JWT and no legacy headers
  When auth dependency validates context
  Then access is denied with a safe error response
  # Source: uow-shared-auth-foundation / NFR-2
  # Construction: aidlc-docs/platform/identity-service/construction/uow-shared-auth-foundation/