# Service Discovery: User Guide

**Status:** 🟢 Implementation In Progress (Phase 4 📋 Planning)
**Last Updated:** March 1, 2026  
**Stage Progress:** Phase 1 ✅ | Phase 2 ✅ | Phase 3 📋 | Phase 4 📋

### Phase Status

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 1 | Foundation - DTOs, Database, RLS | ✅ Complete (50 tests passing) |
| Phase 2 | Service Implementation - Schema & Discovery endpoints | ✅ Complete (80 tests passing) |
| Phase 3 | SDK Methods, EventSelector, A2A Gateway | ✅ Complete — [ACTION_PLAN_Phase3](plans/ACTION_PLAN_Phase3_SDK_Implementation.md) |
| Phase 4 | Tracker NATS Integration | � In Progress — [ACTION_PLAN_Phase4](plans/ACTION_PLAN_Phase4_Tracker_NATS_Integration.md) |
| Phase 5 | Examples & Documentation | ⬜ Not started |

---

## Overview

The Discovery System enables **dynamic agent discovery** and **capability-based communication** in Soorma Core. It provides:

- **Event Registry:** Register and query event definitions with schemas
- **Agent Registry:** Register and query agent definitions with capabilities
- **Discovery API:** Find agents by capability for LLM-based delegation

**Current Implementation:**
- ✅ Basic Registry Service operational with Event and Agent registration
- ✅ Schema Registry implemented (`POST/GET /v1/schemas`)
- ✅ Enhanced agent discovery endpoint (`GET /v1/agents/discover`)
- ✅ `AgentCapability` with structured `EventDefinition` objects (breaking change in v0.8.1)
- ✅ PostgreSQL RLS enforcing multi-tenant isolation
- 📋 `context.registry.discover()` returning `List[DiscoveredAgent]` (Phase 3)
- 📋 `EventSelector` utility for LLM-based routing (Phase 3)
- 📋 `A2AGatewayHelper` for external protocol conversion (Phase 3)

---

## Core Concepts

### How Agents Find Each Other

In event-driven choreography, agents don't call each other directly. Instead, they:
1. **Publish events** to topics
2. **Subscribe to event types** they can handle
3. **Discover capabilities** via Registry Service

**Discovery Methods:**
- **Static:** Hardcoded event names (simple, but inflexible)
- **Dynamic:** Query Registry at runtime (flexible, scales)
- **LLM-based:** EventSelector utility (intelligent selection)

### Registration

Agents register at startup, declaring:
- **Identity:** agent_id, name, description
- **Capabilities:** What tasks they can perform
- **Events:** Consumed and produced event types
- **Schemas:** Payload structure for each event

### Capability Declaration

A capability describes:
- **Task name:** Human-readable identifier (e.g., "web_research")
- **Description:** What the agent does
- **Consumed event:** Event type the agent listens for
- **Produced events:** Event types the agent publishes
- **Examples:** Sample payloads for LLM guidance

---

## Current API (v0.8.1 — Phases 1 & 2 Complete)

### Agent Registration (Breaking Change in v0.8.1)

```python
from soorma import PlatformContext
from soorma_common import AgentDefinition, AgentCapability, EventDefinition

async with PlatformContext() as context:
    # v0.8.1: capabilities use EventDefinition objects (not strings)
    await context.registry.register_agent(
        AgentDefinition(
            agent_id="research-worker-001",
            name="Research Worker",
            description="Performs web research",
            capabilities=[
                AgentCapability(
                    task_name="web_research",
                    description="Web research capability",
                    consumed_event=EventDefinition(
                        event_name="web.research.requested",
                        topic="action-requests",
                        description="Research request",
                        payload_schema_name="research_request_v1",  # Schema reference
                    ),
                    produced_events=[
                        EventDefinition(
                            event_name="research.completed",
                            topic="action-results",
                            description="Research results",
                        )
                    ],
                )
            ],
        )
    )
```

### Schema Registration (New in v0.8.1)

