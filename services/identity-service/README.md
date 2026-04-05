# Identity Service

Identity Service provides platform-tenant identity domain APIs for:
- tenant onboarding
- principal lifecycle management
- token issuance claim contracts
- delegated issuer trust registration
- mapping and collision governance

## Local Run

```bash
cd services/identity-service
pip install -e ".[dev]"
alembic upgrade head
uvicorn identity_service.main:app --reload --port 8085
```
