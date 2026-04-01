# Code Structure

## Build System
- **Type**: Python monorepo with multiple package roots.
- **Configuration**: Repository-level docs and package-level configs under `sdk/`, `services/`, `libs/`, and `examples/`.

## Key Modules
- `sdk/python/soorma/context.py` - High-level wrapper layer.
- `sdk/python/soorma/events.py` - Event client and publish/subscribe APIs.
- `sdk/python/soorma/memory/client.py` - Memory low-level client.
- `sdk/python/soorma/tracker/client.py` - Tracker low-level client.
- `sdk/python/soorma/registry/client.py` - Registry client.
- `libs/soorma-service-common/src/soorma_service_common/dependencies.py` - tenancy dependencies and RLS session config.
- `services/registry/src/registry_service/api/v1/agents.py` - developer-tenant agent APIs.
- `services/memory/src/memory_service/api/v1/working.py` - user-context working-memory APIs.
- `services/event-service/src/api/routes/events.py` - event publishing routes.

## Existing Files Inventory (Identity-Service-Relevant)
- `docs/ARCHITECTURE_PATTERNS.md` - two-tier tenancy and SDK architecture mandates.
- `sdk/python/soorma/context.py` - wrapper delegation and identity resolution defaults.
- `sdk/python/soorma/events.py` - event publish and envelope behavior.
- `sdk/python/soorma/memory/client.py` - tier-2 header contract at client boundary.
- `libs/soorma-service-common/src/soorma_service_common/dependencies.py` - identity validation and DB session context.
- `libs/soorma-service-common/src/soorma_service_common/tenancy.py` - middleware-level identity extraction.
- `services/registry/src/registry_service/api/v1/agents.py` - tier-1 API patterns.
- `services/memory/src/memory_service/api/v1/*.py` - tier-2 API patterns.
- `services/tracker/src/tracker_service/api/v1/*.py` - tier-2 query patterns.

## Design Patterns
### Two-Layer SDK Pattern
- **Location**: `sdk/python/soorma/context.py`
- **Purpose**: Keep agent handlers decoupled from low-level service clients.
- **Implementation**: Wrapper methods delegate to service clients after context resolution.

### Tenant Context + RLS Pattern
- **Location**: `libs/soorma-service-common/src/soorma_service_common/dependencies.py`
- **Purpose**: Enforce tenant/user isolation uniformly.
- **Implementation**: Middleware/dependencies set PostgreSQL session variables per request.

### Event Choreography Pattern
- **Location**: `sdk/python/soorma/task_context.py`, `examples/10-choreography-basic/`
- **Purpose**: Explicit request/response event choreography.
- **Implementation**: `response_event` carried in envelope and used for responses.

## Critical Dependencies
- **FastAPI**: service API framework.
- **SQLAlchemy Async**: data access layer.
- **Pydantic v2**: DTO validation.
- **httpx**: SDK-service HTTP transport.
- **PostgreSQL**: persistent state and RLS enforcement.
- **NATS/Kafka adapters**: event transport integration.