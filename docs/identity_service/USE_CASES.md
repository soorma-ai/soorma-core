# Identity Service: Use Cases

**Status:** Active
**Last Updated:** April 4, 2026

## Purpose

This document captures concrete use cases for Identity Service and maps each use case to service endpoints and expected outcomes.

## Use Case 1: Platform Tenant Onboarding

Scenario:
- A new platform tenant is provisioned and needs an identity domain with bootstrap admin principal.

Endpoint:
- `POST /v1/identity/onboarding`

Expected outcomes:
- tenant identity domain exists
- bootstrap principal exists in active lifecycle state
- operation is atomic across domain and principal writes
- onboarding audit event is recorded

## Use Case 2: Principal Lifecycle Management

Scenario:
- Tenant admin manages principals for users and machine identities.

Endpoints:
- `POST /v1/identity/principals`
- `PUT /v1/identity/principals/{principal_id}`
- `POST /v1/identity/principals/{principal_id}/revoke`

Expected outcomes:
- lifecycle state transitions are persisted
- update and revoke operations are auditable

## Use Case 3: Delegated Issuer Trust Registration

Scenario:
- Tenant wants to allow delegated token issuance from a trusted external issuer.

Endpoints:
- `POST /v1/identity/delegated-issuers`
- `PUT /v1/identity/delegated-issuers/{delegated_issuer_id}`

Expected outcomes:
- issuer metadata is persisted and queryable for trust checks
- trust state is enforced during delegated token issuance
- trust changes are auditable

## Use Case 4: Token Issuance For Platform Principal

Scenario:
- A valid active principal requests a platform token for service access.

Endpoint:
- `POST /v1/identity/tokens/issue`

Expected outcomes:
- bearer token issued
- mandatory claim contract present
- issuance record persisted
- issuance audit event recorded

## Use Case 5: Delegated Issuance Denial

Scenario:
- Token request is delegated but delegated issuer is unknown or inactive.

Endpoint:
- `POST /v1/identity/tokens/issue`

Expected outcomes:
- request denied fail-closed
- typed safe error payload returned by API
- denial issuance record persisted with reason code
- denial audit event recorded

## Use Case 6: Mapping Collision Governance

Scenario:
- External identity binding collides with existing canonical binding.

Endpoint:
- `POST /v1/identity/mappings/evaluate`

Expected outcomes:
- collision without override is denied
- override requests require explicit governance checks
- evaluation result includes decision and reason code
- evaluation is auditable

## Request Context Expectations

Protected endpoints depend on request identity context:
- `X-Tenant-ID`
- `X-Service-Tenant-ID`
- `X-User-ID`

Optional tracing:
- `X-Correlation-ID`
- `X-Request-ID`

Missing required service context fails closed.

## QA Traceability

Coverage for Unit-1 and Unit-2 identity QA cases is documented in:
- [aidlc-docs/platform/identity-service/construction/test-cases/qa-coverage-unit1-unit2.md](../../aidlc-docs/platform/identity-service/construction/test-cases/qa-coverage-unit1-unit2.md)
