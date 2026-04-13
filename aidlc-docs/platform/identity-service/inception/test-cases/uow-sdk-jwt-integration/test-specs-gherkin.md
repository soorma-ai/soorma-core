Feature: SDK JWT integration

@happy-path @TC-USJI-001
Scenario: Existing wrapper signatures remain stable with internal JWT behavior
  Given existing handler code uses current wrapper call signatures
  When SDK JWT integration is enabled
  Then handler call signatures remain unchanged and JWT behavior is injected internally
  # Source: uow-sdk-jwt-integration / FR-12
  # Construction: aidlc-docs/platform/identity-service/construction/uow-sdk-jwt-integration/

@happy-path @TC-USJI-002
Scenario: SDK transmits canonical JWT-authenticated request
  Given valid JWT context is configured in SDK
  When wrapper/client request executes
  Then outbound request uses JWT canonical identity and is accepted by verifier policy
  # Source: uow-sdk-jwt-integration / FR-11
  # Construction: aidlc-docs/platform/identity-service/construction/uow-sdk-jwt-integration/

@happy-path-negative @TC-USJI-003
Scenario: Invalid JWT is rejected fail-closed with typed safe error
  Given SDK request is configured with invalid JWT material
  When request executes
  Then access is denied fail-closed and response uses safe typed error semantics
  # Source: uow-sdk-jwt-integration / NFR-8
  # Construction: aidlc-docs/platform/identity-service/construction/uow-sdk-jwt-integration/

@happy-path @TC-USJI-004
Scenario: Matching compatibility alias with JWT succeeds
  Given request contains valid JWT and matching alias tenant value
  When request executes
  Then compatibility path succeeds
  # Source: uow-sdk-jwt-integration / FR-11
  # Construction: aidlc-docs/platform/identity-service/construction/uow-sdk-jwt-integration/code/

@happy-path-negative @TC-USJI-005
Scenario: Mismatching alias tenant is denied
  Given request contains valid JWT and mismatching alias tenant value
  When request executes
  Then request is denied fail-closed with mismatch decision telemetry
  # Source: uow-sdk-jwt-integration / FR-11
  # Construction: aidlc-docs/platform/identity-service/construction/uow-sdk-jwt-integration/code/

@happy-path-negative @TC-USJI-006
Scenario: Unknown kid or invalid signature is denied
  Given verifier receives token with unknown kid or invalid signature
  When verification executes
  Then access is denied fail-closed under deterministic verifier precedence
  # Source: uow-sdk-jwt-integration / NFR-9
  # Construction: aidlc-docs/platform/identity-service/construction/uow-sdk-jwt-integration/code/

@happy-path-negative @TC-USJI-007
Scenario: soorma dev bootstrap reports deterministic outcomes and blocks protected drift
  Given bootstrap is executed across create, reuse, and protected-drift conditions
  When command outcomes are evaluated
  Then outcomes are CREATED, REUSED, FAILED_DRIFT and protected drift fails closed
  # Source: uow-sdk-jwt-integration / FR-12
  # Construction: aidlc-docs/platform/identity-service/construction/uow-sdk-jwt-integration/code/