```python
from soorma_common import PayloadSchema

# Register payload schema
schema = PayloadSchema(
    schema_name="research_request_v1",
    version="1.0.0",
    json_schema={
        "type": "object",
        "properties": {
            "topic": {"type": "string"},
            "max_results": {"type": "integer"},
        },
        "required": ["topic"],
    },
    description="Schema for web research requests",
)
await context.registry.register_schema(schema)

# Retrieve schema by name
schema = await context.registry.get_schema("research_request_v1")
schema_v1 = await context.registry.get_schema("research_request_v1", version="1.0.0")
```

### Agent Discovery (Phase 3 — coming soon)

```python
# Phase 3: discover() with requirements (returns List[DiscoveredAgent])
agents = await context.registry.discover(
    requirements=["web_research"],
    include_schemas=True,
)
for agent in agents:
    schemas = agent.get_consumed_schemas()  # ["research_request_v1"]
    schema = await context.registry.get_schema(schemas[0])

# Current: discover_agents() — returns basic AgentDefinition list
agents = await context.registry.discover_agents(
    consumed_event="web.research.requested"
)
```

**Key Characteristics:**
- **TTL:** Agent registration expires after 5 minutes without heartbeat
- **Cleanup:** Background task removes stale agents every 60 seconds
- **Deduplication:** Shows only most recently active instance per agent type

### Event Registration

```python
# Register event definition
await context.registry.register_event(
    event_name="web.research.requested",
    description="Request for web research",
    schema={"topic": "string", "max_results": "integer"}
)
```

**Endpoints:**
- `POST /api/v1/events` - Register event
- `GET /api/v1/events` - Query events

### Query API

```python
# Query agents by capability
agents = await context.registry.query_agents(
    capabilities=["web_research"]
)

# Result: List of active agents matching capability
for agent in agents:
    print(f"{agent.name}: {agent.capabilities}")
```

---

## Discovery Patterns

### Pattern 1: Static Discovery

**Use Case:** Simple workflows with known agents.

```python
# Hardcoded event names
@planner.on_goal("research.goal")
async def plan_research(goal: GoalEvent, ctx: PlatformContext):
    # Static: Know the event type in advance
    await ctx.bus.request(
        topic=EventTopic.ACTION_REQUESTS,
        event_type="web.research.requested",  # Hardcoded
        data={"topic": goal.data["topic"]},
        response_event="research.done"
    )
```

**Pros:** Simple, fast
**Cons:** Inflexible, doesn't adapt to new agents

### Pattern 2: Dynamic Discovery

**Use Case:** Workflows that adapt to available agents.

```python
@planner.on_goal("research.goal")
async def plan_research(goal: GoalEvent, ctx: PlatformContext):
    # Dynamic: Query registry at runtime
    agents = await ctx.registry.query_agents(
        capabilities=["web_research"]
    )
    
    if not agents:
        raise ValueError("No research workers available")
    
    worker = agents[0]
    
    # Use discovered agent's consumed event
    await ctx.bus.request(
        topic=EventTopic.ACTION_REQUESTS,
        event_type=worker.capabilities[0].consumed_event,
        data={"topic": goal.data["topic"]},
        response_event="research.done"
    )
```

**Pros:** Flexible, adapts to available agents
**Cons:** Requires registry query, more complex

### Pattern 3: LLM-based Selection (Phase 3 — `EventSelector`)

**Use Case:** Complex workflows where LLM chooses best event/agent.

```python
from soorma.ai.selection import EventSelector  # Phase 3
from soorma_common.events import EventTopic

@planner.on_goal("support.ticket.received")
async def route_ticket(goal: GoalEvent, ctx: PlatformContext):
    # EventSelector discovers available events and uses LLM to route
    selector = EventSelector(
        context=ctx,
        topic=EventTopic.ACTION_REQUESTS,
        prompt_template=None,  # Uses default template
        model="gpt-4o-mini",
    )
    
    decision = await selector.select_event(
        state={
            "ticket": goal.data["description"],
            "priority": goal.data["priority"],
        }
    )
    
    # decision.event_type validated against registry (no hallucinations)
    await selector.publish_decision(
        decision=decision,
        correlation_id=goal.event_id,
        response_event="ticket.routed",
    )
```

