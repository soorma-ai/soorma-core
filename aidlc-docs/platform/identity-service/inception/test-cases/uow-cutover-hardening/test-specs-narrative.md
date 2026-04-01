# Test Specs Narrative - uow-cutover-hardening

### TC-UCH-001 - JWT-only ingress after cutover
Context: Validates final phase behavior after legacy path removal.
Scenario: Request uses valid JWT post-cutover.
Steps: 1) Enable cutover mode 2) Send JWT-authenticated request
Expected: Request succeeds with JWT-only path.
Scope: happy-path
Priority: High
Source: uow-cutover-hardening / FR-11
Construction artifacts: aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/
Technical references: ingress auth dependencies

### TC-UCH-002 - Header-only request denied post-cutover
Context: Ensures legacy auth path is removed.
Scenario: Request provides legacy headers without JWT.
Steps: 1) Enable cutover mode 2) Send header-only request
Expected: Access denied with safe, non-leaking error.
Scope: negative
Priority: High
Source: uow-cutover-hardening / FR-11
Construction artifacts: aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/
Technical references: compatibility removal logic

### TC-UCH-003 - Security telemetry emitted for denied legacy access
Context: Validates observability and security baseline alignment.
Scenario: Denied header-only request in JWT-only mode.
Steps: 1) Trigger denied request 2) Check audit/security telemetry stream
Expected: Structured denial event with tenant/correlation context emitted.
Scope: negative
Priority: Medium
Source: uow-cutover-hardening / FR-13
Construction artifacts: aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/
Technical references: audit telemetry component