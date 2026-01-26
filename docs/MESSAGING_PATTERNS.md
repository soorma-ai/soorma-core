# Event Service Messaging Patterns

This document describes the messaging patterns supported by the Soorma Event Service and how to use them effectively in your agents.

## Overview

The Event Service provides an abstraction layer over message brokers (NATS, GCP Pub/Sub, etc.) and supports three critical messaging patterns:

1. **Queue Behavior (Store-and-Forward)** - Messages are persisted and delivered when consumers reconnect
2. **Broadcast/Fan-Out** - Multiple independent consumers receive the same message
3. **Load Balancing** - Multiple instances of the same consumer share work

## Pattern 1: Queue Behavior (Store-and-Forward)

**Use Case:** Offline consumers should receive events when they reconnect.

### How It Works

The Event Service uses the underlying broker's durable subscription features. Each consumer with a `queue_group` maintains message persistence:

- **NATS:** Durable queue subscriptions persist messages until delivered
- **GCP Pub/Sub:** Subscriptions retain messages per retention policy
- **Memory Adapter:** Ephemeral (for testing only)

### Usage

Agents automatically get queue behavior when they subscribe to topics:

```python
# When agent connects, it automatically receives any queued messages
await context.bus.subscribe(topics=["action-requests"])
```

### Example

```python
from soorma import Worker
from soorma_common import EventEnvelope, EventTopic

worker = Worker(name="task-processor")

@worker.on_event("task.requested", topic=EventTopic.ACTION_REQUESTS)
async def handle_task(event: EventEnvelope, context):
    # This handler will receive messages even if the worker was offline
    # when the messages were published
    data = event.data or {}
    print(f"Processing task: {data}")
    
    await context.bus.publish(
        event_type="task.completed",
        topic=EventTopic.ACTION_RESULTS,
        data={"status": "success"},
        correlation_id=event.correlation_id,
        tenant_id=event.tenant_id,
        user_id=event.user_id,
    )

worker.run()
```

---

## Pattern 2: Broadcast/Fan-Out

**Use Case:** Multiple independent consumers need to receive the same event (each consumer gets its own copy).

### How It Works

Each agent subscription creates an independent consumer. The Event Service manages broker subscriptions, and each agent receives all messages published to the topics they subscribe to.

### Usage

Multiple agents subscribing to the same topic will each receive all messages:

```python
# Agent A - gets all messages
await bus.subscribe(
    topics=["system-events"],
)

# Agent B - also gets all messages (independent subscription)
await bus.subscribe(
    topics=["system-events"],
)
```

### Example

```python
# Logger Agent - logs all events for audit
from soorma import Agent
from soorma_common import EventEnvelope, EventTopic

logger_agent = Agent(name="event-logger")

@logger_agent.on_event("order.placed", topic=EventTopic.BUSINESS_FACTS)
async def log_order(event: EventEnvelope, context):
    print(f"[AUDIT LOG] Order placed: {event.data}")
    # Store in audit database
    await context.memory.store("audit", event.model_dump(mode="json"))

logger_agent.run()

# Analytics Agent - tracks metrics on the same events
analytics_agent = Agent(name="analytics")

@analytics_agent.on_event("order.placed", topic=EventTopic.BUSINESS_FACTS)
async def track_metrics(event: EventEnvelope, context):
    print(f"[ANALYTICS] Updating metrics for order")
    # Update analytics dashboard
    data = event.data or {}
    await update_dashboard(data)

analytics_agent.run()
```

Both agents receive every `order.placed` event independently.

---

## Pattern 3: Load Balancing

**Use Case:** Multiple instances of the same consumer agent share work (only one instance processes each message).

### How It Works

Multiple agents using the **same `queue_group`** will have messages distributed among them (round-robin). The Event Service automatically uses the agent's name as the `queue_group`.

### Implementation Detail

In `event_manager.py`, line 135:
```python
# Use agent_name as queue_group if provided, otherwise fallback to agent_id.
# This enables load balancing across multiple instances of the same logical agent.
queue_group = agent_name if agent_name else agent_id
```

### Usage

Run multiple instances of the same agent (same name) to automatically load balance:

