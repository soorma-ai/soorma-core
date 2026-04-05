# Identity Service

Identity Service manages platform-tenant identity lifecycle for Soorma Core.

Current capabilities:
- tenant domain onboarding
- principal lifecycle management
- JWT token issuance with mandatory claim contract
- delegated issuer trust registration
- external identity mapping and collision governance

## API Surface

Base path: `/v1/identity`

| Endpoint | Method | Purpose |
|---|---|---|
| `/onboarding` | POST | Create tenant identity domain and bootstrap admin principal |
| `/principals` | POST | Create principal |
| `/principals/{principal_id}` | PUT | Update principal |
| `/principals/{principal_id}/revoke` | POST | Revoke principal |
| `/tokens/issue` | POST | Issue platform or delegated token |
| `/delegated-issuers` | POST | Register delegated issuer |
| `/delegated-issuers/{delegated_issuer_id}` | PUT | Update delegated issuer |
| `/mappings/evaluate` | POST | Evaluate mapping collision policy |
| `/health` | GET | Service health |

## Auth And Context Headers

Identity routes use shared Soorma request-context dependencies.

For protected endpoints, provide:
- `X-Tenant-ID`
- `X-Service-Tenant-ID`
- `X-User-ID`

Optional request tracing headers:
- `X-Correlation-ID`
- `X-Request-ID`

If service-tenant or service-user context is missing, requests fail closed.

## Token Contract

Token issuance returns a bearer token. Current mandatory claim contract includes:
- `iss`
- `sub`
- `aud`
- `exp`
- `iat`
- `jti`
- `platform_tenant_id`
- `principal_id`
- `principal_type`
- `roles`

Delegated issuance failures use typed safe API errors:
- stable `code`
- safe `message`
- `correlation_id` when provided

## Local Run

```bash
cd services/identity-service
pip install -e ".[dev]"
alembic upgrade head
uvicorn identity_service.main:app --reload --port 8085
```

## Tests

```bash
cd /path/to/soorma-core
python -m pytest services/identity-service/tests
python -m pytest services/identity-service/tests --cov=services/identity-service/src/identity_service --cov-report=term
```

## Technical Documentation

- Architecture and design: [docs/identity_service/ARCHITECTURE.md](../../docs/identity_service/ARCHITECTURE.md)
- Service technical guide: [docs/identity_service/README.md](../../docs/identity_service/README.md)
- Use cases: [docs/identity_service/USE_CASES.md](../../docs/identity_service/USE_CASES.md)
- Unit-1 and Unit-2 QA coverage report: [aidlc-docs/platform/identity-service/construction/test-cases/qa-coverage-unit1-unit2.md](../../aidlc-docs/platform/identity-service/construction/test-cases/qa-coverage-unit1-unit2.md)
