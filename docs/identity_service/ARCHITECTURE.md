# Identity Service: Architecture

**Status:** Active
**Last Updated:** April 4, 2026

## Executive Summary

Identity Service implements identity-domain write operations and token issuance for platform tenants. It composes shared request-context dependencies from `soorma-service-common`, shared DTO contracts from `soorma-common`, and internal persistence repositories backed by SQLAlchemy.

## High-Level Components

- API layer
  - FastAPI routes in `src/identity_service/api/v1/`
  - DTO contracts from `soorma_common.models`
- Dependency/context layer
  - Tenant context and RLS session activation from `soorma_service_common`
- Domain service layer
  - onboarding, principal lifecycle, delegated trust, mapping policy, token issuance, audit
- Repository layer
  - CRUD modules in `src/identity_service/crud/`
- Persistence layer
  - Postgres schema via Alembic migration `0001_identity_core_init.py`

## Request Flow

1. Request enters FastAPI app (`identity_service.main`).
2. `TenancyMiddleware` extracts context headers to request state.
3. Request dependency resolves `TenantContext` and activates DB session context.
4. Route calls service method.
5. Service delegates persistence to repositories and writes audit records.
6. Route returns DTO response or typed safe HTTP error.

## API Layer Notes

Mounted prefix: `/v1/identity`

Route groups:
- onboarding
- principals
- tokens
- delegated_issuers
- mappings

Health route:
- `/health`

## Domain Services

### Onboarding Service

Responsibilities:
- create tenant domain
- create bootstrap admin principal
- enforce atomic write behavior
- write onboarding audit event

### Principal Service

Responsibilities:
- create principal
- update principal
- revoke principal
- emit principal lifecycle audit events

### Delegated Trust Service

Responsibilities:
- register delegated issuer metadata
- update delegated issuer metadata
- determine trust eligibility for delegated issuance

### Mapping Service

Responsibilities:
- evaluate collision policy
- deny collision by default where no override requested
- enforce explicit override checks
- emit mapping evaluation audit event

### Token Service

Responsibilities:
- validate principal lifecycle state
- verify tenant domain existence
- enforce delegated trust checks
- issue signed token through provider facade
- persist issuance decision records
- emit issuance and deny audit events
- raise typed business errors for stable API mapping

## Typed Error Contract

Token issuance maps domain errors to safe API responses.

Current typed fields:
- `code`
- `message`
- `correlation_id`

This supports fail-closed semantics while avoiding sensitive details in response bodies.

## Claim Contract

Issued tokens include mandatory base claims and identity context:
- `iss`, `sub`, `aud`, `exp`, `iat`, `jti`
- `platform_tenant_id`, `principal_id`, `principal_type`, `roles`

Delegated identifier claim is added when delegated issuance is used.

## Persistence Model

Core tables:
- `platform_tenant_identity_domains`
- `principals`
- `role_assignments`
- `delegated_issuers`
- `claim_mapping_policies`
- `external_identity_bindings`
- `token_issuance_records`
- `identity_audit_events`

Migration:
- `services/identity-service/alembic/versions/0001_identity_core_init.py`

## Configuration

Primary runtime settings in `src/identity_service/core/config.py`:
- `DATABASE_URL`
- `SYNC_DATABASE_URL`
- `IS_PROD`
- `IDENTITY_ADMIN_API_KEY`

Additional runtime auth/signing settings used by middleware/provider:
- `IDENTITY_SIGNING_KEY`
- `SOORMA_AUTH_JWT_SECRET`
- `SOORMA_AUTH_JWT_ISSUER`
- `SOORMA_AUTH_JWT_AUDIENCE`

Local stack behavior:
- `soorma dev --start` generates `.soorma/docker-compose.yml` and `.soorma/.env` and injects local defaults for the above identity/JWT variables.
- Exporting these variables before `soorma dev --start` overrides generated defaults for local testing.

## Architecture Alignment

This service aligns with `docs/ARCHITECTURE_PATTERNS.md` sections:
- Section 1: auth and tenancy context model
- Section 4: tenant isolation and context propagation
- Section 6: error handling and safe envelopes
- Section 7: testability and integration coverage

## Related Documents

- Guide: [README.md](./README.md)
- Use cases: [USE_CASES.md](./USE_CASES.md)
- Service README: [services/identity-service/README.md](../../services/identity-service/README.md)
