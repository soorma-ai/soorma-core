Feature: Identity core domain behavior

@happy-path @TC-UICD-001
Scenario: Onboard tenant identity domain
  Given a valid onboarding request
  When onboarding workflow executes
  Then tenant domain and bootstrap admin are created atomically
  # Source: uow-identity-core-domain / FR-1
  # Construction: aidlc-docs/platform/identity-service/construction/uow-identity-core-domain/

@happy-path @TC-UICD-002
Scenario: Issue token with mandatory claim contract
  Given an active eligible principal
  When token issuance is requested
  Then token contains all mandatory identity claims including jti and platform principal context
  # Source: uow-identity-core-domain / FR-6
  # Construction: aidlc-docs/platform/identity-service/construction/uow-identity-core-domain/

@happy-path-negative @TC-UICD-003
Scenario: Reject unregistered delegated issuer assertion
  Given a delegated assertion with unregistered issuer
  When trust validation is executed
  Then access is denied fail-closed with a typed safe error response and audited
  # Source: uow-identity-core-domain / FR-5
  # Construction: aidlc-docs/platform/identity-service/construction/uow-identity-core-domain/

@happy-path-negative @TC-UICD-004
Scenario: Reject mapping collision without explicit override
  Given a delegated assertion that collides with an existing verified binding
  When collision policy evaluation is executed without admin override
  Then collision is rejected by default and remap is denied
  # Source: uow-identity-core-domain / FR-9
  # Construction: aidlc-docs/platform/identity-service/construction/uow-identity-core-domain/code/