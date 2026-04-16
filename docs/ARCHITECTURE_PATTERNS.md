# Soorma Core: Architecture Patterns

**Version:** 0.8.x (Pre-Production)  
**Status:** Living Document  
**Last Updated:** February 18, 2026

This document defines the core architectural patterns that MUST be followed across all Soorma Core development. All contributors MUST read and reference this document when working on SDK or backend service implementations.

---

## 1. Authentication & Authorization (Current Implementation)

### Soorma Two-Tier Tenancy Model

Soorma operates with **two distinct tenancy dimensions**. Understanding this distinction is critical for correct authentication and data isolation across services.

#### Tier 1: Developer Tenant (Soorma Platform Tenancy)

- **Who:** Agent developers (companies/individuals) who build on the Soorma Core platform
- **Purpose:** Isolates one developer's registered agents and event schemas from another developer's
- **Scope:** **Registry Service only** — agents, events, and payload schemas belong to the developer tenant
- **Identifier:** Platform-tenant identity carried in validated bearer-token claims
- **Current auth:** `Authorization: Bearer <jwt>` for secured runtime traffic
- **Future auth:** Selected control-plane routes may add API-key flows, but bearer-authenticated machine and developer principals remain the baseline runtime path
- **Example:** Acme Corp's registered workers are invisible to Contoso's workers in the same Soorma deployment

#### Tier 2: Client Tenant + User (Developer's Application Tenancy)

- **Who:** End-users and customer tenants of the **developer's** agentic application
- **Purpose:** Isolates one developer's customer's data from another customer's (memory, tasks, plans)
- **Scope:** **Memory Service, Tracker Service, Event Service** — task contexts, plans, episodic memory
- **Identifiers:** Platform tenant + client tenant + end-user identity carried in validated JWT claims
- **Current auth:** `Authorization: Bearer <jwt>`
- **Compatibility aliases:** `X-Service-Tenant-ID` and `X-User-ID` may appear on trusted internal calls, but they must match the JWT when present
- **Future auth:** Same bearer-token model with progressively stricter issuer validation and delegated-trust controls
- **Example:** Acme Corp's customer Alice's conversation history is isolated from customer Bob's

#### Service → Tenancy Tier Mapping

| Service | Tenancy Tier | Current Auth | Notes |
|---------|-------------|--------------|-------|
| **Registry Service** | Developer Tenant | Bearer JWT | Platform tenant and principal identity come from JWT claims |
| **Memory Service** | Client Tenant + User | Bearer JWT | Service tenant and user come from JWT claims |
| **Tracker Service** | Client Tenant + User | Bearer JWT | Service tenant and user come from JWT claims |
| **Event Service** | Client Tenant + User | Bearer JWT | Platform tenant claim is authoritative at ingress |

### Current Identity Projection Model

For the current multi-tenancy rollout, SDK and service code must treat identity as validated bearer-token state projected into request context by shared middleware:

| Concern | Current Source | Transport | Notes |
|---------|----------------|-----------|-------|
| Platform tenant | JWT `platform_tenant_id` or `tenant_id` claim | `Authorization: Bearer ...` | Required on secured routes |
| Service tenant | JWT `service_tenant_id` claim | `Authorization: Bearer ...` | Optional alias header cannot disagree with JWT |
| Service user | JWT `service_user_id`, `user_id`, `principal_id`, or `sub` claim | `Authorization: Bearer ...` | Optional alias header cannot disagree with JWT |

Current SDK rules:

- Low-level SDK clients accept auth explicitly via `auth_token` or `auth_token_provider`; they do not read bearer tokens from environment variables at runtime.
- PlatformContext wrappers may still default service-tenant and user values from the bound event envelope, but outbound service authentication is bearer-token based.
- `EventClient.publish()` must not inject `platform_tenant_id` into outbound event payloads. Event Service remains the trust boundary for platform-tenant enrichment.
- Trusted admin flows are limited to explicit identity-service admin headers; normal service traffic must not fall back to legacy tenancy headers.

