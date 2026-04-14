# Product Requirements Document: JWT-First Service Authentication (Future Work)

**Status:** Future Work (Not in current implementation scope)
**Owner:** Soorma Core Platform Team
**Last Updated:** April 14, 2026
**Related Initiative:** aidlc-docs/platform/identity-service/

## 1. Summary

This PRD captures the target authentication model for a future iteration where service authentication is JWT-first across Soorma Core, with one bounded exception for token issuance bootstrap.

This document is intentionally forward-looking. It does not change current runtime behavior.

## 2. Problem Statement

Current compatibility mode supports mixed auth behavior during migration. This is useful for incremental delivery, but it leaves temporary paths (legacy headers and broad admin-key issuance model) that should be removed in the final state.

We need a clear target contract so future hardening/cutover work is unambiguous.

## 3. Goals

- Enforce a single JWT-first authentication model for secured service endpoints.
- Keep token issuance bootstrap bounded and explicit.
- Standardize claim contract so platform-tier and tier-2 context can be enforced consistently.
- Preserve tenant flexibility by allowing tenant-managed trusted identity proxies.

## 4. Non-Goals

- Implementing this model in the current unit.
- Replacing the tenant-side identity provider design choices.
- Defining UI or developer portal workflows.

## 5. Proposed Target Pattern

1. Identity token issuance endpoint is the only secured endpoint that may accept admin/API-key caller authentication without requiring an incoming JWT.
2. All other secured endpoints require a valid JWT issued by Soorma identity service (or trusted delegated issuer where explicitly allowed by policy).
3. JWT always includes platform tenant context.
4. JWT may include tier-2 service tenant and service user context when required by the target service.
5. Platform tenants own a trusted identity proxy that authenticates caller actors and requests JWTs from Soorma identity service with appropriate claims.

## 6. Endpoint Authentication Policy Matrix (Target)

| Surface | Target Auth Requirement | Notes |
|---|---|---|
| Identity token issuance | Admin/API-key (bootstrap/trusted caller) | Only bounded exception path |
| Identity principal/admin APIs | JWT required | Admin scope/role required |
| Memory service APIs | JWT required | Must carry platform + tier-2 context |
| Tracker service APIs | JWT required | Must carry platform + tier-2 context |
| Event service publish/stream | JWT required | Platform tenant claim required; tier-2 claims as applicable |
| Registry APIs | JWT or developer API credential mapped to platform tenant | Final decision tracked in open questions |
| Health endpoints | Public or infra-auth | Not treated as secured business endpoints |
| Discovery/JWKS endpoints | Public read | Required for verifier key discovery |

## 7. JWT Claim Contract (Target)

### 7.1 Required claims (all secured service calls)

- `iss`
- `aud`
- `exp`
- `iat`
- `kid` (header)
- `platform_tenant_id`
- `principal_id`
- `principal_type`

### 7.2 Conditional claims (service-specific)

- `service_tenant_id` (required for tier-2 scoped endpoints)
- `service_user_id` (required for user-scoped tier-2 endpoints)
- `roles` and/or `scopes` (required for authorization policy enforcement)

### 7.3 Validation requirements

- Fail closed on missing required claims.
- Fail closed on issuer or audience mismatch.
- Fail closed on invalid signature or unknown `kid`.
- Enforce tenant-boundary checks using claims, not request-body overrides.

## 8. Trusted Identity Proxy Responsibilities (Tenant-Owned)

- Authenticate tenant actors (human or service).
- Resolve actor to Soorma principal identity mapping.
- Request JWT from Soorma identity service using trusted caller credentials.
- Include appropriate platform and tier-2 claims per intended service call.
- Enforce tenant-local auth policy before requesting Soorma tokens.

## 9. Security Requirements (Target)

- Asymmetric signing only for platform-issued JWTs in production path.
- JWKS-based verifier distribution with `kid` rotation support.
- Bounded token TTL and refresh policy.
- Deterministic revocation/disable behavior for principals and signing keys.
- Audit records for issuance, override usage, and denial paths.

## 10. Open Decisions to Resolve Before Implementation

- Registry final auth mode: JWT claim-only versus dedicated developer API credential mapped to platform tenant.
- Identity onboarding/bootstrap semantics under JWT-first mode.
- Authorization model standardization: role-only, scope-only, or hybrid.
- Event stream re-auth strategy for long-lived connections.
- Revocation semantics for already-issued tokens during key rollover or principal suspension.

## 11. Migration and Delivery Guidance

This PRD should be implemented in a future iteration after current compatibility-phase closure work is complete.

Recommended sequencing:

1. Complete current Unit 3 closure and Build/Test evidence.
2. Execute Unit 4 cutover-hardening scope (legacy/compatibility removal and strict enforcement baseline).
3. Implement PRD deltas not already covered by Unit 4 in a dedicated follow-up unit/initiative.

## 12. Acceptance Criteria for Future Implementation

- No secured endpoint (except token issuance bootstrap path) accepts non-JWT caller auth.
- JWT claim contract is documented and validated consistently across services.
- Legacy header compatibility path is removed from production flows.
- Issuance and authorization failures are deterministic and fail closed.
- Regression suite covers positive, negative, cross-tenant, and key-rotation scenarios.
