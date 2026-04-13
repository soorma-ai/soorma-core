# Identity JWT Technical Architecture

**Status:** Active (Unit 3 compatibility phase)
**Last Updated:** April 13, 2026

## 1. Purpose and Scope

This document defines the current JWT architecture for Soorma Core identity flows during Unit 3 (SDK JWT integration compatibility phase), including:

- identity-service token issuance and discovery publication
- soorma-service-common middleware validation behavior
- local stack bootstrapping via soorma dev
- SDK client authentication behavior for infrastructure service calls

This is a technical design document for implementation and operations teams. It describes current behavior in code, not future aspirations.

## 2. Architecture Overview

Current JWT architecture has three cooperating layers:

1. Issuer layer (identity-service): issues signed JWTs and publishes discovery metadata/JWKS.
2. Verifier layer (soorma-service-common middleware): validates inbound JWTs for service requests.
3. Caller layer (SDK): supplies auth context to services (JWT path for identity client, compatibility headers elsewhere).

## 3. Identity Service JWT Issuance Design

### 3.1 Issuance API and signing path

Primary issuance endpoint:

- POST /v1/identity/tokens/issue

Token issuance flow:

1. API enforces admin caller auth and platform-tenant boundary checks.
2. Token service validates principal and issuance policy.
3. Provider facade signs JWT with configured signing algorithm and key material.
4. Token response returns token + tokenType=Bearer.

Relevant code paths:

- services/identity-service/src/identity_service/api/v1/tokens.py
- services/identity-service/src/identity_service/services/token_service.py
- services/identity-service/src/identity_service/services/provider_facade.py

### 3.2 Discovery and JWKS publication

Identity service publishes discovery metadata and JWKS at:

- GET /v1/identity/.well-known/openid-configuration
- GET /v1/identity/.well-known/jwks.json

Relevant code paths:

- services/identity-service/src/identity_service/api/v1/discovery.py
- services/identity-service/src/identity_service/services/provider_facade.py

### 3.3 Signing and verifier precedence inside identity-service

Provider facade behavior:

- Supports HS256 and RS256.
- Chooses algorithm by:
  1. IDENTITY_SIGNING_ALGORITHM (explicit), else
  2. RS256 if asymmetric key material is present, else
  3. HS256 fallback.

Delegated assertion validation precedence:

1. JWKS primary verifier material (IDENTITY_VERIFIER_JWKS_JSON or IDENTITY_JWKS_PUBLICATION_JSON)
2. Static fallback verifier keyring
3. Fail closed

## 4. Environment Settings for Correct JWT Enablement

This section defines required configuration to start identity-service with correct JWT behavior.

### 4.1 Core service runtime settings

- DATABASE_URL
- SYNC_DATABASE_URL (optional override)
- IS_PROD
- IDENTITY_ADMIN_API_KEY

### 4.2 Identity-service signing settings (issuer side)

Recommended Unit 3 asymmetric configuration:

- IDENTITY_SIGNING_ALGORITHM=RS256
- IDENTITY_ACTIVE_SIGNING_KID=<active-kid>
- IDENTITY_SIGNING_KEY_ID=<default-kid>
- IDENTITY_SIGNING_PRIVATE_KEY_PEM=<pem>
- IDENTITY_SIGNING_PUBLIC_KEY_PEM=<pem>

Alternative ring-based configuration:

- IDENTITY_SIGNING_PRIVATE_KEYRING_JSON={"kid-a":"<pem>",...}
- IDENTITY_SIGNING_PUBLIC_KEYRING_JSON={"kid-a":"<pem>",...}

Compatibility fallback (legacy/local):

- IDENTITY_SIGNING_KEY (used for HS256 fallback)
- IDENTITY_SIGNING_KEYRING_JSON (HS256 ring)

### 4.3 Identity-service discovery metadata settings

- IDENTITY_ISSUER=<public issuer base url>

When unset, issuer defaults to request base URL for discovery response generation.

### 4.4 Identity-service inbound JWT validation settings (middleware in identity-service)

Identity service also uses soorma-service-common middleware for inbound auth validation. Configure one of these verifier sources:

JWKS/discovery primary:

- SOORMA_AUTH_JWKS_URL=<jwks endpoint>
- or SOORMA_AUTH_JWKS_JSON=<inline jwks payload>

Issuer trust:

- SOORMA_AUTH_JWT_ISSUER=<explicit trusted issuer>
- or SOORMA_AUTH_OPENID_CONFIGURATION_URL / SOORMA_AUTH_OPENID_CONFIGURATION_JSON

Audience (optional but recommended):

- SOORMA_AUTH_JWT_AUDIENCE

Bounded fallback verifier material:

- SOORMA_AUTH_JWT_PUBLIC_KEYS_JSON={"kid":"<pem>",...}
- or SOORMA_AUTH_JWT_PUBLIC_KEY_PEM + SOORMA_AUTH_JWT_PUBLIC_KEY_ID

HS256 compatibility path:

- SOORMA_AUTH_JWT_SECRET

Cache control:

- SOORMA_AUTH_JWKS_CACHE_TTL_SECONDS

## 5. soorma-service-common Middleware Validation Model

### 5.1 Validation behavior

Request auth precedence:

1. If Authorization Bearer token is present:
   - JWT becomes authoritative.
   - Invalid JWT fails closed (no header fallback).
2. If JWT is absent:
   - Legacy header path remains available in compatibility phase.

Supported algorithms:

- RS256 (JWKS/discovery + static fallback)
- HS256 (secret-based compatibility path)

