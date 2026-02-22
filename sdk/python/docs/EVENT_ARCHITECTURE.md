# Soorma Event Architecture

This document describes the topics, events, and how SDK decorators map to the underlying event infrastructure.

## Overview

The Soorma platform uses an event-driven architecture where agents communicate through a centralized **Event Service**. The Event Service acts as a proxy to the underlying message bus (NATS/Kafka/GCP PubSub), providing a unified API for publishing and subscribing to events.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Event Service                                 │
│                    (HTTP + SSE API to Message Bus)                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐         │
│   │ business-facts  │  │ action-requests │  │ action-results  │         │
│   │                 │  │                 │  │                 │         │
│   │ Goals, domain   │  │ Tasks assigned  │  │ Task completion │         │
│   │ events, facts   │  │ to workers      │  │ and results     │         │
│   └─────────────────┘  └─────────────────┘  └─────────────────┘         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Topics

Topics are **stable, well-defined channels** for routing events. They are defined in `soorma-common` and used consistently across all services.

**See [../../../docs/event_system/README.md](../../../docs/event_system/README.md) for the complete topics reference, including purpose, publishers, subscribers, and usage guidance.**

### Topic vs Event Type

- **Topic**: The channel/queue where events are published (e.g., `action-requests`)
- **Event Type**: The semantic type of the event (e.g., `greeting.goal`, `action.request`, `tool.response`)

Multiple event types can flow through the same topic. The Event Service routes events to subscribers based on topic, and subscribers filter by event type.

## SDK Decorator Mapping

The SDK provides high-level decorators that abstract away the topic/event mapping:

### `@planner.on_goal(goal_type)`

**Maps to:** Subscribes to `business-facts` topic, filters by `type == goal_type`

```python
@planner.on_goal("greeting.goal")
async def plan_greeting(goal: GoalContext, context: PlatformContext):
    plan = await PlanContext.create_from_goal(
        goal=goal,
        context=context,
        state_machine={...},
        current_state="start",
        status="pending",
    )
    await plan.execute_next()
```

**Under the hood:**
1. Registers event handler for event type `greeting.goal`
2. `greeting.goal` maps to topic `business-facts` (via `_derive_topics()`)
3. When event arrives, SDK creates `Goal` object and calls handler
4. Handler creates and persists a `PlanContext`, then executes the first state

### `@worker.on_task(task_name)`

**Maps to:** Subscribes to `action-requests` topic, filters by `type == action.request` AND `data.task_name == task_name`

```python
@worker.on_task("greet")
async def handle_greet(task: TaskContext, context) -> dict:
    ...
```

**Under the hood:**
1. Worker auto-subscribes to `action.request` events
2. `action.request` maps to topic `action-requests` (via `_derive_topics()`)
3. When event arrives, SDK checks if `assigned_to` matches worker's name/capabilities
4. SDK creates `TaskContext` and calls the handler for matching `task_name`
5. Handler returns result dict, SDK publishes to `action-results` topic as `action.result`

### `@tool.on_invoke(operation)`

**Maps to:** Subscribes to `action-requests` topic, filters by `type == tool.request` AND `data.operation == operation`

```python
@tool.on_invoke("calculate")
async def calculate(request: ToolRequest, context) -> dict:
    ...
```

**Under the hood:**
1. Tool auto-subscribes to `tool.request` events
2. `tool.request` maps to topic `action-requests` (via `_derive_topics()`)
3. When event arrives, SDK checks if `tool` field matches tool's name
4. SDK creates `ToolRequest` and calls handler for matching `operation`
5. Handler returns result dict, SDK publishes to `action-results` topic as `tool.response`

### `@agent.on_event(event_type)`

**Maps to:** Direct event type subscription with auto-topic inference

```python
@agent.on_event("order.created")
async def handle_order(event, context):
    ...
```

**Under the hood:**
1. Event type `order.created` mapped to topic via `_derive_topics()`
2. Since it doesn't match any special pattern, maps to `business-facts`

## Topic Derivation Logic

The SDK's `Agent._derive_topics()` method maps event types to topics:

