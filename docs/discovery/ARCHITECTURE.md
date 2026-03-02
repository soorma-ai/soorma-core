# Discovery: Technical Architecture

**Status:** 🟢 Implementation In Progress (Phases 1 & 2 ✅, Phase 3 📋 Planning, Phase 4 📋 Planning)  
**Last Updated:** March 1, 2026  
**Stage Progress:** RF-ARCH-005 ✅ | RF-ARCH-006 ✅ | RF-ARCH-007 ✅ | RF-SDK-008 📋 | RF-SDK-017 📋 | TECH-DEBT-001 📋

### Phase Progress

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 1 | Foundation — DTOs, DB Schema, RLS, Alembic migrations | ✅ Complete |
| Phase 2 | Service — Schema endpoints, Discovery endpoint, multi-tenancy middleware | ✅ Complete |
| Phase 3 | SDK — `discover()`, `EventSelector`, `A2AGatewayHelper` | 📋 [Plan](plans/ACTION_PLAN_Phase3_SDK_Implementation.md) |
| Phase 4 | Tracker NATS integration — `soorma-nats` lib, remove SDK from Tracker | 📋 [Plan](plans/ACTION_PLAN_Phase4_Tracker_NATS_Integration.md) |
| Phase 5 | Examples 11–13, full documentation | ⬜ Not started |

---

## Executive Summary

The Discovery System provides dynamic agent and capability discovery through the **Registry Service**. It enables:
- Event and agent metadata registration
- Capability-based agent discovery
- Schema lookup for LLM-based payload generation
- Agent health monitoring via heartbeat TTL

**Current Status:**
- ✅ Basic Registry Service operational (Stages 0-3)
- ✅ **Phase 1 complete:** `PayloadSchema` DTOs, `payload_schemas` table, RLS policies on `agents`, `events`, and `payload_schemas` tables, Alembic migration 003
- ✅ **Phase 2 complete:** Schema CRUD endpoints, `GET /v1/agents/discover`, multi-tenancy middleware, `RegistryClient` schema methods
- 📋 **Phase 3 in planning:** `discover() -> List[DiscoveredAgent]`, `EventSelector`, `A2AGatewayHelper`

---

## Design Principles

### Service Discovery

**Philosophy:** Agents discover each other dynamically rather than hardcode dependencies.

**Benefits:**
- **Loose coupling:** Add/remove agents without code changes
- **Scalability:** New agent instances register automatically
- **Resilience:** Health monitoring detects failed agents

### Capability-Based Routing

**Philosophy:** Route events based on capabilities, not hardcoded agent IDs.

**Benefits:**
- **Flexibility:** Multiple agents can provide same capability
- **Load balancing:** Registry returns all instances, caller chooses
- **Version management:** Different agent versions coexist

### A2A Integration (Stage 5)

**Philosophy:** Enable Agent-to-Agent (A2A) delegation with schema-based discovery.

**Benefits:**
- **LLM-driven:** Agents use LLM to select best capability
- **Schema-aware:** Full JSON schemas guide payload generation
- **Validated:** Registry validates agent capabilities

---

## Registry Service Architecture

### Tech Stack

- **Framework:** FastAPI
- **Database:** SQLite (local testing) or PostgreSQL (production)
- **ORM:** SQLAlchemy async
- **Background Tasks:** asyncio for TTL cleanup

### Core Components (Current — Phases 1 & 2)

```
services/registry/
├── src/registry_service/
│   ├── api/v1/                  # REST endpoints
│   │   ├── agents.py            # Registration, query, heartbeat, discover
│   │   ├── events.py            # Event registration, query
│   │   └── schemas.py           # NEW (Phase 2): Schema CRUD endpoints
│   ├── services/
│   │   ├── agent_service.py     # Agent business logic + discover_agents()
│   │   ├── event_service.py     # Event business logic
│   │   └── schema_service.py    # NEW (Phase 2): Schema CRUD business logic
│   ├── middleware/
│   │   └── tenant.py            # NEW (Phase 2): X-Tenant-ID extraction + RLS session vars
│   ├── models/
│   │   ├── agent.py             # Agent DB model (+ developer tenant_id, version columns)
│   │   ├── event.py             # Event DB model (+ developer tenant_id, owner_agent_id)
│   │   └── schema.py            # NEW (Phase 1): PayloadSchema DB model
│   ├── core/
│   └── main.py
└── migrations/              # Alembic migrations 001–003

libs/soorma-common/
└── models.py                # PayloadSchema, DiscoveredAgent, AgentCapability (EventDefinition)

libs/soorma-nats/            # COMING Phase 4: shared NATS client for infrastructure services
└── src/soorma_nats/
    ├── client.py            # NATSClient (connect, subscribe, disconnect)
    └── exceptions.py        # NATSConnectionError, NATSSubscriptionError

sdk/python/soorma/
├── registry/client.py       # RegistryClient (register_schema, get_schema, discover_agents)
├── ai/event_toolkit.py      # EventToolkit (discover_events, format_for_llm) — reused by Phase 3
├── ai/selection.py          # COMING Phase 3: EventSelector
└── gateway.py               # COMING Phase 3: A2AGatewayHelper
```

