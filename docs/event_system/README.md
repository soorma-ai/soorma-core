# Event System

**Status:** ✅ Stage 1 Complete  
**Last Updated:** February 15, 2026  
**Related Stages:** Stage 1 (Foundation - Event System)

---

## Overview

Events are the primary communication mechanism in Soorma. They enable:
- **Loose coupling** between agents
- **Choreographed workflows** without central orchestration
- **Scal ability** through asynchronous processing
- **Flexibility** to add/remove capabilities dynamically

### Key Principles

1. **Event-driven choreography** - Agents communicate exclusively through events
2. **Fixed topic schema** - 8 well-defined topics (not arbitrary names)
3. **Explicit topic specification** - No magic topic inference
4. **Correlation tracking** - Multi-step workflows maintain trace_id and parent_event_id
5. **Response routing** - Caller specifies response_event for async completion

---

## Topics

**⚠️ Important:** Soorma uses a fixed set of well-defined topics. You cannot use arbitrary topic names.

### Core DisCo Topics

| Topic | Purpose | Who Publishes | Who Subscribes |
|-------|---------|---------------|----------------|
| **action-requests** | Request another agent to perform an action | Planner, Worker | Worker agents |
| **action-results** | Report results from completing an action | Worker | Planner that initiated |
| **business-facts** | Announce business domain events | Any agent | Choreography observers |

### System Topics

| Topic | Purpose | Who Publishes | Who Subscribes |
|-------|---------|---------------|----------------|
| **system-events** | Platform lifecycle events | System services | Monitoring services |
| **notification-events** | User-facing notifications | Any agent | Notification gateways |

### Orchestration Topics

| Topic | Purpose | Who Publishes | Who Subscribes |
|-------|---------|---------------|----------------|
| **plan-events** | Plan lifecycle (creation, completion) | Planner | Workflow engines |
| **task-events** | Individual task lifecycle within plans | Worker | Progress tracking |
| **billing-events** | Usage and cost tracking | System | Billing services |

### Topic Selection Guide

```
What are you publishing?

├─ Request for agent to do work?
│  └─ action-requests
│
├─ Report result from completed work?
│  └─ action-results
│
├─ Business domain observation?
│  └─ business-facts
│
├─ Platform lifecycle event?
│  └─ system-events
│
├─ User-facing notification?
│  └─ notification-events
│
├─ Plan/task tracking?
│  └─ plan-events, task-events
│
└─ Billing/usage data?
   └─ billing-events
```

---

## Event Structure

### EventEnvelope (Stage 1 Enhancements)

```python
{
    "id": "evt_abc123",
    "event_type": "research.requested",      # Event name
    "topic": "action-requests",              # Routing topic
    "timestamp": "2026-01-17T10:30:00Z",
    "data": {...},                           # Event payload
    
    # Stage 1 additions
    "response_event": "research.completed",  # Caller-specified response
    "response_topic": "action-results",      # Where to publish response
    "trace_id": "trace_xyz",                 # Distributed tracing
    "parent_event_id": "evt_parent",         # Event chain parent
    "payload_schema_name": "ResearchRequest", # Schema for LLM lookup
    
    # Correlation & context
    "correlation_id": "req_789",
    "tenant_id": "tenant-001",
    "user_id": "user-123",
    "source": "planner-agent"
}
```

**Key Fields:**
- `event_type`: Semantic name of the event (e.g., "order.placed")
- `topic`: Routing channel (from fixed set)
- `response_event`: Caller specifies expected response event name
- `trace_id`: Tracks entire workflow across multiple events
- `parent_event_id`: Links child events to parent for hierarchy
- `payload_schema_name`: Schema reference for LLM reasoning

---

## Event Types

### 1. Simple Events

**When to use:** Straightforward pub/sub with hardcoded event types

**Example:** [02-events-simple](../../examples/02-events-simple/)

```python
from soorma import Worker
from soorma_common import EventTopic

worker = Worker(name="order-processor")

@worker.on_event(topic=EventTopic.BUSINESS_FACTS, event_type="order.placed")
async def handle_order(event, context):
    await context.bus.publish(
        topic=EventTopic.ACTION_REQUESTS,
        event_type="inventory.reserve",
        data=event.data,
        correlation_id=event.correlation_id,
    )
```

**Characteristics:**
- Event names known at compile time
- Fast - no discovery overhead
- Best for stable workflows
- Uses EventTopic enum for type safety

### 2. Structured Events

**When to use:** Dynamic event selection based on context

**Example:** [03-events-structured](../../examples/03-events-structured/)

```python
from pydantic import BaseModel, Field
from soorma_common import EventDefinition, EventTopic

# Define event with Pydantic schema
class ResearchPayload(BaseModel):
    query: str = Field(..., description="Research query")
    depth: str = Field(default="standard", description="Research depth")

RESEARCH_EVENT = EventDefinition(
    event_name="research.requested",
    topic=EventTopic.ACTION_REQUESTS,
    description="Request research on a topic",
    payload_schema=ResearchPayload.model_json_schema(),
)

# SDK auto-registers EventDefinition on agent startup
worker = Worker(
    name="researcher",
    events_consumed=[RESEARCH_EVENT],  # Pass EventDefinition objects
)
```

**Characteristics:**
- Events defined with Pydantic models
- Rich metadata for LLM reasoning
- Auto-registration with Registry
- Flexible - adapts to available capabilities

---

## Messaging Patterns