---

### Current Pattern: Bearer Tokens (v0.8.x)

**Status:** Active runtime contract for secured service-to-service traffic

SDK-to-service communication uses **explicit bearer tokens**. Shared middleware validates the token and projects the resulting identity into `request.state`.

**Tier 2 services (Memory, Tracker, Event):**
- `Authorization: Bearer <jwt>` is required
- JWT claims carry platform tenant, service tenant, and service user identity
- Optional compatibility headers must match the token when present

**Tier 1 service (Registry):**
- `Authorization: Bearer <jwt>` is required
- JWT claims carry the developer platform tenant and the authenticated machine or developer principal

**Implementation (Tier 2 — Memory/Tracker/Event services):**

```python
# SDK MemoryServiceClient example (explicit bearer auth)
response = await self._client.post(
    f"{self.base_url}/v1/memory/task-context",
    json=data.model_dump(by_alias=True),
    headers={"Authorization": f"Bearer {token}"},
)
```

**Implementation (Tier 1 — Registry Service):**

```python
# RegistryClient — explicit bearer auth, developer tenant from claims
response = await self._client.post(
    f"{self.base_url}/v1/agents",
    json=request.model_dump(by_alias=True),
    headers={"Authorization": f"Bearer {token}"},
)
```

**Services Implementation:**

Services extract validated request identity and use it for:
- Row-Level Security (RLS) policies in PostgreSQL
- Query filtering by tenant/user
- Audit logging

```python
# Memory/Tracker service endpoint example (Tier 2 — identity resolved by middleware)
@router.post("/v1/memory/task-context")
async def store_task_context(
    data: TaskContextCreate,
    ctx: TenantContext = Depends(get_tenant_context),
):
    # Set session variables for RLS
    await db.execute(f"SET app.tenant_id = '{ctx.service_tenant_id}'")
    await db.execute(f"SET app.user_id = '{ctx.service_user_id}'")
    result = await db.execute(...)

# Registry service endpoint example (Tier 1 — developer tenant only)
@router.post("/v1/agents")
async def register_agent(
    data: AgentRegistrationRequest,
    platform_tenant_id: str = Depends(get_platform_tenant_id),
):
    await db.execute(f"SET app.tenant_id = '{platform_tenant_id}'")
    result = await db.execute(...)
```

**Database RLS Policies:**

```sql
-- Tier 2: Memory / Tracker tables (client tenant + user)
CREATE POLICY task_context_tenant_isolation ON task_context
    USING (tenant_id = current_setting('app.tenant_id')::UUID);

CREATE POLICY plans_user_access ON plans
    USING (
        tenant_id = current_setting('app.tenant_id')::UUID 
        AND user_id = current_setting('app.user_id')::UUID
    );

-- Tier 1: Registry tables (developer tenant only — no user_id column)
CREATE POLICY agents_tenant_isolation ON agents
    USING (tenant_id = current_setting('app.tenant_id')::UUID);
```

### Future Pattern: Delegated JWT Trust & Selective API Keys (v0.9.0+)

**Status:** 📋 Planned hardening and expansion work

The production authentication system will support dual modes:

**Mode 1: JWT Authentication (User and machine context)**
```python
# User-facing applications
context = PlatformContext(auth_token="jwt-token")
await context.memory.store_task_context(...)

# JWT payload contains:
# {
#   "tenant_id": "uuid",
#   "user_id": "uuid",
#   "roles": ["agent", "admin"],
#   "exp": timestamp
# }
```

**Mode 2: API Key Authentication (Selected control-plane flows)**
```python
# Selected control-plane clients
context = PlatformContext(api_key="control-plane-api-key")
await context.registry.register_agent(...)

# API Key metadata:
# {
#   "tenant_id": "uuid",
#   "agent_id": "uuid",
#   "scopes": ["memory:read", "memory:write"]
# }
```

**Migration Plan:**