**Pros:** Intelligent selection, handles ambiguity
**Cons:** LLM call overhead, requires good capability descriptions

---

## EventSelector Utility (Phase 3)

**Purpose:** LLM-driven event selection from Registry. Prevents hallucinations by validating selected events exist before publishing.

**Status:** 📋 Phase 3 — [ACTION_PLAN_Phase3](plans/ACTION_PLAN_Phase3_SDK_Implementation.md)

**Features:**
- Queries Registry via `context.toolkit.discover_events()` (existing `EventToolkit`)
- Uses LiteLLM — BYO model (gpt-4o-mini, ollama, claude, etc.)
- Returns `EventDecision` DTO with `event_type`, `payload`, `reasoning`, `confidence`
- Validates LLM-selected event exists in discovered list before returning
- Custom prompt templates via f-string substitution

**Planned API:**

```python
from soorma.ai.selection import EventSelector
from soorma_common.events import EventTopic

selector = EventSelector(
    context=context,          # PlatformContext
    topic=EventTopic.ACTION_REQUESTS,
    model="gpt-4o-mini",
)

decision = await selector.select_event(state={"input": "route this ticket"})
# EventDecision(event_type="billing.issue.requested", payload={...}, reasoning="...")

await selector.publish_decision(
    decision=decision,
    correlation_id="corr-001",
    response_event="ticket.routed",
)
```

---

## Stage 5 Enhancements (Planned)

### RF-ARCH-005: Schema Registration by Name

**Change:** Register **payload schemas by schema name**, not event name.

**Rationale:** Dynamic event names (caller-specified `response_event`) require schemas to be decoupled from event names.

**Planned Schema:**

```python
class PayloadSchema(BaseDTO):
    schema_name: str  # e.g., "research_result_v1"
    version: str
    json_schema: Dict[str, Any]
    owner_agent_id: str
    description: Optional[str]
```

**Example:**

```python
# Register schema independently
await context.registry.register_schema(
    schema_name="research_result_v1",
    version="1.0",
    json_schema={
        "type": "object",
        "properties": {
            "findings": {"type": "array"},
            "confidence": {"type": "number"}
        }
    },
    owner_agent_id="research-worker"
)

# Event references schema by name
await context.registry.register_event(
    event_type="web.research.completed",
    payload_schema_name="research_result_v1",
    description="Research results"
)
```

### RF-ARCH-006: Structured Capabilities

**Change:** Capabilities include full `EventDefinition` objects, not just names.

**Planned Structure:**

```python
class AgentCapability(BaseDTO):
    task_name: str
    description: str
    consumed_event: EventDefinition  # Full schema
    produced_events: List[EventDefinition]
    examples: Optional[List[Dict[str, Any]]]

class EventDefinition(BaseDTO):
    event_type: str  # Canonical type
    payload_schema_name: str
    description: str
    examples: List[Dict[str, Any]]
```

**Benefits:**
- LLM agents get complete schema information
- No separate schema lookup required
- Examples guide payload generation

### RF-ARCH-007: Enhanced Discovery API

**Change:** Discovery returns full schemas for LLM-based delegation.

**Planned Endpoint:**

```python
GET /v1/agents/discover?capabilities=web_search&include_events=true

Response:
{
    "agents": [
        {
            "agent_id": "research-worker-001",
            "name": "Research Worker",
            "capabilities": [
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
                            "description": "Research results"
                        }
                    ]
                }
            ]
        }
    ]
}
```

---

## Best Practices

### Agent Registration

1. **Send heartbeats regularly:** Prevent TTL expiration (every 60-120 seconds)
2. **Unique agent_id:** Use versioned IDs (e.g., "research-worker-v1")
3. **Descriptive capabilities:** Help LLM agents understand what you do
4. **Include examples:** Guide payload generation

