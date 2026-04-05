# Identity Service: Technical Guide

**Status:** Active
**Last Updated:** April 4, 2026

## Overview

Identity Service provides platform-tenant identity APIs used by Soorma services during onboarding, token issuance, and delegated trust enforcement.

This service currently covers:
- platform tenant identity-domain onboarding
- principal lifecycle management
- delegated issuer trust registration
- mapping collision policy evaluation
- token issuance with typed deny semantics

## Why This Service Exists

The identity domain is a security and tenancy boundary. It centralizes principal state, trust metadata, and issuance/audit records so other platform services can rely on a consistent identity contract.

## Runtime Boundaries

- Service package: `services/identity-service`
- API mount prefix: `/v1/identity`
- Shared DTO package: `libs/soorma-common`
- Shared auth/context dependency package: `libs/soorma-service-common`

## Endpoint Summary

| Endpoint | Method | Request DTO | Response DTO |
|---|---|---|---|
| `/v1/identity/onboarding` | POST | `OnboardingRequest` | `OnboardingResponse` |
| `/v1/identity/principals` | POST | `PrincipalRequest` | `PrincipalResponse` |
| `/v1/identity/principals/{principal_id}` | PUT | `PrincipalRequest` | `PrincipalResponse` |
| `/v1/identity/principals/{principal_id}/revoke` | POST | none | `PrincipalResponse` |
| `/v1/identity/tokens/issue` | POST | `TokenIssueRequest` | `TokenIssueResponse` |
| `/v1/identity/delegated-issuers` | POST | `DelegatedIssuerRequest` | `DelegatedIssuerResponse` |
| `/v1/identity/delegated-issuers/{delegated_issuer_id}` | PUT | `DelegatedIssuerRequest` | `DelegatedIssuerResponse` |
| `/v1/identity/mappings/evaluate` | POST | `MappingEvaluationRequest` | `MappingEvaluationResponse` |
| `/health` | GET | none | service status payload |

## Request Context Model

Identity endpoints use shared tenancy middleware and dependencies.

Headers used by request-context dependency:
- `X-Tenant-ID`
- `X-Service-Tenant-ID`
- `X-User-ID`

Optional tracing headers:
- `X-Correlation-ID`
- `X-Request-ID`

Behavior:
- missing user-context dimensions fail closed
- request validation logs preserve correlation IDs when present
- token issuance deny paths return typed safe error payloads

## Security And Behavior Notes

- JWT path is authoritative when JWT is present.
- Coexistence mode remains compatible for legacy header-based context where applicable.
- Delegated issuance requires trusted issuer state.
- Mapping collision default is deny unless explicit override is requested and caller principal qualifies.

## Local Development

```bash
cd services/identity-service
pip install -e ".[dev]"
alembic upgrade head
uvicorn identity_service.main:app --reload --port 8085
```

## Testing

```bash
cd /path/to/soorma-core
python -m pytest services/identity-service/tests
python -m pytest services/identity-service/tests --cov=services/identity-service/src/identity_service --cov-report=term
python -m pytest libs/soorma-service-common/tests/test_dependencies.py
```

## Related Docs

- Architecture details: [ARCHITECTURE.md](./ARCHITECTURE.md)
- Use-case scenarios: [USE_CASES.md](./USE_CASES.md)
- Service README: [services/identity-service/README.md](../../services/identity-service/README.md)
- QA coverage matrix (Unit-1/Unit-2): [aidlc-docs/platform/identity-service/construction/test-cases/qa-coverage-unit1-unit2.md](../../aidlc-docs/platform/identity-service/construction/test-cases/qa-coverage-unit1-unit2.md)
