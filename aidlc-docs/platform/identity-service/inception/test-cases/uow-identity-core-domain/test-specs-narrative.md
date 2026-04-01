# Test Specs Narrative - uow-identity-core-domain

### TC-UICD-001 - Tenant onboarding creates identity domain
Context: Validates onboarding flow and bootstrap behavior.
Scenario: Platform admin submits valid onboarding request.
Steps: 1) Submit onboarding payload 2) Execute onboarding workflow 3) Query tenant domain record
Expected: Tenant domain created and bootstrap admin persisted.
Scope: happy-path
Priority: High
Source: uow-identity-core-domain / FR-1
Construction artifacts: aidlc-docs/platform/identity-service/construction/uow-identity-core-domain/
Technical references: services identity domain APIs

### TC-UICD-002 - Token issuance returns mandatory claims
Context: Validates FR-7 claim contract in identity core.
Scenario: Active principal requests token.
Steps: 1) Create eligible principal 2) Request token 3) Decode claims
Expected: Mandatory claims present and correctly populated.
Scope: happy-path
Priority: High
Source: uow-identity-core-domain / FR-6
Construction artifacts: aidlc-docs/platform/identity-service/construction/uow-identity-core-domain/
Technical references: token issuance component

### TC-UICD-003 - Unregistered delegated issuer denied
Context: Negative path for delegated trust handling.
Scenario: Delegated assertion from unregistered issuer.
Steps: 1) Submit delegated assertion with unknown issuer 2) Execute trust validation
Expected: Assertion rejected; access denied and audit event emitted.
Scope: negative
Priority: High
Source: uow-identity-core-domain / FR-5
Construction artifacts: aidlc-docs/platform/identity-service/construction/uow-identity-core-domain/
Technical references: delegated trust component