The Event Service supports three critical patterns through the `queue_group` parameter:

### Pattern 1: Queue Behavior (Store-and-Forward)

**Use Case:** Offline consumers receive events when they reconnect

**How it works:** Event Service uses broker's durable subscription features

```python
# Agent automatically gets queue behavior
await context.bus.subscribe(topics=["action-requests"])

# Messages are persisted until delivered
```

**Broker behavior:**
- **NATS:** Durable queue subscriptions
- **GCP Pub/Sub:** Subscription retention policy
- **Memory:** Ephemeral (testing only)

### Pattern 2: Broadcast/Fan-Out

**Use Case:** Multiple independent consumers receive same event

**How it works:** Each agent subscription creates independent consumer

```python
# Logger agent - gets all events
logger = Agent(name="event-logger")

@logger.on_event(topic=EventTopic.BUSINESS_FACTS, event_type="order.placed")
async def log(event, context):
    await context.memory.store("audit", event.model_dump(mode="json"))

# Analytics agent - also gets all events
analytics = Agent(name="analytics")

@analytics.on_event(topic=EventTopic.BUSINESS_FACTS, event_type="order.placed")
async def track(event, context):
    await update_metrics(event.data)
```

**Both agents receive every event independently.**

### Pattern 3: Load Balancing

**Use Case:** Multiple instances of same agent share work

**How it works:** Agents with same name use same `queue_group`

```python
# Same agent name = load balanced
worker = Worker(name="heavy-task-worker")

@worker.on_event(topic=EventTopic.ACTION_REQUESTS, event_type="heavy.task")
async def process(event, context):
    # Only ONE instance processes each event
    result = await expensive_computation(event.data)
    await context.bus.publish(...)
```

**Deploy multiple instances:**
```bash
# Terminal 1
python worker.py

# Terminal 2
python worker.py

# Terminal 3
python worker.py
```

Messages are distributed round-robin across instances.

---

## Common Patterns

### Fan-Out Pattern

One event triggers multiple handlers:

```python
@inventory_worker.on_event(topic=EventTopic.BUSINESS_FACTS, event_type="order.placed")
@analytics_worker.on_event(topic=EventTopic.BUSINESS_FACTS, event_type="order.placed")
@notification_worker.on_event(topic=EventTopic.BUSINESS_FACTS, event_type="order.placed")
async def handle(event, context):
    # Each agent processes independently
    pass
```

### Sequential Chain Pattern

Events trigger in sequence:

```
order.placed → inventory.reserved → payment.completed → order.shipped
```

### Request-Response Pattern (Stage 1)

Async request/response with response_event:

```python
# Worker handles request and publishes to caller's response_event
@worker.on_task(event_type="calculate.requested")
async def calculate(task, context):
    result = await do_calculation(task.data)
    
    # Publish to caller-specified response_event
    await context.bus.respond(
        event_type=task.response_event,  # Caller specifies this
        data={"result": result},
        correlation_id=task.correlation_id,
    )
```

### Event Discovery Pattern

Discover available events at runtime:

```python
from soorma.ai.event_toolkit import EventToolkit

# Discover events on topic
events = await toolkit.discover_actionable_events(
    topic="action-requests"
)

# Each event includes metadata
for event in events:
    print(f"{event['name']}: {event['description']}")
```

**See:** [03-events-structured](../../examples/03-events-structured/)

---

## Publishing Events

### Basic Publishing

```python
await context.bus.publish(
    topic=EventTopic.ACTION_REQUESTS,
    event_type="research.requested",
    data={"query": "AI trends"},
    correlation_id=str(uuid4()),
)
```

### Request with Response Event (Stage 1)

```python
await context.bus.request(
    topic=EventTopic.ACTION_REQUESTS,
    event_type="calculate.requested",
    data={"expression": "2 + 2"},
    response_event="calc.result",  # Caller specifies response
    response_topic=EventTopic.ACTION_RESULTS,
)
```

### Creating Child Requests (Stage 1)

```python
# Auto-propagate trace_id and parent_event_id
child_params = context.bus.create_child_request(
    parent_event=goal_event,
    event_type="web.search.requested",
    data={"query": "AI"},
    response_event="task-1.search.done",
)

await context.bus.request(**child_params)
```

---

## Best Practices

### ✅ Do

- Use explicit topic specification (no inference)
- Include correlation_id for tracing
- Specify response_event for async completion
- Use EventTopic enum for type safety
- Add rich metadata for LLM reasoning
- Use create_child_request() for event chains

### ❌ Don't

- Create arbitrary topic names
- Rely on topic inference (removed in Stage 1)
- Omit correlation tracking
- Put large payloads in events (use references)
- Assume event ordering
- Hardcode event names that should be discovered

---

## Examples

| Example | Pattern | Status |
|---------|---------|--------|
| [02-events-simple](../../examples/02-events-simple/) | Basic pub/sub | ✅ |
| [03-events-structured](../../examples/03-events-structured/) | Rich metadata, discovery | ✅ |
| [08-worker-basic](../../examples/08-worker-basic/) | Sequential delegation | ✅ |

---

## Related Documentation

- [ARCHITECTURE.md](./ARCHITECTURE.md) - Technical design and implementation
- [Agent Patterns](../agent_patterns/README.md) - Agent orchestration patterns
- [Refactoring Plan](../refactoring/sdk/01-EVENT-SYSTEM.md) - Stage 1 implementation details

