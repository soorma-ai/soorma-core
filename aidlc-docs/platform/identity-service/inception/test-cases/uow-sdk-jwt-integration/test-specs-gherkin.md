Feature: SDK JWT integration

@happy-path @TC-USJI-001
Scenario: Existing wrapper signatures remain stable
  Given existing wrapper call patterns
  When SDK JWT integration is enabled
  Then handler call signatures remain unchanged
  # Source: uow-sdk-jwt-integration / FR-12
  # Construction: aidlc-docs/platform/identity-service/construction/uow-sdk-jwt-integration/

@happy-path @TC-USJI-002
Scenario: SDK transmits JWT-authenticated requests
  Given JWT context configured in SDK
  When wrapper/client request executes
  Then outbound request includes valid JWT auth
  # Source: uow-sdk-jwt-integration / FR-11
  # Construction: aidlc-docs/platform/identity-service/construction/uow-sdk-jwt-integration/

@happy-path-negative @TC-USJI-003
Scenario: Wrapper flow rejects invalid JWT
  Given SDK is configured with invalid JWT
  When request executes
  Then access is denied with safe failure response
  # Source: uow-sdk-jwt-integration / NFR-2
  # Construction: aidlc-docs/platform/identity-service/construction/uow-sdk-jwt-integration/