RS256 verifier precedence:

1. JWKS primary keys (from URL or inline JWKS)
2. Static fallback public keys
3. Fail closed

Important fail-closed rule:

- If JWKS primary keys are available and kid is present but signature verification fails, middleware denies immediately and does not silently fall back.

### 5.2 Issuer trust resolution

Issuer resolution order in middleware:

1. SOORMA_AUTH_JWT_ISSUER (explicit trust anchor)
2. Discovery issuer from SOORMA_AUTH_OPENID_CONFIGURATION_JSON
3. Discovery issuer from SOORMA_AUTH_OPENID_CONFIGURATION_URL
4. If unset, middleware does not enforce issuer check

### 5.3 Two-tier multi-tenancy enforcement model

Two-tier model (from architecture patterns):

Tier 1: Developer tenant scope (primarily registry).
Tier 2: Platform tenant + service tenant + user scope (memory/tracker/event and identity request context).

For tier-2 paths, middleware resolves and sets request context:

- platform_tenant_id
- service_tenant_id
- service_user_id
- principal identity metadata (when present)

Compatibility alias validation:

- If legacy alias headers are present with JWT, values must match canonical JWT claim values.
- Mismatch is denied fail closed.

Relevant code path:

- libs/soorma-service-common/src/soorma_service_common/middleware.py

## 6. soorma dev CLI Local Stack Configuration

soorma dev performs local stack provisioning by generating:

- .soorma/docker-compose.yml
- .soorma/.env
- .soorma/bootstrap-state.json (deterministic fingerprint tracking)

Relevant code path:

- sdk/python/soorma/cli/commands/dev.py

### 6.1 What it seeds by default

Current default local values are compatibility-oriented:

- IDENTITY_ADMIN_API_KEY=dev-identity-admin
- IDENTITY_SIGNING_KEY=dev-identity-signing-key
- SOORMA_AUTH_JWT_SECRET=dev-identity-signing-key
- SOORMA_AUTH_JWT_ISSUER=soorma-identity-service
- SOORMA_AUTH_JWT_AUDIENCE=soorma-services

### 6.2 Deterministic bootstrap behavior

CLI computes a fingerprint from key configuration inputs and returns:

- CREATED
- REUSED
- FAILED_DRIFT

If drift is detected, startup fails closed and requires reset via clean stop.

### 6.3 Enabling asymmetric local mode

CLI does not auto-generate RSA keypairs today. To run asymmetric local mode:

1. Export RS256-related env vars before soorma dev --start.
2. Provide signing key material and middleware verifier settings (JWKS URL/JSON or static public keys).
3. Recreate stack if bootstrap fingerprint drift is detected.

## 7. SDK Client JWT Authentication Behavior

### 7.1 Identity SDK client (current JWT-aware path)

IdentityServiceClient behavior:

1. Builds base auth headers with platform tenant + identity admin key.
2. Resolves caller JWT from:
   - SOORMA_IDENTITY_CALLER_JWT (explicit token), or
   - locally minted short-lived HS256 token from SOORMA_AUTH_JWT_SECRET.
3. Sends Authorization: Bearer <token> when JWT is available.
4. Can include bounded compatibility alias headers when SOORMA_IDENTITY_INCLUDE_LEGACY_ALIAS is true.

Relevant code path:

- sdk/python/soorma/identity/client.py

### 7.2 Other SDK infrastructure clients (current compatibility state)

Current state for memory/tracker/event/registry clients:

- still rely primarily on header-based identity propagation
- wrappers in PlatformContext resolve tenant_id/user_id from bound event metadata

Representative code paths:

- sdk/python/soorma/memory/client.py
- sdk/python/soorma/tracker/client.py
- sdk/python/soorma/events.py
- sdk/python/soorma/registry/client.py

This is expected during Unit 3 compatibility phase and is progressively converged in later cutover work.

## 8. Recommended Unit 3 Runtime Profiles

### 8.1 Local compatibility profile (default)

Use for deterministic local testing with minimal setup:

- HS256 enabled
- shared local secrets
- legacy header compatibility enabled where needed

### 8.2 Local asymmetric profile (recommended for Unit 3 verification)

Use for crypto/discovery validation:

- RS256 signing enabled in identity-service
- JWKS publication endpoints enabled
- middleware verifier configured with JWKS URL/JSON
- explicit issuer and audience configured

## 9. Validation and Test Coverage Anchors

Implementation validation currently includes tests for:

- discovery endpoint publication (openid-configuration, jwks.json)
- provider facade unknown kid and invalid signature deny paths
- middleware RS256 verification via JWKS primary
- middleware fallback and fail-closed paths
- issuer trust from explicit config and discovery metadata

Representative test paths:

- services/identity-service/tests/test_discovery_api.py
- services/identity-service/tests/test_provider_facade.py
- libs/soorma-service-common/tests/test_middleware.py
- services/identity-service/tests/test_token_api.py

## 10. Relationship to Core Architecture Patterns

This document is an implementation companion to:

- [ARCHITECTURE_PATTERNS.md](../ARCHITECTURE_PATTERNS.md)

Operational bootstrap details for local asymmetric setup are documented separately in:

- [ASYMMETRIC_BOOTSTRAP_PRIMER.md](./ASYMMETRIC_BOOTSTRAP_PRIMER.md)

It concretizes Section 1 (auth), Section 2 (two-layer SDK), Section 4 (tenancy), Section 6 (error handling), and Section 7 (testing) for JWT issuance and verification flows in Unit 3.