```python
def _derive_topics(self, event_types: List[str]) -> List[str]:
    topics = set()
    for event_type in event_types:
        if "*" in event_type:
            topics.add(event_type)  # Wildcard passthrough
        elif event_type.endswith(".request"):
            topics.add("action-requests")
        elif event_type.endswith(".result"):
            topics.add("action-results")
        elif event_type.startswith("billing."):
            topics.add("billing-events")
        elif event_type.startswith("notification."):
            topics.add("notification-events")
        else:
            topics.add("business-facts")  # Default
    return list(topics)
```

## Event Flow Example: Hello World

```
Client                 Planner              Worker               Event Service
  │                      │                    │                       │
  │ ─── greeting.goal ───────────────────────────────────────────────▶│
  │     topic: business-facts                                         │
  │                      │◀─── greeting.goal ─────────────────────────│
  │                      │     (matched by @on_goal)                  │
  │                      │                                            │
  │                      │ ─── action.request ───────────────────────▶│
  │                      │     topic: action-requests                 │
  │                      │     data: {task_name: "greet", ...}        │
  │                      │                    │                       │
  │                      │                    │◀─ action.request ─────│
  │                      │                    │   (matched by @on_task)
  │                      │                    │                       │
  │                      │                    │ ─── action.result ───▶│
  │                      │                    │     topic: action-results
  │                      │                    │     data: {greeting: ...}
  │                      │                    │                       │
  │◀────────────────────────────────────────────── action.result ─────│
  │ (client subscribed to action-results)                             │
```

## Where Definitions Live

| Component | Location | Responsibility |
|-----------|----------|----------------|
| Topic Enum | `soorma-common/events.py` | Canonical topic names |
| Event DTOs | `soorma-common/events.py` | CloudEvents envelope, typed events |
| Topic Derivation | `sdk/agents/base.py` | Event type → topic mapping |
| Decorator Logic | `sdk/agents/{planner,worker,tool}.py` | High-level abstractions |
| Event Service | `services/gateway/` | Message bus proxy, SSE streaming |

## Design Decisions

### Why SDK Controls Topic Mapping

1. **Convention over Configuration**: Developers use semantic event types (`greeting.goal`), SDK handles routing
2. **Consistency**: All SDKs (Python, future JS/Go) use same mapping logic
3. **Flexibility**: Event Service is topic-agnostic, SDK can evolve mappings independently

### Why Fixed Topics (Not Dynamic)

1. **Observability**: Known topics enable monitoring, alerting, capacity planning
2. **Security**: Topic-level ACLs for access control
3. **Performance**: Message brokers optimize for known topic structures

### Event Type Naming Conventions

| Pattern | Example | Topic | Usage |
|---------|---------|-------|-------|
| `{domain}.goal` | `research.goal` | `business-facts` | Client goals for Planners |
| `{domain}.created` | `order.created` | `business-facts` | Domain events |
| `action.request` | `action.request` | `action-requests` | Planner → Worker |
| `action.result` | `action.result` | `action-results` | Worker → Client |
| `tool.request` | `tool.request` | `action-requests` | Worker → Tool |
| `tool.response` | `tool.response` | `action-results` | Tool → Worker |
| `billing.*` | `billing.usage` | `billing-events` | Cost tracking |
| `notification.*` | `notification.email` | `notification-events` | User alerts |

**For usage patterns, see [../../../docs/event_system/README.md](../../../docs/event_system/README.md).**

## Extending the Architecture

### Adding a New Topic

1. Add to `EventTopic` enum in `soorma-common/events.py`
2. Update `_derive_topics()` in `sdk/agents/base.py`
3. Create topic-specific event DTOs if needed
4. Update Event Service to provision the topic

### Creating Custom Event Types

Custom event types flow through `business-facts` by default:

```python
# Publishing custom events
await context.bus.publish(
    event_type="inventory.low_stock",
    data={"sku": "ABC123", "quantity": 5},
)

# Subscribing to custom events
@agent.on_event("inventory.low_stock")
async def handle_low_stock(event, context):
    ...
```