| Tier | Current (v0.8.x) | v0.9.0+ | v1.0.0 |
|------|-----------------|---------|--------|
| Developer Tenant (Registry) | Bearer JWT | Bearer JWT + optional control-plane API key | Explicitly documented split by route class |
| Client Tenant+User (Memory/Tracker/Event) | Bearer JWT | Bearer JWT with delegated trust | JWT only |

---

## 2. SDK Two-Layer Architecture

### Pattern Overview

Soorma SDK follows a **strict two-layer abstraction** to separate low-level service communication from high-level agent APIs:

```
┌─────────────────────────────────────────────────────────────┐
│                     Agent Handlers                          │
│              (Workers, Planners, Tools)                     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│            Layer 2: PlatformContext Wrappers                │
│                  (High-Level Agent API)                     │
│                                                             │
│  • context.memory  (MemoryClient wrapper)                   │
│  • context.bus     (BusClient wrapper)                      │
│  • context.registry (RegistryClient)                        │
│  • context.tracker (TrackerClient wrapper)                  │
└────────────────────┬────────────────────────────────────────┘
                     │ Delegates via self._client
                     ▼
┌─────────────────────────────────────────────────────────────┐
│            Layer 1: Service Clients                         │
│              (Low-Level HTTP Clients)                       │
│                                                             │
│  • MemoryServiceClient  (soorma.memory.client)              │
│  • EventClient          (soorma.events)                     │
│  • RegistryClient       (soorma.registry.client)            │
│    └─ NOTE: RegistryClient is ALSO the Layer 2 wrapper      │
│       (no separate low-level class for Registry)            │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP/gRPC
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  Backend Services                           │
│         (Memory, Event, Registry, Tracker)                  │
└─────────────────────────────────────────────────────────────┘
```

### Layer 1: Service Clients (Low-Level)

**Purpose:** Direct HTTP/gRPC communication with backend services

**Location:**
- `sdk/python/soorma/memory/client.py` - MemoryServiceClient
- `sdk/python/soorma/events.py` - EventClient
- `sdk/python/soorma/registry/client.py` - RegistryClient (serves as both Layer 1 and Layer 2 for Registry)

**Characteristics:**
- Direct HTTP calls with `httpx`
- Explicit bearer-auth header injection
- Pydantic model serialization/deserialization
- Fine-grained error handling
- **NOT for agent handler use**

**Example:**
```python
# ❌ NEVER use in agent handlers
from soorma.memory.client import MemoryServiceClient

client = MemoryServiceClient(base_url="http://localhost:8083")
result = await client.store_task_context(
    task_id="task-123",
    service_tenant_id="tenant-uuid",  # Manual per-call service tenant
    service_user_id="user-uuid",      # Manual per-call service user
    ...
)
```

### Layer 2: PlatformContext Wrappers (High-Level)

**Purpose:** Agent-friendly API with automatic context management

**Location:**
- `sdk/python/soorma/context.py` - MemoryClient, BusClient, TrackerClient wrappers
- `sdk/python/soorma/registry/client.py` - RegistryClient (already high-level)

**Characteristics:**
- Automatic tenant_id/user_id extraction from event context
- Simplified method signatures
- Delegation to underlying service clients
- **REQUIRED for all agent handlers**

**Example:**
```python
# ✅ CORRECT: Use PlatformContext wrappers
@worker.on_task("research.requested")
async def handle_research(task, context: PlatformContext):
    # Wrapper handles tenant_id/user_id automatically
    await context.memory.store_task_context(
        task_id=task.id,
        plan_id=task.plan_id,
        event_type="research.requested",
        data=task.data,
    )
    
    await context.bus.publish(
        topic="action-requests",
        event_type="search.requested",
        data={"query": task.data["topic"]},
    )
```

### Wrapper Implementation Pattern

All wrappers MUST follow this pattern:

```python
@dataclass
class MemoryClient:
    """High-level Memory Service client wrapper."""
    
    base_url: str = field(default_factory=lambda: os.getenv(...))
    _client: Optional[MemoryServiceClient] = field(default=None, repr=False, init=False)
    
    async def _ensure_client(self) -> MemoryServiceClient:
        """Lazy initialization of underlying service client."""
        if self._client is None:
            self._client = MemoryServiceClient(base_url=self.base_url)
        return self._client
    
    async def store_task_context(
        self,
        task_id: str,
        plan_id: Optional[str],
        event_type: str,
        # Note: NO tenant_id/user_id parameters here
        ...
    ) -> TaskContextResponse:
        """
        Store task context (wrapper delegates to service client).
        
        Tenant/user context extracted from event envelope automatically.
        """
        client = await self._ensure_client()
        return await client.store_task_context(
            task_id=task_id,
            plan_id=plan_id,
            event_type=event_type,
            service_tenant_id=tenant_id,  # Extracted from event context
            service_user_id=user_id,      # Extracted from event context
            ...
        )
```

### Mandatory Rules

1. **Agent Code:** MUST use `context.memory`, `context.bus`, `context.registry` exclusively
2. **Examples:** MUST demonstrate wrapper usage, NEVER import service clients directly
3. **New Service Methods:** MUST have corresponding wrapper methods before use
4. **Wrapper Delegation:** All wrappers delegate to `self._client` after `_ensure_client()`
5. **No Direct Imports:** NEVER `from soorma.memory.client import MemoryServiceClient` in agent code

---

## 3. Event Choreography Patterns

### Event Envelope Structure

All events follow a standardized envelope:

```python
@dataclass
class EventEnvelope:
    event_id: str              # Unique event identifier
    event_type: str            # Event type (e.g., "search.requested")
    correlation_id: str        # For request/response tracking
    trace_id: str              # Distributed tracing root
    parent_event_id: Optional[str]  # Event lineage
    
    # Metadata
    tenant_id: str             # Multi-tenancy isolation
    user_id: str               # User context
    session_id: Optional[str]  # Conversation context
    
    # Payload
    data: Dict[str, Any]       # Event-specific data
    
    # DisCo Pattern
    response_event: Optional[str]  # Expected response event type
    response_topic: Optional[str]  # Response topic (default: action-results)
```

### DisCo Pattern: Explicit Response Events

**Critical Design:** Response events are **explicit**, not inferred.

```python
# ✅ CORRECT: Explicit response_event
@worker.on_task("search.requested")
async def search(task, context: PlatformContext):
    results = await do_search(task.data["query"])
    
    # Use response_event from original request
    await context.bus.respond(
        event_type=task.response_event,  # "search.completed"
        correlation_id=task.correlation_id,
        data={"results": results},
    )

# ❌ WRONG: Never infer response event names
await context.bus.publish(
    event_type="search.succeeded",  # Where did this come from?
    ...
)
```

### Event Topics

Standard topics for event choreography:

- `action-requests`: Task/goal requests from Planners/Workers
- `action-results`: Task completion results
- `business-events`: Domain facts (orders placed, payments completed)
- `system-events`: Platform events (agent registered, service health)

---

## 4. Multi-Tenancy & Data Isolation

> **Two-Tier Model:** See Section 1 (Two-Tier Tenancy) for the distinction between Developer Tenant (Registry) and Client Tenant+User (Memory, Tracker, Event). The patterns below apply to **Tier 2** (client tenant + user) unless explicitly noted.

### Tenant Isolation Strategy

**PostgreSQL Row-Level Security (RLS)** enforces tenant isolation:

```sql
-- All tenant-scoped tables
CREATE TABLE plans (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    ...
);

-- RLS policy
ALTER TABLE plans ENABLE ROW LEVEL SECURITY;

CREATE POLICY plans_tenant_isolation ON plans
    USING (
        tenant_id = current_setting('app.tenant_id')::UUID 
        AND user_id = current_setting('app.user_id')::UUID
    );
```

### Session Variables

Services set PostgreSQL session variables from headers:

```python
# In service middleware/endpoint
async def set_tenant_context(tenant_id: str, user_id: str):
    await db.execute(f"SET app.tenant_id = '{tenant_id}'")
    await db.execute(f"SET app.user_id = '{user_id}'")
```