```python
# Instance 1 of research-worker
await bus.subscribe(
    topics=["action-requests"],
)

# Instance 2 of research-worker (same agent_name)
await bus.subscribe(
    topics=["action-requests"],
)
# Same queue_group = messages are distributed between instances
```

### Example

```python
# File: heavy_task_worker.py
from soorma import Worker

worker = Worker(name="heavy-task-worker")  # Same name for all instances

@worker.on_event("heavy.task.requested", topic="action-requests")
async def process_heavy_task(event, context):
    print(f"Instance processing task: {event['data']}")
    # Expensive computation
    result = await expensive_computation(event["data"])
    
    await context.bus.respond(
        event_type="heavy.task.completed",
        data={"result": result},
        correlation_id=event["correlation_id"],
    )

if __name__ == "__main__":
    worker.run()
```

**Deploy multiple instances:**
```bash
# Terminal 1
python heavy_task_worker.py

# Terminal 2
python heavy_task_worker.py

# Terminal 3
python heavy_task_worker.py
```

Messages published to `heavy.task.requested` will be distributed round-robin across the three worker instances.

---

## Combining Patterns

You can combine patterns for sophisticated architectures:

### Example: Order Processing System

```python
# Load-balanced order processor (scale horizontally)
order_processor = Worker(name="order-processor")  # Same name across instances

@order_processor.on_event("order.placed", topic="business-facts")
async def process_order(event, context):
    # Only ONE instance processes each order
    print(f"Processing order: {event['data']['order_id']}")
    await validate_and_process_order(event["data"])

# Broadcast to analytics (all instances receive)
analytics_agent = Agent(name="analytics-1")  # Different name = different queue_group

@analytics_agent.on_event("order.placed", topic="business-facts")
async def track_order(event, context):
    # ALL analytics instances receive the event
    await update_metrics(event["data"])

# Broadcast to audit log (all instances receive)
audit_agent = Agent(name="audit-logger")  # Different name = different queue_group

@audit_agent.on_event("order.placed", topic="business-facts")
async def audit_order(event, context):
    # ALL audit instances receive the event
    await log_to_audit_trail(event["data"])
```

---

## Best Practices

### 1. Choose the Right Pattern

- **Queue Behavior:** Use for reliable message delivery (already built-in)
- **Broadcast:** Use for multiple independent consumers (logging, analytics, notifications)
- **Load Balancing:** Use when you need to scale horizontally (use same agent name)

### 2. Agent Naming

- **Load balancing:** Use the **same name** across instances
- **Broadcast:** Use **different names** for independent consumers

### 3. Topic Organization

Follow the standard Soorma topics:

| Topic | Purpose | Pattern |
|-------|---------|---------|
| `action-requests` | Request work from agents | Load-balanced or Queue |
| `action-results` | Return results to requestor | Queue |
| `business-facts` | Announce domain events | Broadcast + Load-balanced |
| `notification-events` | User notifications | Broadcast |
| `system-events` | Observability, metrics | Broadcast |

### 4. Queue Groups

Queue groups are automatically managed by agent names. To override:

- Use **unique agent names** for broadcast behavior
- Use **same agent name** for load balancing
- The Event Service handles the underlying queue_group parameter

---

## Testing Patterns

### Test Queue Behavior

```python
# 1. Start an agent
# 2. Stop the agent
# 3. Publish events while agent is offline
# 4. Restart the agent
# 5. Verify agent receives queued messages
```

### Test Broadcast

```python
# 1. Start multiple agents with different names
# 2. Publish one event
# 3. Verify all agents receive the event
```

### Test Load Balancing

```python
# 1. Start multiple agents with the same name
# 2. Publish multiple events
# 3. Verify events are distributed (not all to one agent)
```

---

## Implementation References

- **Event Service:** `services/event-service/src/event_manager.py` (line 135)
- **SDK Subscribe:** `sdk/python/soorma/context.py` (BusClient.subscribe)
- **Tests:** `services/event-service/tests/test_queue_groups.py`

---

## Related Documentation

- [Event System SDK](../sdk/01-EVENT-SYSTEM.md) - SDK BusClient changes
- [Event Service Architecture](../arch/01-EVENT-SERVICE.md) - Service-level patterns
- [Distributed Tracing](../arch/01-EVENT-SERVICE.md#distributed-tracing) - trace_id propagation
