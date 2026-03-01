# Migration Guide: v0.8.0 → v0.8.1

**Release Date:** February 28, 2026  
**Target:** Schema Registry & DTOs Foundation (Phase 1)  
**Breaking Changes:** YES - AgentCapability structure, database schema

---

## Overview

Version 0.8.1 introduces the Schema Registry foundation for dynamic event type discovery and multi-tenancy support. This release includes **breaking changes** to the AgentCapability structure and database schema.

**Key Changes:**
- Schema Registry DTOs for dynamic event registration
- Enhanced EventDefinition with schema references
- Breaking: AgentCapability now requires EventDefinition objects (not strings)
- Breaking: Database unique constraints now tenant-scoped
- Multi-tenancy columns added to agents and events tables
- Row-Level Security (RLS) policies for tenant isolation

---

## Breaking Changes

### 1. AgentCapability Structure (BREAKING)

**Impact:** All agent registration code must be updated.

#### Old Format (v0.8.0)
```python
from soorma_common import AgentDefinition, AgentCapability

agent = AgentDefinition(
    agent_id="research-worker-001",
    name="Research Worker",
    description="Performs web research tasks",
    capabilities=[
        AgentCapability(
            task_name="web_research",
            description="Performs web research",
            consumed_event="research.requested",  # ❌ String (deprecated)
            produced_events=["research.completed"]  # ❌ String list (deprecated)
        )
    ]
)
```

#### New Format (v0.8.1+)
```python
from soorma_common import AgentDefinition, AgentCapability, EventDefinition

agent = AgentDefinition(
    agent_id="research-worker-001",
    name="Research Worker",
    description="Performs web research tasks",
    version="1.0.0",  # ✅ Required (new field)
    capabilities=[
        AgentCapability(
            task_name="web_research",
            description="Performs web research",
            consumed_event=EventDefinition(  # ✅ EventDefinition object required
                event_name="research.requested",
                topic="action-requests",
                description="Research request event",
                payload_schema_name="research_request_v1"  # ✅ Schema reference
            ),
            produced_events=[  # ✅ List[EventDefinition] required
                EventDefinition(
                    event_name="research.completed",
                    topic="action-results",
                    description="Research completion event",
                    payload_schema_name="research_result_v1"  # ✅ Schema reference
                )
            ]
        )
    ]
)
```

**Validation Error:**
If you try to use strings in v0.8.1+, you'll get a Pydantic ValidationError:
```
ValidationError: 1 validation error for AgentCapability
consumed_event
  Input should be a valid dictionary or instance of EventDefinition [type=model_type, ...]
```

---

### 2. Database Schema Changes (BREAKING)

#### Unique Constraints - Now Tenant-Scoped

**Old (v0.8.0):**
- `agents.agent_id` was globally unique across all tenants
- `events.event_name` was globally unique across all tenants

**New (v0.8.1):**
- `agents.agent_id` is unique within tenant: `(agent_id, tenant_id)`
- `events.event_name` is unique within tenant: `(event_name, tenant_id)`

**Impact:**
- Different tenants can now use the same agent_id or event_name
- True multi-tenancy isolation with independent namespaces
- Example: Tenant A and Tenant B can both have "worker-001"

#### New Required Columns

All tables now require tenant context:

**agents table:**
- `tenant_id` (UUID, required) - Tenant identifier from JWT
- `user_id` (UUID, required) - User identifier from JWT
- `version` (VARCHAR, optional) - Agent version (e.g., "1.0.0")

**events table:**
- `tenant_id` (UUID, required) - Tenant identifier from JWT
- `user_id` (UUID, required) - User identifier from JWT
- `owner_agent_id` (VARCHAR, optional) - Agent that owns this event
- `payload_schema_name` (VARCHAR, optional) - Schema reference
- `response_schema_name` (VARCHAR, optional) - Response schema reference

**Migration Strategy:**
- Migration applies default UUIDs during upgrade: `'00000000-0000-0000-0000-000000000000'`
- After migration, defaults are removed (forces explicit tenant/user context)
- Full rollback support via `alembic downgrade -1`

---

## Migration Steps

### Step 1: Update Dependencies

```bash
# Update soorma-common library
pip install --upgrade soorma-common==0.8.1
```

### Step 2: Run Database Migration

```bash
# Navigate to registry service
cd services/registry

# Backup database (production only)
pg_dump -U postgres registry > registry_backup_$(date +%Y%m%d).sql

# Run migration
alembic upgrade head

# Verify migration
psql -U postgres registry -c "\d payload_schemas"
psql -U postgres registry -c "\d agents"
psql -U postgres registry -c "\d events"
```

**Expected Output:**
```
INFO  [alembic.runtime.migration] Running upgrade 002_composite_key -> 003_schema_registry
INFO  [alembic.runtime.migration] Applied migration 003_schema_registry
```

