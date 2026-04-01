# Test Specs Narrative - uow-sdk-jwt-integration

### TC-USJI-001 - Wrapper calls remain signature-compatible
Context: Ensures no agent handler signature churn in SDK migration.
Scenario: Existing wrapper calls executed with upgraded SDK.
Steps: 1) Use existing wrapper invocation 2) Execute request path
Expected: No signature changes required at handler call sites.
Scope: happy-path
Priority: High
Source: uow-sdk-jwt-integration / FR-12
Construction artifacts: aidlc-docs/platform/identity-service/construction/uow-sdk-jwt-integration/
Technical references: sdk/python/soorma wrappers

### TC-USJI-002 - SDK sends JWT auth on outbound calls
Context: Validates rollout phase-2 behavior.
Scenario: JWT configured in SDK environment.
Steps: 1) Configure JWT context 2) Execute SDK call 3) Inspect outbound auth material
Expected: JWT auth is sent and accepted by service ingress.
Scope: happy-path
Priority: High
Source: uow-sdk-jwt-integration / FR-11
Construction artifacts: aidlc-docs/platform/identity-service/construction/uow-sdk-jwt-integration/
Technical references: SDK client transport

### TC-USJI-003 - Invalid JWT rejected through wrapper flow
Context: Negative path for wrapper-driven auth failure.
Scenario: SDK request uses expired or invalid JWT.
Steps: 1) Configure invalid JWT 2) Execute SDK call
Expected: Request denied fail-closed with safe error propagation.
Scope: negative
Priority: High
Source: uow-sdk-jwt-integration / NFR-2
Construction artifacts: aidlc-docs/platform/identity-service/construction/uow-sdk-jwt-integration/
Technical references: SDK error mapping