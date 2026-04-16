# soorma-service-common

Shared FastAPI/Starlette infrastructure library for Soorma backend services.

Provides three cross-cutting concerns for all services (Memory, Tracker, Registry, Event Service):

1. **Identity extraction** — `TenancyMiddleware` validates bearer tokens and projects platform-tenant, service-tenant, and service-user identity into `request.state` on secured requests.
2. **RLS activation** — `create_get_tenanted_db` factory produces a FastAPI dependency that calls PostgreSQL `set_config` for all three session variables (transaction-scoped) before yielding the DB session, activating Row-Level Security policies.
3. **GDPR deletion contract** — `PlatformTenantDataDeletion` abstract base class defines the erasure interface; concrete implementations live in each service.

## Usage

```python
# In your service's core/dependencies.py
from soorma_service_common import (
    create_get_tenanted_db,
    create_get_tenant_context,
)
from my_service.core.database import get_db

get_tenanted_db = create_get_tenanted_db(get_db)
get_tenant_context = create_get_tenant_context(get_tenanted_db)
```

```python
# In your service's main.py
from soorma_service_common import TenancyMiddleware

app.add_middleware(TenancyMiddleware)
```

```python
# In your route handlers
from my_service.core.dependencies import get_tenant_context
from soorma_service_common import TenantContext

@router.post("/items")
async def create_item(payload: ItemCreate, ctx: TenantContext = Depends(get_tenant_context)):
    return await service.create(ctx.db, ctx.platform_tenant_id, ctx.service_tenant_id, ctx.service_user_id, payload)
```

## Constraints

- **MUST NOT** be imported by `soorma-common` or `sdk/python` — contains FastAPI/Starlette dependencies incompatible with SDK clients.
- `platform_tenant_id` flows from validated request identity or Event Service injection — never as a per-call API parameter.
