# Event Patterns

**Status:** 📝 Draft  
**Last Updated:** January 6, 2026

This document describes event-driven architecture patterns in Soorma.

---

## Overview

Events are the primary communication mechanism in Soorma. They enable:
- **Loose coupling** between agents
- **Choreographed workflows** without central orchestration
- **Scalability** through asynchronous processing
- **Flexibility** to add/remove capabilities dynamically

### Topics

**⚠️ Important:** Soorma uses a fixed set of well-defined topics. You cannot use arbitrary topic names.

**See [TOPICS.md](TOPICS.md) for the complete list of topics and detailed guidance on which topic to use.**

---

## Event Types

### 1. Simple Events

**When to use:** Straightforward pub/sub with hardcoded event types

**Example:** [02-events-simple](../examples/02-events-simple/)

```python
@worker.on_event("order.placed")
async def handle_order(event, context):
    await context.bus.publish(
        event_type="inventory.reserve",
        topic="business-facts",  # ← Use correct Soorma topic
        data={...}
    )
```

**Characteristics:**
- Event names are known at compile time
- Fast - no discovery overhead
- Best for stable, well-defined workflows
- Must use valid Soorma topics

### 2. Structured Events

**When to use:** Dynamic event selection based on context

**Example:** [03-events-structured](../examples/03-events-structured/)

```python
from pydantic import BaseModel, Field
from soorma_common import EventDefinition, EventTopic

# Define event with Pydantic schema
class Tier2RoutePayload(BaseModel):
    ticket_id: str = Field(..., description="Ticket to route")
    category: str = Field(..., description="Issue category")
    severity: str = Field(..., description="Severity level")
    technical_area: str = Field(..., description="Technical domain")

TIER2_ROUTE_EVENT = EventDefinition(
    event_name="ticket.route.tier2",
    topic=EventTopic.ACTION_REQUESTS,
    description="Route to Tier 2 technical support for technical issues",
    payload_schema=Tier2RoutePayload.model_json_schema(),
)

# LLM discovers and chooses event dynamically
events = await discover_events(context, topic="action-requests")
selected = await select_event_with_llm(prompt_template, data, events)
await validate_and_publish(selected, events, "action-requests", context)
```

**Characteristics:**
- Events defined with Pydantic models for type safety
- EventDefinition objects with rich metadata
- Event names discovered at runtime from Registry
- SDK automatically registers EventDefinition objects
- Flexible - workflows adapt to available capabilities
- Best for complex, changing requirements

---

## Event Components

### Event Structure

```python
{
    "id": "evt_abc123",
    "type": "order.placed",
    "source": "order-service",
    "topic": "orders",
    "timestamp": "2026-01-06T10:30:00Z",
    "data": {
        "order_id": "ORD-001",
        "items": [...],
        "total": 1500.00
    },
    "correlation_id": "req_xyz789"
}
```

### Agent Event Declarations

Agents declare which events they consume and produce. When using structured events, pass EventDefinition objects (not strings) for SDK auto-registration:

```python
from events import TICKET_CREATED_EVENT, TIER1_ROUTE_EVENT, TIER2_ROUTE_EVENT

worker = Worker(
    name="ticket-router",
    capabilities=["ticket-routing"],
    events_consumed=[TICKET_CREATED_EVENT],  # EventDefinition objects
    events_produced=[TIER1_ROUTE_EVENT, TIER2_ROUTE_EVENT],  # EventDefinition objects
)
```

For simple events, strings are sufficient:

```python
worker = Worker(
    name="order-processor",
    capabilities=["order-processing"],
    events_consumed=["order.placed", "inventory.reserved"],
    events_produced=["inventory.reserve", "payment.process"],
)
```

This enables:
- **SDK Auto-Registration** - EventDefinition objects are automatically registered with Registry on startup
- **Event Flow Visualization** - Registry knows the complete event graph
- **Dependency Analysis** - Which agents depend on which events
- **Impact Analysis** - What happens if an event changes
- **Documentation** - Self-documenting event consumers/producers

### Topics

Topics organize events into logical channels. Soorma provides 8 fixed topics for routing events.

