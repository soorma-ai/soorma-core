Feature: Shared auth context coexistence

@happy-path @TC-USAF-001
Scenario: Resolve JWT auth context
  Given a request with valid JWT claims
  When auth context dependency resolves request identity
  Then JWT context and provenance metadata are set for downstream processing
  # Source: uow-shared-auth-foundation / FR-11
  # Construction: aidlc-docs/platform/identity-service/construction/uow-shared-auth-foundation/
  # Technical refs: business-rules.md, nfr-design-patterns.md

@happy-path-negative @TC-USAF-002
Scenario: Deny legacy header-only request under compatibility override
  Given compatibility override is approved for this unit
  And a request has legacy headers only
  When auth dependency validates context
  Then access is denied with no header-compat fallback
  # Source: uow-shared-auth-foundation / NFR-8 override (FR-11 compatibility decision)
  # Construction: aidlc-docs/platform/identity-service/construction/uow-shared-auth-foundation/
  # Technical refs: nfr-requirements.md, business-rules.md

@happy-path-negative @TC-USAF-003
Scenario: Deny request without auth context
  Given a request has no JWT and no legacy headers
  When auth dependency validates context
  Then access is denied with a 401 safe error response
  # Source: uow-shared-auth-foundation / NFR-2
  # Construction: aidlc-docs/platform/identity-service/construction/uow-shared-auth-foundation/
  # Technical refs: business-rules.md, nfr-design-patterns.md