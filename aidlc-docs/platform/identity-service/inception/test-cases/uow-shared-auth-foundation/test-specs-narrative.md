# Test Specs Narrative - uow-shared-auth-foundation

### TC-USAF-001 - JWT context resolved from authenticated request
Context: Validates FR-11 phase-1 coexistence with JWT as preferred auth source.
Scenario: Service ingress request contains valid JWT and route policy.
Steps:
1. Send request with valid JWT claims.
2. Invoke shared dependency auth context resolver.
3. Observe resolved auth context in request state.
Expected: JWT-derived context is accepted and available downstream.
Scope: happy-path
Priority: High
Source: uow-shared-auth-foundation / FR-11
Construction artifacts: aidlc-docs/platform/identity-service/construction/uow-shared-auth-foundation/
Technical references: libs/soorma-service-common

### TC-USAF-002 - Legacy context translated during coexistence
Context: Ensures existing DI/router call sites remain non-breaking in coexistence.
Scenario: Request uses legacy header context while coexistence enabled.
Steps:
1. Send request with legacy headers only.
2. Invoke compatibility adapter.
3. Observe translated auth context.
Expected: Request remains functional without route-level contract changes.
Scope: happy-path
Priority: High
Source: uow-shared-auth-foundation / FR-11
Construction artifacts: aidlc-docs/platform/identity-service/construction/uow-shared-auth-foundation/
Technical references: libs/soorma-service-common

### TC-USAF-003 - Missing auth context fails closed
Context: Negative path for SECURITY-08 and SECURITY-15.
Scenario: Request missing JWT and missing legacy headers.
Steps:
1. Send unauthenticated request.
2. Run auth context dependency.
Expected: Access denied with safe error; no downstream handler execution.
Scope: negative
Priority: High
Source: uow-shared-auth-foundation / NFR-2
Construction artifacts: aidlc-docs/platform/identity-service/construction/uow-shared-auth-foundation/
Technical references: libs/soorma-service-common