---

## Database Schema (Current — Post Phase 1 & 2)

### Agents Table (updated in Phase 1)

```sql
CREATE TABLE agents (
    id UUID PRIMARY KEY,
    agent_id VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    capabilities JSONB NOT NULL DEFAULT '[]',
    status VARCHAR(50) DEFAULT 'active',
    last_heartbeat TIMESTAMPTZ DEFAULT NOW(),
    -- Added Phase 1 (developer tenant isolation — no user_id):
    tenant_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000',
    -- NOTE: No user_id — Registry is scoped to the *developer tenant* only.
    -- The developer tenant UUID comes from SOORMA_DEVELOPER_TENANT_ID (env var)
    -- or a future Developer API Key. It is NOT an end-user or client tenant ID.
    version VARCHAR(50) NOT NULL DEFAULT '1.0.0',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS policies (Phase 1): developer tenant isolation only
ALTER TABLE agents ENABLE ROW LEVEL SECURITY;
CREATE POLICY agents_tenant_isolation ON agents
    USING (tenant_id = current_setting('app.tenant_id')::UUID);
-- (app.tenant_id is set from the X-Tenant-ID header, which carries the developer tenant UUID)

CREATE INDEX agents_agent_id_idx ON agents (agent_id);
CREATE INDEX agents_last_heartbeat_idx ON agents (last_heartbeat);
```

**Capability Structure (Current):**

```json
{
    "taskName": "web_research",
    "description": "Performs web research",
    "consumedEvent": "web.research.requested",
    "producedEvents": ["research.completed"]
}
```

### Events Table

```sql
CREATE TABLE events (
    id UUID PRIMARY KEY,
    event_name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    schema JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX events_event_name_idx ON events (event_name);
```

---

### Payload Schemas Table (New — Phase 1)

```sql
CREATE TABLE payload_schemas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    schema_name VARCHAR(255) NOT NULL,
    version VARCHAR(50) NOT NULL,
    json_schema JSONB NOT NULL,
    description TEXT,
    owner_agent_id VARCHAR(255),               -- References agents.agent_id (no FK constraint)
    tenant_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000',
    -- NOTE: No user_id — schemas are scoped to the *developer tenant* only.
    -- Uniqueness and RLS use only tenant_id (developer UUID).
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (schema_name, version, tenant_id)   -- Developer-tenant-scoped uniqueness
);

ALTER TABLE payload_schemas ENABLE ROW LEVEL SECURITY;
CREATE POLICY schemas_tenant_isolation ON payload_schemas
    USING (tenant_id = current_setting('app.tenant_id')::UUID);
-- (app.tenant_id is set from X-Tenant-ID header carrying the developer tenant UUID)
```

---

## SDK Layer Architecture (v0.8.1)

Reference: ARCHITECTURE_PATTERNS.md Section 1 (Two-Tier Tenancy) and Section 2 (Two-Layer SDK).

**Tenancy model:** Registry Service uses **Tier 1 — Developer Tenant** isolation only. It does NOT carry client tenant or user context. The developer tenant UUID (`SOORMA_DEVELOPER_TENANT_ID`) identifies *who built the agents*, not *whose data is being processed*.

```
Agent Startup Code
    ↓ context.registry.*
RegistryClient  (sdk/python/soorma/registry/client.py)
    ↓ HTTP + X-Tenant-ID: <developer_tenant_uuid>   (NO X-User-ID)
Registry Service (FastAPI)
    ↓ tenant middleware: SET app.tenant_id = developer_tenant_uuid
PostgreSQL + RLS (developer tenant isolation only)
```

**Contrast with Memory/Tracker (Tier 2 — Client Tenant + User):**
```
Agent Handler  (processing an end-user's request)
    ↓ context.memory.*
MemoryClient wrapper  (context.py)
    ↓ HTTP + X-Tenant-ID: <client_tenant_uuid> + X-User-ID: <user_uuid>
Memory Service (FastAPI)
    ↓ middleware: SET app.tenant_id = client_tenant_uuid, SET app.user_id = user_uuid
PostgreSQL + RLS (client tenant + user isolation)
```

