# Test Specs Narrative - uow-shared-auth-foundation

### TC-USAF-001 - JWT context resolved from authenticated request
Context: Validates authoritative JWT path, issuer pinning checks, and downstream context propagation.
Scenario: Service ingress request contains valid JWT and route policy.
Steps:
1. Send request with valid JWT claims.
2. Invoke shared dependency auth context resolver.
3. Observe resolved auth context in request state.
Expected: JWT-derived context is accepted, provenance is recorded, and canonical tuple context is available downstream.
Scope: happy-path
Priority: High
Source: uow-shared-auth-foundation / FR-11
Construction artifacts: aidlc-docs/platform/identity-service/construction/uow-shared-auth-foundation/
Technical references: libs/soorma-service-common; construction/uow-shared-auth-foundation/functional-design/business-rules.md; construction/uow-shared-auth-foundation/nfr-design/nfr-design-patterns.md

### TC-USAF-002 - Legacy header-only request denied under compatibility override
Context: Enforces approved NFR-8 compatibility override for this unit (no header-compat fallback path).
Scenario: Request uses legacy header context without JWT.
Steps:
1. Send request with legacy headers only.
2. Invoke shared dependency auth context resolver.
3. Observe auth decision and response envelope.
Expected: Request is denied fail-closed; no compatibility translation path is used.
Scope: negative
Priority: High
Source: uow-shared-auth-foundation / NFR-8 override (FR-11 compatibility decision)
Construction artifacts: aidlc-docs/platform/identity-service/construction/uow-shared-auth-foundation/
Technical references: libs/soorma-service-common; construction/uow-shared-auth-foundation/nfr-requirements/nfr-requirements.md; construction/uow-shared-auth-foundation/functional-design/business-rules.md

### TC-USAF-003 - Missing auth context fails closed
Context: Negative path for SECURITY-08 and SECURITY-15.
Scenario: Request missing JWT and missing legacy headers.
Steps:
1. Send unauthenticated request.
2. Run auth context dependency.
Expected: Access denied with 401 safe error; no downstream handler execution.
Scope: negative
Priority: High
Source: uow-shared-auth-foundation / NFR-2
Construction artifacts: aidlc-docs/platform/identity-service/construction/uow-shared-auth-foundation/
Technical references: libs/soorma-service-common; construction/uow-shared-auth-foundation/functional-design/business-rules.md; construction/uow-shared-auth-foundation/nfr-design/nfr-design-patterns.md