# Changelog

## [Unreleased]

- Added canonical `tenant_id` claim issuance alongside compatibility claims for cutover consumers.
- Documented RS256/JWKS-first local bootstrap defaults and fail-closed verifier expectations for `soorma dev`.
- Added initial identity-service scaffold for AI-DLC code generation.
- Expanded service README with API, auth, token-contract, and testing guidance.
- Added technical docs in `docs/identity_service/` for architecture and use cases.
- Added Unit 3 compatibility-phase asymmetric signing path support in provider facade with explicit `kid` and `alg` metadata.
- Added deterministic verifier precedence in provider facade (JWKS primary with static fallback) plus fail-closed deny behavior.
- Added discovery endpoints for `/.well-known/openid-configuration` and `/.well-known/jwks.json` under v1 identity routes.
- Added provider and API tests for JWKS publication, discovery metadata, unknown `kid`, invalid signature, and JWKS precedence behavior.