**Key design:** `RegistryClient` IS the agent-facing wrapper. There is no separate low-level service client class. `PlatformContext.registry` is initialized as `RegistryClient(base_url=...)` directly.

### Current `RegistryClient` Methods (Phase 2)

| Method | Endpoint | Status |
|--------|----------|--------|
| `register_event(event)` | `POST /v1/events` | ✅ |
| `get_event(name)` | `GET /v1/events?event_name=` | ✅ |
| `get_events_by_topic(topic)` | `GET /v1/events?topic=` | ✅ |
| `register_agent(agent)` | `POST /v1/agents` | ✅ |
| `get_agent(agent_id)` | `GET /v1/agents?agent_id=` | ✅ |
| `query_agents(...)` | `GET /v1/agents` | ✅ |
| `deregister_agent(agent_id)` | `DELETE /v1/agents/{id}` | ✅ |
| `refresh_heartbeat(agent_id)` | `PUT /v1/agents/{id}/heartbeat` | ✅ |
| `register_schema(schema)` | `POST /v1/schemas` | ✅ Phase 2 |
| `get_schema(name, version)` | `GET /v1/schemas/{name}[/versions/{ver}]` | ✅ Phase 2 |
| `list_schemas(owner_agent_id)` | `GET /v1/schemas` | ✅ Phase 2 |
| `discover_agents(consumed_event)` | `GET /v1/agents/discover` | ✅ Phase 2 (⚠️ returns `List[AgentDefinition]`) |
| `discover(requirements, include_schemas)` | `GET /v1/agents/discover` | 📋 Phase 3 (returns `List[DiscoveredAgent]`) |


**Purpose:** Decouple schemas from event names for dynamic event types.

```sql
CREATE TABLE payload_schemas (
    id UUID PRIMARY KEY,
    schema_name VARCHAR(255) NOT NULL,
    version VARCHAR(50) NOT NULL,
    json_schema JSONB NOT NULL,
    owner_agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(schema_name, version)
);

-- Update events table
ALTER TABLE events ADD COLUMN owner_agent_id UUID REFERENCES agents(id) ON DELETE SET NULL;
ALTER TABLE events DROP CONSTRAINT events_event_name_key;
ALTER TABLE events ADD CONSTRAINT events_name_owner_unique UNIQUE(event_name, owner_agent_id);
```

**Rationale:** Dynamic `response_event` names require schemas to be referenced independently of event type.

### Structured Capabilities (RF-ARCH-006)

**Updated Capability Structure:**

```json
{
    "task_name": "web_research",
    "description": "Performs web research on a given topic",
    "consumed_event": {
        "event_type": "web.research.requested",
        "payload_schema_name": "research_request_v1",
        "description": "Request for web research",
        "examples": [{"topic": "AI trends", "max_results": 10}]
    },
    "produced_events": [
        {
            "event_type": "research.completed",
            "payload_schema_name": "research_result_v1",
            "description": "Research results with findings array"
        }
    ]
}
```

**Benefits:** Full schema information embedded in capability for LLM reasoning.

---

## API Specification

### Current Endpoints (Stages 0-3)

#### Agent Registration

```http
POST /api/v1/agents
Content-Type: application/json

{
    "agent": {
        "agentId": "research-worker-v1",
        "name": "Research Worker",
        "description": "Performs web research",
        "capabilities": [
            {
                "taskName": "web_research",
                "description": "Web research capability",
                "consumedEvent": "web.research.requested",
                "producedEvents": ["research.completed"]
            }
        ]
    }
}

Response: 201 Created
{
    "message": "Agent registered successfully",
    "agent_id": "research-worker-v1"
}
```

#### Agent Query

```http
GET /api/v1/agents?capability=web_research

Response: 200 OK
{
    "agents": [
        {
            "agentId": "research-worker-v1",
            "name": "Research Worker",
            "capabilities": [...],
            "lastHeartbeat": "2026-02-15T10:30:00Z"
        }
    ]
}
```

#### Heartbeat

```http
PUT /api/v1/agents/research-worker-v1/heartbeat

Response: 200 OK
{
    "message": "Heartbeat updated",
    "last_heartbeat": "2026-02-15T10:35:00Z"
}
```

#### Event Registration

```http
POST /api/v1/events
Content-Type: application/json

{
    "event": {
        "eventName": "web.research.requested",
        "description": "Request for web research",
        "schema": {
            "topic": "string",
            "max_results": "integer"
        }
    }
}

Response: 201 Created
{
    "message": "Event registered successfully"
}
```

