# Test Specs Narrative - uow-identity-core-domain

### TC-UICD-001 - Tenant onboarding creates identity domain
Context: Validates onboarding flow and bootstrap behavior, including the approved atomic onboarding boundary.
Scenario: Platform admin submits valid onboarding request for a new tenant domain.
Steps: 1) Submit onboarding payload 2) Execute onboarding workflow 3) Query tenant domain and bootstrap principal state
Expected: Tenant domain and bootstrap admin are created in one atomic operation.
Scope: happy-path
Priority: High
Source: uow-identity-core-domain / FR-1
Construction artifacts: aidlc-docs/platform/identity-service/construction/uow-identity-core-domain/
Technical references: construction/uow-identity-core-domain/functional-design/business-logic-model.md (BLM-1), construction/uow-identity-core-domain/functional-design/business-rules.md (BR-02)

### TC-UICD-002 - Token issuance returns mandatory claims
Context: Validates mandatory claim contract and policy-gated issuance behavior for active principals.
Scenario: Active principal requests token.
Steps: 1) Create eligible principal 2) Request token 3) Decode claims
Expected: Mandatory claims (`iss`, `sub`, `aud`, `exp`, `iat`, `jti`, `platform_tenant_id`, `principal_id`, `principal_type`, `roles`) are present and correctly populated.
Scope: happy-path
Priority: High
Source: uow-identity-core-domain / FR-6
Construction artifacts: aidlc-docs/platform/identity-service/construction/uow-identity-core-domain/
Technical references: construction/uow-identity-core-domain/functional-design/business-rules.md (BR-10, BR-11), construction/uow-identity-core-domain/nfr-design/logical-components.md (LC-1)

### TC-UICD-003 - Unregistered delegated issuer denied
Context: Negative path for delegated trust handling with fail-closed behavior and safe error envelope requirements.
Scenario: Delegated assertion from unregistered issuer.
Steps: 1) Submit delegated assertion with unknown issuer 2) Execute trust validation
Expected: Assertion rejected fail-closed, access denied with typed safe error envelope, and audit event emitted.
Scope: happy-path-negative
Priority: High
Source: uow-identity-core-domain / FR-5
Construction artifacts: aidlc-docs/platform/identity-service/construction/uow-identity-core-domain/
Technical references: construction/uow-identity-core-domain/functional-design/business-rules.md (BR-17, BR-18), construction/uow-identity-core-domain/nfr-design/nfr-design-patterns.md (ND-1)

### TC-UICD-004 - Mapping collision defaults to reject and requires explicit override for remap
Context: Validates collision-governance safety controls in external identity mapping.
Scenario: A delegated assertion resolves to a canonical key that conflicts with an existing verified binding.
Steps: 1) Submit delegated assertion causing mapping collision 2) Execute collision policy evaluation 3) Attempt remap without admin override
Expected: Collision is rejected by default and remap is denied until an explicit admin override workflow is applied.
Scope: happy-path-negative
Priority: High
Source: uow-identity-core-domain / FR-9
Construction artifacts: aidlc-docs/platform/identity-service/construction/uow-identity-core-domain/code/
Technical references: construction/uow-identity-core-domain/functional-design/business-rules.md (BR-13, BR-16), construction/uow-identity-core-domain/nfr-design/logical-components.md (LC-5, LC-6)