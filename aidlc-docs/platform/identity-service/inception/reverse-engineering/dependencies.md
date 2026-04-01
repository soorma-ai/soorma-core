# Dependencies

## Internal Dependencies
- `sdk/python/soorma` depends on:
  - `libs/soorma-common` for DTOs and event models.
  - service APIs (`services/registry`, `services/memory`, `services/tracker`, `services/event-service`) via HTTP.
- `services/*` depend on:
  - `libs/soorma-common` for shared schemas.
  - `libs/soorma-service-common` for tenancy and request dependencies.
- `services/event-service` uses transport adapters (`libs/soorma-nats`) for pub/sub integration.

## Dependency Relationships
### SDK -> Services
- **Type**: Runtime API dependency
- **Reason**: Wrappers delegate to concrete HTTP clients.

### Services -> Shared Libraries
- **Type**: Compile/runtime
- **Reason**: Model consistency and middleware reuse.

### Examples -> SDK
- **Type**: Runtime
- **Reason**: Demonstrate canonical usage patterns.

## External Dependencies (Representative)
### FastAPI
- **Purpose**: Service routing and dependency injection.

### SQLAlchemy Async
- **Purpose**: Async DB access and transaction boundaries.

### PostgreSQL (+pgvector)
- **Purpose**: relational storage + vector retrieval.

### httpx
- **Purpose**: SDK outbound API communication.

### Pydantic v2
- **Purpose**: validation and serialization contracts.