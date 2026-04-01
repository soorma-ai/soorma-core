# System Architecture

## System Overview
soorma-core is a Python multi-package platform. The SDK provides high-level wrappers (`PlatformContext`) over internal service clients. Backend services provide registry, memory, tracker, and event APIs. Shared libraries centralize models and tenancy middleware.

## Architecture (Text Representation)
1. Agent handlers use `PlatformContext` wrappers.
2. Wrappers delegate to low-level service clients.
3. Service clients call FastAPI services over HTTP.
4. Services apply tenancy middleware and database RLS context.
5. Shared models enforce cross-layer contract consistency.

## Component Descriptions
### sdk/python/soorma/context.py
- **Purpose**: Wrapper layer (`context.memory`, `context.bus`, `context.registry`, `context.tracker`)
- **Responsibilities**: Identity extraction defaults, delegation to service clients.
- **Dependencies**: `soorma.memory.client`, `soorma.events`, `soorma.registry.client`, `soorma.tracker.client`
- **Type**: Application SDK wrapper layer

### sdk/python/soorma/memory/client.py
- **Purpose**: Low-level memory HTTP client
- **Responsibilities**: Send platform/service tenant and user headers; map responses
- **Dependencies**: Memory service endpoints and common models
- **Type**: Client

### services/*
- **Purpose**: Control-plane services
- **Responsibilities**: Tenant-aware CRUD, eventing, registry, plan/task visibility
- **Dependencies**: Shared libs, PostgreSQL, transport adapters
- **Type**: Application services

### libs/soorma-service-common
- **Purpose**: Shared tenancy/auth middleware patterns
- **Responsibilities**: Header validation, user-context requirements, per-request DB RLS setup
- **Dependencies**: FastAPI, SQLAlchemy async
- **Type**: Shared library

## Data Flow (Key Workflow)
- Planner publishes task event.
- Worker receives task, persists context into memory.
- Worker delegates/awaits sub-work through event service.
- Result event resumes workflow and updates tracker/memory.

## Integration Points
- **External APIs**: HTTP APIs of registry/memory/tracker/event-service.
- **Databases**: PostgreSQL (including tenant-aware RLS usage in services).
- **Third-party Services**: NATS/Kafka adapters for event transport; optional LLM providers via SDK integrations.

## Infrastructure Components
- **Deployment Model**: Service-per-domain backend + Python SDK clients.
- **Networking**: HTTP service endpoints + event streaming/bus channels.
- **Tenancy Boundaries**:
  - Tier 1 (Developer tenant): Registry scope.
  - Tier 2 (Client tenant + user): Memory/Tracker/Event scope.