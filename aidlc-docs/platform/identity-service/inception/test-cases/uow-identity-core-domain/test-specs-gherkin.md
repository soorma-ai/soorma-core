Feature: Identity core domain behavior

@happy-path @TC-UICD-001
Scenario: Onboard tenant identity domain
  Given a valid onboarding request
  When onboarding workflow executes
  Then tenant domain and bootstrap admin are created
  # Source: uow-identity-core-domain / FR-1
  # Construction: aidlc-docs/platform/identity-service/construction/uow-identity-core-domain/

@happy-path @TC-UICD-002
Scenario: Issue token with mandatory claim contract
  Given an active eligible principal
  When token issuance is requested
  Then token contains all mandatory claims
  # Source: uow-identity-core-domain / FR-6
  # Construction: aidlc-docs/platform/identity-service/construction/uow-identity-core-domain/

@happy-path-negative @TC-UICD-003
Scenario: Reject unregistered delegated issuer assertion
  Given a delegated assertion with unregistered issuer
  When trust validation is executed
  Then access is denied and audited
  # Source: uow-identity-core-domain / FR-5
  # Construction: aidlc-docs/platform/identity-service/construction/uow-identity-core-domain/