# Service Discovery: User Guide

**Status:** 🔄 Stage 5 Planned  
**Last Updated:** February 15, 2026  
**Related Stages:** Stage 5 (RF-ARCH-005, RF-ARCH-006, RF-ARCH-007, RF-SDK-015, RF-SDK-016, RF-SDK-017)

---

## Overview

The Discovery System enables **dynamic agent discovery** and **capability-based communication** in Soorma Core. It provides:

- **Event Registry:** Register and query event definitions with schemas
- **Agent Registry:** Register and query agent definitions with capabilities
- **Discovery API:** Find agents by capability for LLM-based delegation

**Current Implementation:**
- ✅ Basic Registry Service with Event and Agent registration
- 🔄 Stage 5 enhancements planned (schema-based discovery, structured capabilities)

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

## Current API (Stages 0-3)

### Agent Registration

```python
from soorma import PlatformContext

async with PlatformContext() as context:
    # Register agent with capabilities
    await context.registry.register_agent(
        agent_id="research-worker-001",
        name="Research Worker",
        capabilities=[
            {
                "taskName": "web_research",
                "description": "Performs web research",
                "consumedEvent": "web.research.requested",
                "producedEvents": ["research.completed"]
            }
        ]
    )
    
    # Send heartbeat (keeps agent active)
    await context.registry.heartbeat(agent_id="research-worker-001")
```

**Endpoints:**
- `POST /api/v1/agents` - Register agent
- `GET /api/v1/agents` - Query agents
- `PUT /api/v1/agents/{agent_id}/heartbeat` - Refresh heartbeat

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

### Pattern 3: LLM-based Selection

**Use Case:** Complex workflows where LLM chooses best agent.

```python
from soorma.discovery import EventSelector

@planner.on_goal("research.goal")
async def plan_research(goal: GoalEvent, ctx: PlatformContext):
    # LLM selects best event/agent for goal
    selector = EventSelector(
        registry_client=ctx.registry,
        llm_client=ctx.llm
    )
    
    selected_event = await selector.select_event(
        goal_description="Perform web research on AI trends",
        capabilities=["web_research", "academic_search"]
    )
    
    # Use LLM-selected event
    await ctx.bus.request(
        topic=EventTopic.ACTION_REQUESTS,
        event_type=selected_event.event_type,
        data=selected_event.suggested_payload,
        response_event="research.done"
    )
```

**Pros:** Intelligent selection, handles ambiguity
**Cons:** LLM call overhead, requires good capability descriptions

---

## EventSelector Utility

**Purpose:** LLM-driven event selection from Registry.

**Features:**
- Queries Registry for available capabilities
- Uses LLM to select best match for goal
- Generates suggested payload based on schema
- Validates selection against Registry

**Implementation (Stage 5 Planned):**

```python
class EventSelector:
    def __init__(self, registry_client, llm_client):
        self.registry = registry_client
        self.llm = llm_client
    
    async def select_event(
        self,
        goal_description: str,
        capabilities: List[str],
        custom_prompt: Optional[str] = None
    ) -> EventSelection:
        # 1. Query Registry for capabilities
        agents = await self.registry.query_agents(capabilities)
        
        # 2. Build LLM prompt with schemas
        prompt = self._build_prompt(goal_description, agents, custom_prompt)
        
        # 3. LLM selects best event
        response = await self.llm.complete(prompt)
        
        # 4. Parse and validate
        selection = self._parse_selection(response)
        self._validate_selection(selection, agents)
        
        return selection
```

**Example:** [examples/09-app-research-advisor](../../examples/09-app-research-advisor/)

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

### Current (Stages 0-3)

- ✅ Registry Service operational
- ✅ Event and Agent registration endpoints
- ✅ Heartbeat TTL and cleanup
- ✅ Basic query API
- ✅ Agent deduplication by name

### Stage 5 (Planned)

- ⬜ RF-ARCH-005: Schema registration by name
- ⬜ RF-ARCH-006: Structured capabilities with EventDefinition
- ⬜ RF-ARCH-007: Enhanced discovery API with schemas
- ⬜ RF-SDK-015: DiscoveryClient in SDK
- ⬜ RF-SDK-016: Schema validation helpers
- ⬜ RF-SDK-017: EventSelector utility

---

## Related Documentation

- [ARCHITECTURE.md](./ARCHITECTURE.md) - Technical design
- [Registry Service](../../services/registry/README.md) - Service implementation
- [Refactoring Plan](../refactoring/arch/05-REGISTRY-SERVICE.md) - Stage 5 design
- [Event System](../event_system/README.md) - Event-driven choreography