### Stage 5 Endpoints (Planned)

#### Schema Registration (RF-ARCH-005)

```http
POST /v1/schemas
Content-Type: application/json

{
    "schema_name": "research_request_v1",
    "version": "1.0",
    "json_schema": {
        "type": "object",
        "properties": {
            "topic": {"type": "string"},
            "max_results": {"type": "integer"}
        },
        "required": ["topic"]
    },
    "owner_agent_id": "research-worker-v1",
    "description": "Schema for web research requests"
}

Response: 201 Created
{
    "message": "Schema registered successfully",
    "schema_name": "research_request_v1"
}
```

#### Schema Lookup

```http
GET /v1/schemas/research_request_v1

Response: 200 OK
{
    "schema_name": "research_request_v1",
    "version": "1.0",
    "json_schema": {...},
    "description": "Schema for web research requests"
}
```

#### Enhanced Discovery (RF-ARCH-007)

```http
GET /v1/agents/discover?capabilities=web_search&include_events=true

Response: 200 OK
{
    "agents": [
        {
            "agent_id": "research-worker-v1",
            "name": "Research Worker",
            "capabilities": [
                {
                    "task_name": "web_research",
                    "consumed_event": {
                        "event_type": "web.research.requested",
                        "payload_schema_name": "research_request_v1",
                        "examples": [...]
                    },
                    "produced_events": [...]
                }
            ]
        }
    ]
}
```

---

## Agent Health Monitoring

### TTL-Based Lifecycle

**Mechanism:** Agents must send heartbeat within TTL window or be marked stale.

**Configuration:**
- `AGENT_TTL_SECONDS`: 300 (5 minutes)
- `AGENT_CLEANUP_INTERVAL_SECONDS`: 60 (1 minute)

**Implementation:**

```python
# services/registry/src/registry_service/main.py

async def cleanup_stale_agents():
    """Background task: Remove stale agents."""
    while True:
        try:
            async with AsyncSessionLocal() as db:
                cutoff = datetime.now() - timedelta(seconds=AGENT_TTL_SECONDS)
                await db.execute(
                    delete(Agent).where(Agent.last_heartbeat < cutoff)
                )
                await db.commit()
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
        
        await asyncio.sleep(AGENT_CLEANUP_INTERVAL_SECONDS)

# Start background task on app startup
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(cleanup_stale_agents())
```

### Deduplication Strategy

**Behavior:** Query returns only most recently active instance per agent type.

**SQL Logic:**

```sql
SELECT DISTINCT ON (agent_id) *
FROM agents
WHERE status = 'active'
ORDER BY agent_id, last_heartbeat DESC
```

**Rationale:** Prevents showing multiple stale instances of same agent.

---

## SDK RegistryClient (Planned - RF-SDK-015)

### Auto-Registration

```python
from soorma import PlatformContext

async with PlatformContext() as context:
    # Auto-register on startup
    await context.registry.register_agent(
        agent_id="my-agent-v1",
        name="My Agent",
        capabilities=[...]
    )
    
    # Start heartbeat loop
    context.registry.start_heartbeat_loop(interval=60)
```

### Discovery Queries

```python
# Query by capability
agents = await context.registry.query_agents(capabilities=["web_research"])

# Get event schema (Stage 5)
schema = await context.registry.get_schema("research_request_v1")
```

### A2A Gateway (Stage 5)

```python
# Publish A2AAgentCard
await context.registry.publish_agent_card(
    agent_id="my-agent",
    capabilities=[...],
    endpoints={"http": "https://my-agent.example.com/api"}
)
```

---

## EventSelector Utility (RF-SDK-017)

**Purpose:** LLM-driven event selection from Registry.

**Planned Implementation:**

```python
from soorma.discovery import EventSelector

selector = EventSelector(
    registry_client=context.registry,
    llm_client=context.llm
)

# LLM selects best event for task
selection = await selector.select_event(
    goal_description="Perform web research on AI trends",
    capabilities=["web_research", "academic_search"]
)

# Returns EventSelection with:
# - event_type: Selected event type
# - suggested_payload: LLM-generated payload
# - agent_id: Discovered agent ID
```

