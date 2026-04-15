Feature: JWT-only cutover hardening

@happy-path @TC-UCH-001
Scenario: JWT-authenticated request succeeds after release cutover
  Given the cutover release is deployed
  And the request includes a valid JWT
  When ingress auth validation executes for a secured non-public endpoint
  Then the request proceeds on the JWT-only path without legacy-header fallback
  # Source: uow-cutover-hardening / FR-11
  # Construction: aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/

@happy-path-negative @TC-UCH-002
Scenario: Header-only request is denied after cutover
  Given the cutover release is deployed
  And the request includes no JWT and only legacy auth headers
  When ingress auth validation executes
  Then access is denied fail-closed with a safe non-leaking error
  # Source: uow-cutover-hardening / FR-11
  # Construction: aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/

@happy-path-negative @TC-UCH-003
Scenario: Denied legacy access emits structured telemetry
  Given a header-only request is denied after cutover
  When denial handling completes
  Then structured centralized security telemetry is emitted with deny reason and correlation context
  # Source: uow-cutover-hardening / FR-13
  # Construction: aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/

@happy-path @TC-UCH-004
Scenario: Trusted caller self-issue succeeds with canonical tenant contract
  Given an approved trusted caller is authenticated
  And the issuance request targets the caller itself using canonical tenant_id
  When issuance authorization executes
  Then token issuance succeeds on the trusted-caller path
  # Source: uow-cutover-hardening / FR-11
  # Construction: aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/code/

@happy-path-negative @TC-UCH-005
Scenario: Issue-for-other without override authority is denied
  Given a trusted caller is authenticated without override authority
  And the caller requests a token for a different principal
  When issuance authorization executes
  Then the request is denied fail-closed regardless of payload override hints
  # Source: uow-cutover-hardening / FR-11
  # Construction: aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/code/

@happy-path-negative @TC-UCH-006
Scenario: Legacy tenant alias field is rejected
  Given a request uses platform_tenant_id or tenant_domain_id on an active cutover path
  When request validation executes
  Then the request is rejected because only canonical tenant_id is accepted
  # Source: uow-cutover-hardening / FR-11
  # Construction: aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/code/

@happy-path-negative @TC-UCH-007
Scenario: Unknown kid or invalid signature is denied
  Given a JWT contains an unknown kid or invalid signature
  When verifier resolution and signature validation execute
  Then the request is denied fail-closed without permissive fallback
  # Source: uow-cutover-hardening / FR-11
  # Construction: aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/code/

@happy-path-negative @TC-UCH-008
Scenario: Unallowlisted delegated issuer is denied before trust retrieval
  Given delegated token validation references an issuer outside the approved allowlist
  When delegated issuer trust evaluation executes
  Then validation is denied and runtime trust retrieval is not permitted for that issuer
  # Source: uow-cutover-hardening / FR-11
  # Construction: aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/code/

@happy-path-negative @TC-UCH-009
Scenario: Unknown kid denial emits alert-ready centralized signal
  Given a secured request fails with an unknown kid verifier denial
  When telemetry and alert signal processing complete
  Then centralized observability receives structured verifier-failure signal data
  # Source: uow-cutover-hardening / FR-13
  # Construction: aidlc-docs/platform/identity-service/construction/uow-cutover-hardening/code/