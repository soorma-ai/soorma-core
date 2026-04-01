Feature: JWT-only cutover hardening

@happy-path @TC-UCH-001
Scenario: JWT-authenticated request succeeds after cutover
  Given cutover mode is enabled
  And request includes valid JWT
  When ingress auth validation executes
  Then request proceeds on JWT-only path
  # Source: uow-cutover-hardening / FR-11
  # Construction: aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/

@happy-path-negative @TC-UCH-002
Scenario: Header-only request denied after cutover
  Given cutover mode is enabled
  And request includes no JWT
  When ingress auth validation executes
  Then access is denied with safe error
  # Source: uow-cutover-hardening / FR-11
  # Construction: aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/

@happy-path-negative @TC-UCH-003
Scenario: Denied legacy access is audited
  Given a header-only request is denied in cutover mode
  When denial handling completes
  Then structured security telemetry is emitted
  # Source: uow-cutover-hardening / FR-13
  # Construction: aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/