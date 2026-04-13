# Code Generation Summary - uow-sdk-jwt-integration

## Scope
Implemented Unit 3 code-generation changes for SDK, identity-service, and shared dependencies with fail-closed behavior and deterministic local bootstrap outcome tracking.

## Architecture Alignment
- Section 1 (Authentication): strengthened JWT claim-shape validation and typed deny envelopes.
- Section 2 (Two-layer SDK): wrapper signature remained unchanged; hardening was implemented inside wrapper internals.
- Section 6 (Error handling): standardized typed safe API envelope for platform-tenant mismatch denial.
- Section 7 (Testing): executed RED -> GREEN with targeted negative-path tests and full touched-module regression runs.

## Implemented Changes
### SDK
- Hardened identity wrapper resolution to reject blank or whitespace `tenant_id` / `user_id` before delegation.
- Added deterministic bootstrap outcome tracking in `soorma dev`:
  - `CREATED` when no prior bootstrap state exists.
  - `REUSED` when bootstrap fingerprint matches previous state.
  - `FAILED_DRIFT` (fail-closed) when persisted state is malformed or fingerprint changes.
- Added bootstrap state persistence file in `.soorma/bootstrap-state.json` and cleanup on `soorma dev --stop --clean`.

### Identity Service
- Refactored principal/domain/platform mismatch pre-check to raise `IdentityServiceError`.
- Updated `/v1/identity/tokens/issue` route to emit typed safe `detail` envelopes for mismatch and lookup failures:
  - `code`
  - `message`
  - `correlation_id`

### Shared Dependency
- Hardened tenancy middleware JWT processing:
  - Reject unsupported `principal_type` values.
  - Reject malformed `roles` claims that are not collection types.
  - Preserve fail-closed 401 behavior on invalid JWT claim structure.

## Files Updated
- `sdk/python/soorma/identity/wrapper.py`
- `sdk/python/soorma/cli/commands/dev.py`
- `sdk/python/tests/test_context_identity_wrapper.py`
- `sdk/python/tests/cli/test_dev.py`
- `services/identity-service/src/identity_service/api/v1/tokens.py`
- `services/identity-service/tests/test_token_api.py`
- `libs/soorma-service-common/src/soorma_service_common/middleware.py`
- `libs/soorma-service-common/tests/test_middleware.py`

## RED -> GREEN Evidence
### RED failures observed
- Middleware accepted unsupported `principal_type` and malformed `roles` claim (expected 401, got 200).
- Identity wrapper accepted blank identity values instead of failing closed.
- Token API platform mismatch returned plain-string detail instead of typed safe envelope.

### GREEN verification (targeted)
- `2 passed`: middleware hardening tests.
- `1 passed`: SDK wrapper blank-identity fail-closed test.
- `2 passed`: identity-service typed mismatch envelope tests.
- `6 passed`: CLI bootstrap-state helper tests.

### Regression verification (touched modules)
- `30 passed`: `sdk/python/tests/cli/test_dev.py` and `sdk/python/tests/test_context_identity_wrapper.py`
- `19 passed`: `libs/soorma-service-common/tests/test_middleware.py`
- `7 passed`: `services/identity-service/tests/test_token_api.py`

## Notes
- Public API signatures for wrapper methods were preserved.
- Changes are backward-compatible for local development defaults while adding deterministic drift protection for local stack bootstrap.
