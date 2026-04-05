Feature: Shared auth context coexistence

@happy-path @TC-USAF-001
Scenario: Resolve JWT auth context
  Given a request with valid JWT claims
  When auth context dependency resolves request identity
  Then JWT context and provenance metadata are set for downstream processing
  # Source: uow-shared-auth-foundation / FR-11
  # Construction: aidlc-docs/platform/identity-service/construction/uow-shared-auth-foundation/
  # Technical refs: business-rules.md, nfr-design-patterns.md

@happy-path @TC-USAF-002
Scenario: Accept legacy header-only request during FR-11 coexistence
  Given FR-11 phase 1 or phase 2 coexistence mode is active
  And a request has legacy headers only
  When auth dependency validates context
  Then header-derived canonical context is accepted and propagated
  # Source: uow-shared-auth-foundation / FR-11 compatibility constraint
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