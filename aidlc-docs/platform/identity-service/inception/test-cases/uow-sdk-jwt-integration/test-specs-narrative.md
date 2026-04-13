# Test Specs Narrative - uow-sdk-jwt-integration

### TC-USJI-001 - Wrapper calls remain signature-compatible with internal JWT injection
Context: Ensures wrapper APIs remain stable while JWT transport/auth behavior is injected internally per Unit 3 compatibility design.
Scenario: Existing handler code uses wrapper methods after SDK JWT integration changes.
Steps: 1) Invoke existing wrapper call pattern from unchanged handler code 2) Execute request path 3) Inspect wrapper/client contract usage
Expected: No handler signature changes are required, and JWT behavior is applied inside wrapper/client internals.
Scope: happy-path
Priority: High
Source: uow-sdk-jwt-integration / FR-12
Construction artifacts: aidlc-docs/platform/identity-service/construction/uow-sdk-jwt-integration/
Technical references: construction/uow-sdk-jwt-integration/functional-design/business-rules.md (BR-05, BR-06)

### TC-USJI-002 - SDK sends canonical JWT-authenticated outbound request
Context: Validates canonical JWT-first outbound behavior and compatibility-phase verifier acceptance.
Scenario: SDK request executes with valid JWT claims and configured verifier distribution policy.
Steps: 1) Configure valid JWT context in SDK 2) Execute wrapper/client request 3) Validate outbound auth and service-side acceptance path
Expected: Outbound request carries JWT as canonical identity source and is accepted via deterministic verifier resolution policy.
Scope: happy-path
Priority: High
Source: uow-sdk-jwt-integration / FR-11
Construction artifacts: aidlc-docs/platform/identity-service/construction/uow-sdk-jwt-integration/
Technical references: construction/uow-sdk-jwt-integration/functional-design/business-logic-model.md (BLM-2), construction/uow-sdk-jwt-integration/nfr-design/nfr-design-patterns.md (ND-1)

### TC-USJI-003 - Invalid JWT is denied fail-closed with typed safe error
Context: Negative path for wrapper/client JWT verification failures where fallback must not silently bypass invalid JWT.
Scenario: SDK sends expired, invalid-signature, or otherwise invalid JWT.
Steps: 1) Configure invalid JWT 2) Execute wrapper/client request 3) Inspect denial and returned error contract
Expected: Request is denied fail-closed with typed safe error behavior and no permissive fallback that weakens trust boundary.
Scope: happy-path-negative
Priority: High
Source: uow-sdk-jwt-integration / NFR-8
Construction artifacts: aidlc-docs/platform/identity-service/construction/uow-sdk-jwt-integration/
Technical references: construction/uow-sdk-jwt-integration/functional-design/business-rules.md (BR-17, BR-18), construction/uow-sdk-jwt-integration/nfr-design/nfr-design-patterns.md (ND-1)

### TC-USJI-004 - JWT plus matching compatibility alias succeeds
Context: Validates bounded compatibility behavior while legacy alias paths remain temporarily supported.
Scenario: SDK request includes JWT and optional legacy alias tenant value that matches canonical JWT tenant.
Steps: 1) Configure valid JWT and matching alias tenant 2) Execute request 3) Observe authorization result
Expected: Request succeeds on compatibility path because alias tenant matches canonical JWT tenant identity.
Scope: happy-path
Priority: High
Source: uow-sdk-jwt-integration / FR-11
Construction artifacts: aidlc-docs/platform/identity-service/construction/uow-sdk-jwt-integration/code/
Technical references: construction/uow-sdk-jwt-integration/functional-design/business-logic-model.md (BLM-3), construction/uow-sdk-jwt-integration/functional-design/business-rules.md (BR-03)

### TC-USJI-005 - JWT plus mismatching alias tenant is denied
Context: Validates defensive alias mismatch guardrail to prevent tenant-identity ambiguity.
Scenario: SDK request includes valid JWT but alias tenant differs from canonical JWT tenant.
Steps: 1) Configure valid JWT and mismatching alias tenant 2) Execute request 3) Observe decision and audit signal
Expected: Request is denied fail-closed due to tenant mismatch and structured denial telemetry/audit signal is emitted.
Scope: happy-path-negative
Priority: High
Source: uow-sdk-jwt-integration / FR-11
Construction artifacts: aidlc-docs/platform/identity-service/construction/uow-sdk-jwt-integration/code/
Technical references: construction/uow-sdk-jwt-integration/functional-design/business-logic-model.md (BLM-3), construction/uow-sdk-jwt-integration/functional-design/business-rules.md (BR-04)

### TC-USJI-006 - Unknown kid or invalid signature is denied under verifier policy
Context: Validates compatibility-phase verifier hardening for asymmetric/JWKS distribution behavior.
Scenario: Consumer receives token with unknown kid or invalid signature material.
Steps: 1) Execute verification with unknown kid token 2) Execute verification with invalid signature token 3) Evaluate outcomes
Expected: Both paths are denied fail-closed according to deterministic verifier precedence and trust resolution rules.
Scope: happy-path-negative
Priority: High
Source: uow-sdk-jwt-integration / NFR-9
Construction artifacts: aidlc-docs/platform/identity-service/construction/uow-sdk-jwt-integration/code/
Technical references: construction/uow-sdk-jwt-integration/nfr-design/nfr-design-patterns.md (ND-1, ND-7), construction/plans/uow-sdk-jwt-integration-migration-checklist.md

### TC-USJI-007 - soorma dev bootstrap returns deterministic outcomes and blocks protected drift
Context: Validates idempotent local bootstrap contract and fail-closed drift protection.
Scenario: `soorma dev` bootstrap is executed repeatedly across create, reuse, and protected-drift conditions.
Steps: 1) Run bootstrap on missing state 2) Run bootstrap on matching existing state 3) Run bootstrap with protected drift
Expected: Outcomes are deterministic (`CREATED`, `REUSED`, `FAILED_DRIFT`) and protected drift path fails closed without silent overwrite.
Scope: happy-path-negative
Priority: High
Source: uow-sdk-jwt-integration / FR-12
Construction artifacts: aidlc-docs/platform/identity-service/construction/uow-sdk-jwt-integration/code/
Technical references: construction/uow-sdk-jwt-integration/functional-design/business-logic-model.md (BLM-5), construction/uow-sdk-jwt-integration/functional-design/business-rules.md (BR-13, BR-14, BR-15)