**See [TOPICS.md](TOPICS.md) for the complete topics reference, including purpose, example events, and selection guidance.**

---

## Common Patterns

### Fan-Out Pattern

One event triggers multiple handlers:

```python
# When order.placed arrives, multiple services react
@inventory_worker.on_event("order.placed")
@analytics_worker.on_event("order.placed")
@notification_worker.on_event("order.placed")
```

**Use when:** Multiple independent actions needed for one event

### Sequential Chain Pattern

Events trigger in sequence:

```python
order.placed → inventory.reserved → payment.completed → order.shipped
```

**Use when:** Steps must happen in order

### Conditional Routing Pattern

Publish different events based on conditions:

```python
@worker.on_event("order.placed")
async def route_order(event, context):
    if event["data"]["total"] > 1000:
        await context.bus.publish(
            event_type="order.priority.route",
            topic="action-requests",
            data=event["data"]
        )
    else:
        await context.bus.publish(
            event_type="order.standard.route",
            topic="action-requests",
            data=event["data"]
        )
```

**Use when:** Logic determines next step

### Request-Reply Pattern

RPC-style synchronous communication over events:

```python
# Requester sends request and waits for correlated response
response = await context.bus.request(
    event_type="tool.request",
    data={
        "tool": "calculator",
        "operation": "add",
        "data": {"a": 5, "b": 3}
    },
    timeout=30.0
)
print(f"Result: {response['result']}")  # 8

# Responder handles request and publishes response with correlation_id
@tool.on_invoke("add")
async def add(request: ToolRequest, context: PlatformContext):
    result = request.data["a"] + request.data["b"]
    return {"result": result}  # SDK handles correlation
```

**Use when:** Need immediate response from another agent

**Note:** The SDK handles correlation IDs automatically. Tools publish to `action-results` topic with the correlation_id from the request.

---

## Event Discovery

Agents can discover available events from the Registry:

```python
from soorma.ai.event_toolkit import EventToolkit

async with EventToolkit(context.registry.base_url) as toolkit:
    # Discover all events on a topic
    events = await toolkit.discover_actionable_events(topic="action-requests")
    
    # Each event includes metadata
    for event in events:
        print(f"{event['name']}: {event['description']}")
        # Metadata available if event was registered with EventDefinition
        if 'metadata' in event:
            print(f"When to use: {event['metadata'].get('when_to_use', 'N/A')}")
```

This enables:
- **Dynamic workflows** that adapt to available capabilities
- **LLM-based event selection** based on semantic understanding
- **Validation** that events exist before publishing

**See [03-events-structured](../examples/03-events-structured/) for complete example.**

---

## Best Practices

### ✅ Do

- Use descriptive event names: `order.placed` not `order1`
- Include correlation IDs for tracing
- Version events when schemas change: `order.placed.v2`
- Add rich metadata for LLM reasoning
- Validate payloads against schemas
- Use topics to organize related events

### ❌ Don't

- Create too many granular events (event explosion)
- Put large payloads in events (use references instead)
- Rely on event ordering (design for eventual consistency)
- Use events for synchronous operations (use RPC instead)
- Hardcode event names that should be discovered

---

## Related Documentation

- [Topics](./TOPICS.md) - Complete topics reference and selection guide
- [Design Patterns](./DESIGN_PATTERNS.md) - Agent orchestration patterns
- [Event Architecture](../sdk/python/docs/EVENT_ARCHITECTURE.md) - SDK internals, decorator mapping, topic derivation
- [Architecture](../ARCHITECTURE.md) - Platform overview
- [Examples](../examples/) - Working code examples

---

## Future Enhancements

- **Event Sourcing** - Store events as source of truth
- **Event Replay** - Replay events for debugging/testing
- **Dead Letter Queue** - Handle failed event processing
- **Event Throttling** - Rate limiting per topic
- **Event Schemas** - Formal schema validation

---

**See Also:**
- [02-events-simple](../examples/02-events-simple/) - Basic pub/sub example
- [03-events-structured](../examples/03-events-structured/) - Rich metadata example