**Rollback (if needed):**
```bash
alembic downgrade -1
```

### Step 3: Update Agent Registration Code

Update all agent registration code to use EventDefinition objects.

**Files to Update:**
- All example directories: `examples/01-hello-world/` through `examples/10-planner-tracker/`
- Your agent implementations (workers, planners, tools)
- Any custom agent registration logic

**Template:**
```python
from soorma_common import AgentDefinition, AgentCapability, EventDefinition

# Define consumed event
consumed_event = EventDefinition(
    event_name="task.requested",
    topic="action-requests",
    description="Task request event",
    payload_schema_name="task_request_v1"  # Reference to registered schema
)

# Define produced events
produced_events = [
    EventDefinition(
        event_name="task.completed",
        topic="action-results",
        description="Task completion event",
        payload_schema_name="task_result_v1"
    ),
    EventDefinition(
        event_name="task.failed",
        topic="action-results",
        description="Task failure event",
        payload_schema_name="task_error_v1"
    )
]

# Create capability
capability = AgentCapability(
    task_name="process_task",
    description="Processes tasks",
    consumed_event=consumed_event,
    produced_events=produced_events
)

# Register agent
agent = AgentDefinition(
    agent_id="worker-001",
    name="Task Worker",
    description="Processes tasks",
    version="1.0.0",
    capabilities=[capability]
)
```

### Step 4: Verify Changes

```bash
# Run tests
cd libs/soorma-common
pytest tests/test_registry_dtos.py -v

# Expected: 22/22 tests passing
```

**Run examples:**
```bash
# Test each example
cd examples/01-hello-world
python agent.py

# Verify no ValidationError exceptions
```

---

## New Features

### 1. Schema Registry DTOs

You can now register payload schemas dynamically:

```python
from soorma_common import PayloadSchemaRegistration

schema_registration = PayloadSchemaRegistration(
    schema_name="research_request_v1",
    version="1.0.0",
    json_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "max_results": {"type": "integer", "default": 10}
        },
        "required": ["query"]
    },
    description="Research request payload schema"
)

# Note: Service endpoints for registration will be added in Phase 2
```

### 2. Enhanced EventDefinition

EventDefinition now supports schema references:

```python
event = EventDefinition(
    event_name="research.requested",
    topic="action-requests",
    description="Research request event",
    payload_schema_name="research_request_v1",  # ✅ NEW: Schema reference
    response_schema_name="research_result_v1"   # ✅ NEW: Response schema
)
```

**Backward Compatibility:**
Old embedded schema fields are deprecated but still supported:
```python
event = EventDefinition(
    event_name="research.requested",
    topic="action-requests",
    description="Research request event",
    payload_schema={"type": "object"},  # ⚠️ Deprecated (will be removed in v1.0.0)
    response_schema={"type": "object"}  # ⚠️ Deprecated (will be removed in v1.0.0)
)
```

### 3. DiscoveredAgent Helper Methods

When querying discovered agents:

```python
from soorma_common import DiscoveredAgent

# Get agent from discovery
agent: DiscoveredAgent = ...

# Extract consumed schema names
consumed_schemas = agent.get_consumed_schemas()
# Returns: ["research_request_v1", "task_request_v1"]

# Extract produced schema names
produced_schemas = agent.get_produced_schemas()
# Returns: ["research_result_v1", "task_result_v1"]
```

---

## Row-Level Security (RLS)

The database now enforces tenant isolation at the PostgreSQL level.

### How It Works

1. **Authentication Context:**
   - Service middleware extracts `tenant_id` and `user_id` from JWT/API Key headers
   - Sets PostgreSQL session variables: `app.tenant_id`, `app.user_id`

2. **RLS Policies:**
   - **Read Policy:** `WHERE tenant_id = current_setting('app.tenant_id')::UUID`
   - **Write Policy:** `WHERE tenant_id = current_setting('app.tenant_id')::UUID AND user_id = current_setting('app.user_id')::UUID`

3. **Query Isolation:**
   - All queries automatically filtered by tenant_id
   - Cross-tenant queries blocked at database level
   - No application-level filtering needed

### Performance Optimization

Composite indexes match RLS query patterns:

```sql
-- RLS queries filter by tenant_id first, then by other criteria
CREATE INDEX idx_payload_schemas_tenant_schema ON payload_schemas(tenant_id, schema_name);
CREATE INDEX idx_agents_tenant_agent ON agents(tenant_id, agent_id);
CREATE INDEX idx_events_tenant_event ON events(tenant_id, event_name);
```

**Query Pattern:**
```sql
-- This query is optimized by composite index
SELECT * FROM agents 
WHERE tenant_id = '...' AND agent_id = 'worker-001';
```

---

## Troubleshooting