**Workflow:**
1. Query Registry for all agents with matching capabilities
2. Build LLM prompt with agent descriptions and schemas
3. LLM selects best match and generates payload
4. Validate selection against Registry
5. Return EventSelection object

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./registry.db` | Async database URL |
| `SYNC_DATABASE_URL` | (derived) | Sync URL for Alembic |
| `AGENT_TTL_SECONDS` | `300` | Agent registration TTL (5 min) |
| `AGENT_CLEANUP_INTERVAL_SECONDS` | `60` | Background cleanup interval |
| `IS_LOCAL_TESTING` | `true` | Use SQLite for local dev |
| `IS_PROD` | `false` | Production mode (disables docs) |

---

## Performance Characteristics

### Throughput

- **Agent registration:** ~100 req/sec (database bottleneck)
- **Query:** ~500 req/sec (indexed lookups)
- **Heartbeat:** ~200 req/sec (UPDATE queries)

### Scalability

- **Horizontal:** Add read replicas for queries
- **Vertical:** PostgreSQL scales to millions of agents
- **Caching:** Future enhancement (Redis for hot queries)

### Reliability

- **TTL Cleanup:** Automatic stale agent removal
- **Database Redundancy:** PostgreSQL replication
- **Health Checks:** `/health` endpoint for monitoring

---

## Architectural Design Decisions

### 1. SQLite for Local Testing

**Decision:** Support SQLite as default for local development.

**Rationale:**
- Zero infrastructure setup
- Fast test execution
- Production uses PostgreSQL

### 2. Heartbeat TTL (No Manual Deregistration)

**Decision:** Agents don't explicitly deregister; TTL expires stale registrations.

**Rationale:**
- Handles crashes gracefully (agent can't deregister if crashed)
- Simpler lifecycle management
- Self-healing registry

### 3. Capability-Based Discovery (Not Event-Type-Based)

**Decision:** Query by capability name, not event type.

**Rationale:**
- Capabilities are human-readable ("web_research" vs "web.research.requested")
- Multiple agents can share same capability
- Event types may be dynamic (Stage 5)

### 4. Schema Decoupling (Stage 5)

**Decision:** Store schemas by name, not event type.

**Rationale:**
- Dynamic `response_event` names require independent schema lookup
- Schema versioning without changing event names
- Reuse schemas across multiple event types

---

## Implementation Status

### Completed

- ✅ Registry Service operational (Stages 0-3)
- ✅ Agent/Event registration endpoints
- ✅ Heartbeat TTL and cleanup
- ✅ Basic query API by capability
- ✅ Agent deduplication
- ✅ **Phase 1:** `PayloadSchema` DTO + `payload_schemas` table + Alembic migration 003
- ✅ **Phase 1:** `AgentCapability` with `EventDefinition` objects (RF-ARCH-006 DTOs)
- ✅ **Phase 1:** RLS policies on `agents`, `events`, `payload_schemas` tables
- ✅ **Phase 2:** `POST /v1/schemas`, `GET /v1/schemas/{name}`, `GET /v1/schemas/{name}/versions/{ver}` (RF-ARCH-005)
- ✅ **Phase 2:** `GET /v1/agents/discover` capability-based discovery (RF-ARCH-007)
- ✅ **Phase 2:** Multi-tenancy middleware (X-Tenant-ID → PostgreSQL session vars)
- ✅ **Phase 2:** `RegistryClient.register_schema()`, `get_schema()`, `list_schemas()`, `discover_agents()`

### In Progress

- 📋 **Phase 3:** `RegistryClient.discover()` returning `List[DiscoveredAgent]` (RF-SDK-008)
- 📋 **Phase 3:** `EventDecision` DTO in `soorma_common.decisions`
- 📋 **Phase 3:** `EventSelector` utility (RF-SDK-017) — `sdk/python/soorma/ai/selection.py`
- 📋 **Phase 3:** `A2AGatewayHelper` — `sdk/python/soorma/gateway.py`
- 📋 **Phase 3:** 40+ SDK unit tests
- 📋 **Phase 4:** Tracker Service NATS direct integration (TECH-DEBT-001) — [Plan](plans/ACTION_PLAN_Phase4_Tracker_NATS_Integration.md)
- 📋 **Phase 4:** `libs/soorma-nats/` shared NATS client library (v0.1.0)

### Not Started

- ⬜ Phase 5: Example 11 (LLM-based discovery)
- ⬜ Phase 5: Example 12 (EventSelector routing)
- ⬜ Phase 5: Example 13 (A2A Gateway)
- ⬜ Phase 5: End-to-end integration tests

---

## Related Documentation

- [README.md](./README.md) - User guide and patterns
- [Registry Service](../../services/registry/README.md) - Service implementation
- [Refactoring Plan](../refactoring/arch/05-REGISTRY-SERVICE.md) - Stage 5 design decisions
- [Event System](../event_system/ARCHITECTURE.md) - Event-driven choreography
