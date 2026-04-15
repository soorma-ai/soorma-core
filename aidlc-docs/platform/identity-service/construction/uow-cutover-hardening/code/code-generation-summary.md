# Code Generation Summary - uow-cutover-hardening

## Scope Completed
- Hardened shared tenancy middleware so secured non-public routes require bearer JWTs, preserve the trusted admin-key exception for identity control-plane paths, and prefer canonical `tenant_id` claims over compatibility aliases.
- Updated low-level SDK Memory and Tracker clients so the active bearer-auth path sends `Authorization` without legacy `X-*` identity headers.
- Added canonical `tenant_id` issuance in identity-service tokens while preserving compatibility claims for bounded migration.
- Switched `soorma dev` local bootstrap from HS256-secret defaults to persisted `.soorma/identity/` RSA key material with inline JWKS/public-key verifier material derived from those files.

## Brownfield Files Changed
- `libs/soorma-service-common/src/soorma_service_common/middleware.py`
- `sdk/python/soorma/memory/client.py`
- `sdk/python/soorma/tracker/client.py`
- `sdk/python/soorma/cli/commands/dev.py`
- `services/identity-service/src/identity_service/services/token_service.py`
- Focused tests under `libs/soorma-service-common/tests/`, `sdk/python/tests/`, and `services/identity-service/tests/`
- Documentation and changelogs under `services/identity-service/`, `sdk/python/`, and `docs/identity_service/`

## Architecture Alignment
- Section 1 Authentication and tenancy: secured ingress now denies header-only requests after cutover, while the explicit trusted admin-key exception remains bounded to identity control-plane routes.
- Section 2 Two-layer SDK: handler-facing wrapper surfaces were unchanged; bearer-auth transport changes remain inside low-level clients and CLI bootstrap.
- Section 4 Multi-tenancy: active runtime extraction now prefers canonical `tenant_id` while keeping compatibility claims bounded to migration seams.
- Section 6 Error handling: deny behavior remains fail closed for missing bearer tokens, invalid signatures, and unknown-key conditions.

## Verification Executed
- `sdk/python/tests/cli/test_dev.py`
- `sdk/python/tests/test_memory_client.py`
- `sdk/python/tests/test_tracker_service_client.py`
- `sdk/python/tests/test_context_wrappers.py`
- `sdk/python/tests/test_context_identity_wrapper.py`
- `libs/soorma-service-common/tests/test_middleware.py`
- `services/identity-service/tests/test_token_api.py`
- `services/identity-service/tests/test_provider_facade.py`
- `services/identity-service/tests/test_delegated_issuer_api.py`
- `services/identity-service/tests/test_discovery_api.py`

## Results
- SDK CLI + client suites: 58 passed
- Shared middleware suite: 29 passed
- Identity token API suite: 7 passed
- Provider facade suite: 6 passed
- Delegated issuer + discovery suites: 5 passed
- Onboarding API suite: 4 passed
- Wrapper suites: 25 passed
- CLI correction pass after review feedback: 29 passed

## Residual Notes
- Identity-service persistence still retains compatibility-era naming in storage tables; this unit keeps that behind a bounded migration seam while moving active issuance/verification behavior toward canonical `tenant_id`.
- Monorepo pytest invocations still need package-local grouping because multiple `tests/conftest.py` files collide when mixed in one command.
- Local key rotation now follows the documented delete-and-regenerate path: remove `.soorma/identity/` files and rerun `soorma dev`.