### ValidationError: consumed_event must be EventDefinition

**Error:**
```
ValidationError: 1 validation error for AgentCapability
consumed_event
  Input should be a valid dictionary or instance of EventDefinition
```

**Solution:**
Update your code to use EventDefinition objects instead of strings (see Step 3 above).

### Migration Fails: "column already exists"

**Error:**
```
psql error: column "tenant_id" of relation "agents" already exists
```

**Solution:**
You may have partially applied the migration. Rollback and retry:
```bash
alembic downgrade -1
alembic upgrade head
```

### RLS Policy Blocks Query

**Error:**
```
psql error: new row violates row-level security policy for table "agents"
```

**Solution:**
Ensure your service middleware sets session variables:
```python
await conn.execute(text("SET app.tenant_id = :tenant_id"), {"tenant_id": tenant_id})
await conn.execute(text("SET app.user_id = :user_id"), {"user_id": user_id})
```

---

## FAQ

**Q: Can I skip this migration and stay on v0.8.0?**  
A: No. v0.8.1 is a required upgrade for the Schema Registry system (Stage 5 goals). All future features depend on this foundation.

**Q: Why were strings deprecated in AgentCapability?**  
A: Pre-launch phase allows clean architectural breaks. Structured EventDefinition objects enable rich metadata for discovery, validation, and A2A protocol compatibility.

**Q: Will different tenants' agents conflict if they use the same agent_id?**  
A: No. Unique constraints are now tenant-scoped: `(agent_id, tenant_id)`. Each tenant has an independent namespace.

**Q: Do I need to update all 10 examples?**  
A: Yes (Day 4 of Phase 1). Examples serve as live documentation and must work after the breaking changes.

**Q: What happens to existing data during migration?**  
A: Migration adds default UUIDs (`'00000000-0000-0000-0000-000000000000'`) for tenant_id/user_id. After migration, you must re-register agents with valid authentication context.

**Q: Can I test the migration locally?**  
A: Yes. Use `alembic upgrade head` and `alembic downgrade -1` with SQLite or PostgreSQL. Full rollback support is included.

---

## Support

**Documentation:**
- [ACTION_PLAN_Phase1_Foundation.md](plans/ACTION_PLAN_Phase1_Foundation.md) - Detailed implementation plan
- [ARCHITECTURE_PATTERNS.md](../ARCHITECTURE_PATTERNS.md) - Authentication and RLS patterns

**Related Refactoring Tasks:**
- RF-ARCH-005: Schema registration by name (foundation)
- RF-ARCH-006: Structured capabilities with EventDefinition (DTOs)

**Questions?**
Check the action plan or consult the Soorma Core team.

---

**Last Updated:** March 1, 2026  
**Version:** 0.8.2  
**Author:** Soorma Core Team

---

## v0.8.2 Addendum — Schema Registry Endpoints & Agent Discovery

**Released:** March 1, 2026 | **Phase 2 of Enhanced Discovery**

### New Endpoints (No Breaking Changes)

All endpoints are additive. Existing code does not require changes; authentication pattern is unchanged (`X-Tenant-ID` header).

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/v1/schemas` | Register a payload schema |
| `GET` | `/v1/schemas/{name}` | Get latest version of a schema |
| `GET` | `/v1/schemas/{name}/versions/{version}` | Get specific schema version |
| `GET` | `/v1/schemas` | List schemas (optional `?owner_agent_id=`) |
| `GET` | `/v1/agents/discover` | Discover active agents (optional `?consumed_event=`) |

### Register a Schema

```python
from soorma_common import PayloadSchema

schema = PayloadSchema(
    schema_name="research_request_v1",
    version="1.0.0",
    json_schema={
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"]
    },
    description="Research task request payload",
    owner_agent_id="research-planner-001",
)
response = await context.registry.register_schema(schema)
# PayloadSchemaResponse(schema_name="research_request_v1", version="1.0.0", success=True, ...)
```

**Duplicate behavior:** Registering the same `(schema_name, version)` pair twice returns `409 Conflict`. Schemas are immutable once registered (Decision D1).

### Discover Agents

```python
# Discover all active agents that consume "research.requested"
agents: List[AgentDefinition] = await context.registry.discover_agents(
    consumed_event="research.requested"
)

# Discover all active agents (no filter)
all_agents = await context.registry.discover_agents()
```

Expired agents (beyond TTL) are excluded automatically.

### SDK Methods Added

```python
# In agent handlers via context.registry:
await context.registry.register_schema(schema)           # Register
await context.registry.get_schema("research_request_v1") # Get latest
await context.registry.get_schema("research_request_v1", "1.0.0")  # Get specific
await context.registry.list_schemas(owner_agent_id="planner-001")   # List by owner
await context.registry.discover_agents(consumed_event="my.event")   # Discover
```