RLS policies automatically use these variables to filter ALL queries.

### Cross-Tenant Access

Some resources may be shared across tenants (e.g., public knowledge):

```python
# Semantic memory with privacy flag
await context.memory.store_knowledge(
    content="Public best practice",
    metadata={"category": "guidelines"},
    is_public=True,  # Accessible to all users in tenant
)
```

### Admin Boundary and Data Access Separation

When a service exposes operational/admin endpoints, enforce a strict separation between user ownership flows and admin flows.

**User ownership flows:**
- Apply user-context validation at route boundary.
- Pass full identity tuple through service and CRUD layers.
- Use ownership-scoped predicates for read/write operations.

**Admin operational flows:**
- Do not rely on user ownership dependencies by default.
- Require explicit server-side admin authorization checks per endpoint.
- Use dedicated admin service/query paths with explicit scope parameters.

**Non-negotiable rule:** admin endpoints must not silently reuse user-scoped CRUD methods that are designed around caller ownership semantics.

---

## 5. State Management Patterns

### Working Memory (Plan-Scoped)

Temporary state for plan execution:

```python
# Store state for plan
await context.memory.store("vehicle_id", "VIN-12345")

# Retrieve state
vehicle_id = await context.memory.retrieve("vehicle_id")

# Auto-deleted when plan completes
```

### Task Context (Async Worker Pattern)

For long-running tasks with delegations:

```python
@worker.on_task("research.requested")
async def handle_research(task: TaskContext, context: PlatformContext):
    # Save task before delegation
    await task.save()
    
    # Delegate to sub-agent
    sub_task_id = await task.delegate("search.requested", ...)
    
    # Task restored when result arrives
    
@worker.on_result("search.completed")
async def handle_result(result: ResultContext, context: PlatformContext):
    # Restore parent task
    task = await result.restore_task()
    
    # Continue processing
    task.results["search"] = result.data
    await task.complete()
```

### Plan Context (Planner State Machine)

For multi-step workflows:

```python
@planner.on_goal("research.goal")
async def plan_research(goal: GoalContext, context: PlatformContext):
    # Create state machine
    plan = await PlanContext.create_from_goal(
        goal=goal,
        context=context,
        state_machine={...},
        current_state="start",
        status="pending",
    )
    
    # Execute
    await plan.execute_next()

@planner.on_transition()
async def handle_transition(
    event: EventEnvelope,
    context: PlatformContext,
    plan: PlanContext,
    next_state: str,
) -> None:
    """SDK auto-restores plan and validates transition."""
    # Update state
    plan.current_state = next_state
    plan.results[event.type] = event.data
    
    # Execute next state or finalize
    if plan.is_complete():
        await plan.finalize(result=event.data)
    else:
        await plan.execute_next(event)
```

---

## 6. Error Handling Patterns

### Service Client Errors

```python
# Service clients raise HTTPStatusError
try:
    result = await client.get_plan_context(plan_id)
except httpx.HTTPStatusError as e:
    if e.response.status_code == 404:
        return None  # Not found is expected
    elif e.response.status_code == 403:
        raise PermissionError("Access denied")
    else:
        raise  # Re-raise unexpected errors
```

### Wrapper Errors

```python
# Wrappers provide graceful degradation
async def get_task_context(self, task_id: str) -> Optional[TaskContextResponse]:
    """Returns None if not found, raises on unexpected errors."""
    try:
        client = await self._ensure_client()
        return await client.get_task_context(task_id, ...)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return None
        raise
```

### Agent Handler Errors

```python
@worker.on_task("process_payment")
async def process_payment(task, context: PlatformContext):
    try:
        # Business logic
        result = await charge_card(...)
        
        await context.bus.respond(
            event_type=task.response_event,
            data={"status": "success", "result": result},
            correlation_id=task.correlation_id,
        )
    except PaymentError as e:
        # Publish error event
        await context.bus.respond(
            event_type=task.response_event,
            data={"status": "failed", "error": str(e)},
            correlation_id=task.correlation_id,
        )
```