### Event Registration

1. **Register schemas early:** Before first event publish
2. **Version schemas:** Use semantic versioning (e.g., "schema_v1.0")
3. **Document changes:** Update descriptions when schema evolves
4. **Tie to agent:** Use owner_agent_id for lifecycle management

### Discovery Queries

1. **Cache results:** Don't query on every event
2. **Handle empty results:** No agents available for capability
3. **Validate schemas:** Ensure payload matches schema
4. **Fallback strategies:** What to do if no agent discovered

---

## Common Patterns

### Pattern: Heartbeat Loop

```python
import asyncio

async def heartbeat_loop(context, agent_id):
    """Send heartbeat every 60 seconds."""
    while True:
        try:
            await context.registry.heartbeat(agent_id)
            await asyncio.sleep(60)
        except Exception as e:
            print(f"Heartbeat failed: {e}")
            await asyncio.sleep(5)  # Retry quickly

# Start in background
asyncio.create_task(heartbeat_loop(context, "my-agent"))
```

### Pattern: Schema Validation (Stage 5)

```python
# Get schema for validation
schema = await context.registry.get_schema("research_request_v1")

# Validate payload before publishing
import jsonschema
try:
    jsonschema.validate(payload, schema.json_schema)
    await context.bus.publish(...)
except jsonschema.ValidationError as e:
    print(f"Invalid payload: {e}")
```

---

## Configuration

Environment variables for Registry Service:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./registry.db` | Async database URL |
| `AGENT_TTL_SECONDS` | `300` | Agent registration TTL (5 min) |
| `AGENT_CLEANUP_INTERVAL_SECONDS` | `60` | Cleanup interval (1 min) |
| `IS_LOCAL_TESTING` | `true` | Use SQLite for local testing |

---

## Examples

- [examples/07-tool-discovery](../../examples/07-tool-discovery/) - Dynamic capability discovery
- [examples/09-app-research-advisor](../../examples/09-app-research-advisor/) - Uses EventSelector

---

## Implementation Status

### Completed

- ✅ Registry Service operational
- ✅ Event and Agent registration endpoints
- ✅ Heartbeat TTL and cleanup
- ✅ Basic query API
- ✅ Agent deduplication by name
- ✅ **v0.8.1:** `PayloadSchema` DTO and `payload_schemas` table (Phase 1)
- ✅ **v0.8.1:** `AgentCapability` with `EventDefinition` objects — breaking change (Phase 1)
- ✅ **v0.8.1:** PostgreSQL RLS for multi-tenant isolation (Phase 1)
- ✅ **v0.8.1:** `POST /v1/schemas`, `GET /v1/schemas/{name}`, `GET /v1/schemas/{name}/versions/{ver}` (Phase 2)
- ✅ **v0.8.1:** `GET /v1/agents/discover` capability-based discovery endpoint (Phase 2)
- ✅ **v0.8.1:** `RegistryClient.register_schema()`, `get_schema()`, `list_schemas()`, `discover_agents()` (Phase 2)

### In Progress

- 📋 **Phase 3:** `RegistryClient.discover()` returning `List[DiscoveredAgent]` (RF-SDK-008)
- 📋 **Phase 3:** `EventSelector` utility (RF-SDK-017)
- 📋 **Phase 3:** `A2AGatewayHelper` for A2A protocol conversion
- 📋 **Phase 3:** `EventDecision` DTO

### Not Started

- ⬜ Phase 4: Tracker Service NATS integration (TECH-DEBT-001)
- ⬜ Phase 5: Examples 11 (LLM discovery), 12 (EventSelector), 13 (A2A gateway)
- ⬜ Phase 5: Documentation updates

---

## Related Documentation

- [ARCHITECTURE.md](./ARCHITECTURE.md) - Technical design
- [Registry Service](../../services/registry/README.md) - Service implementation
- [Refactoring Plan](../refactoring/arch/05-REGISTRY-SERVICE.md) - Stage 5 design
- [Event System](../event_system/README.md) - Event-driven choreography
