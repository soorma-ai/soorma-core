# API Documentation

## Registry Service APIs (Tier 1)
### Register Agent
- **Method**: POST
- **Path**: `/v1/agents`
- **Purpose**: Register/update agent metadata for developer tenant.
- **Identity Context**: `X-Tenant-ID` (developer tenant only).

### Query Agents
- **Method**: GET
- **Path**: `/v1/agents`
- **Purpose**: Query discoverable agents within developer scope.
- **Identity Context**: `X-Tenant-ID`.

### Agent Heartbeat
- **Method**: POST/PUT
- **Path**: `/v1/agents/{agent_id}/heartbeat`
- **Purpose**: Keep agent registration active.
- **Identity Context**: `X-Tenant-ID`.

## Memory Service APIs (Tier 2)
### Working Memory Set/Get/Delete
- **Method**: PUT/GET/DELETE
- **Path**: `/v1/working/{plan_id}/{key}` and `/v1/working/{plan_id}`
- **Purpose**: Manage plan-scoped state.
- **Identity Context**: `X-Tenant-ID` + `X-Service-Tenant-ID` + `X-User-ID`.

### Semantic/Episodic/Procedural Memory
- **Method**: POST/GET
- **Paths**: `/v1/semantic*`, `/v1/episodic*`, `/v1/procedural/context`
- **Purpose**: Knowledge and interaction memory operations.
- **Identity Context**: tier-2 header triplet.

### Task/Plan Context
- **Method**: POST/GET
- **Paths**: `/v1/task-context*`, `/v1/plans*`
- **Purpose**: Persist and retrieve task/plan execution context.
- **Identity Context**: tier-2 header triplet.

## Tracker Service APIs (Tier 2)
### Plan Progress
- **Method**: GET
- **Path**: `/v1/plans/{plan_id}`
- **Purpose**: Retrieve plan progress/state.
- **Identity Context**: tier-2 header triplet.

### Plan Actions
- **Method**: GET
- **Path**: `/v1/plans/{plan_id}/actions`
- **Purpose**: Retrieve task/action execution history.
- **Identity Context**: tier-2 header triplet.

## Event Service APIs (Tier 2)
### Publish Event
- **Method**: POST
- **Path**: `/publish`
- **Purpose**: Ingest event envelopes and route to subscribers.
- **Identity Context**: platform tenant header + envelope tenant/user context.

## Internal APIs and Models
- `PlatformContext` wrappers in SDK are mandatory entrypoints for agent handlers.
- Shared models/events live in `libs/soorma-common`.
- Tenancy middleware and user-context dependencies live in `libs/soorma-service-common`.