---

## 7. Testing Patterns

### Unit Tests (SDK Components)

```python
# Mock service clients
async def test_memory_wrapper_stores_task():
    # Mock underlying service client
    mock_client = MagicMock()
    mock_client.store_task_context = AsyncMock(return_value=TaskContextResponse(...))
    
    # Test wrapper
    memory = MemoryClient()
    memory._client = mock_client
    
    result = await memory.store_task_context(task_id="task-123", ...)
    
    # Verify delegation
    mock_client.store_task_context.assert_called_once()
```

### Integration Tests (End-to-End)

```python
@pytest.mark.integration
async def test_worker_task_delegation():
    # Real services running
    context = PlatformContext.from_env()
    
    worker = Worker(name="research-worker")
    
    @worker.on_task("research.requested")
    async def handle_research(task, ctx):
        await ctx.memory.store_task_context(...)
        await task.delegate("search.requested", ...)
    
    # Publish task
    await worker.start()
    # ... verify via Memory Service
```

---

## 8. Migration & Versioning

### API Versioning

Services use URL-based versioning:
- `/v1/memory/task-context` - Current stable
- `/v2/memory/task-context` - Future breaking changes

SDK maintains backward compatibility across minor versions.

### Breaking Changes

Follow semantic versioning:
- **Patch (0.7.1):** Bug fixes, no API changes
- **Minor (0.8.0):** New features, backward compatible
- **Major (1.0.0):** Breaking changes requiring migration

### Deprecation Policy

1. **Announce:** Add deprecation warning in docs and code
2. **Grace Period:** Minimum 1 minor version (e.g., 0.8.x -> 0.9.x)
3. **Remove:** Next major version (1.0.0)

Example:
```python
async def old_method(self, ...):
    """
    DEPRECATED: Use new_method() instead.
    Will be removed in v1.0.0.
    """
    warnings.warn("old_method is deprecated", DeprecationWarning)
    return await self.new_method(...)
```

---

## 9. Development Checklist

### Adding a New Service Method

- [ ] Implement endpoint in backend service (e.g., Memory Service)
- [ ] Add method to service client (e.g., MemoryServiceClient)
- [ ] Add wrapper method to PlatformContext layer (e.g., MemoryClient)
- [ ] Verify wrapper delegates correctly
- [ ] Update unit tests for service client
- [ ] Update unit tests for wrapper
- [ ] Update integration tests
- [ ] Update SDK documentation
- [ ] Update CHANGELOG.md

### Adding a New Agent Type

- [ ] Define agent class extending `Agent` base
- [ ] Implement decorators (e.g., `@agent.on_event()`)
- [ ] Implement handler-only event registration (RF-SDK-023)
- [ ] Add agent configuration to Registry Service
- [ ] Create example implementation
- [ ] Add integration test
- [ ] Update agent patterns documentation

---

## 10. References

### Key Documents

- [AGENT.md](../AGENT.md) - Developer constitution
- [ARCHITECTURE.md](../ARCHITECTURE.md) - System architecture overview
- [CONTRIBUTING_REFERENCE.md](CONTRIBUTING_REFERENCE.md) - Development how-to guide
- [DisCo Pattern Docs](agent_patterns/) - Planner/Worker/Tool patterns

### Refactoring Docs

- [Memory Service Architecture](refactoring/arch/02-MEMORY-SERVICE.md)
- [Memory SDK](refactoring/sdk/02-MEMORY-SDK.md)
- [Event System](event_system/)
- [Agent Patterns](agent_patterns/)

### External References

- [CoALA Framework](https://arxiv.org/abs/2309.02427) - Memory architecture
- [Pydantic v2](https://docs.pydantic.dev/latest/) - Data validation
- [FastAPI](https://fastapi.tiangolo.com/) - Service framework

---

**Last Updated:** February 18, 2026  
**Document Owner:** @soorma-core-team  
**Review Cycle:** Updated with each major architectural change
