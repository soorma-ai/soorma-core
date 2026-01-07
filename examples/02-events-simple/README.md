# 02 - Events Simple

**Concepts:** Event publishing, Event subscription, Pub/Sub pattern  
**Difficulty:** Beginner  
**Prerequisites:** [01-hello-world](../01-hello-world/)

## What You'll Learn

- How to publish events to different topics
- How to subscribe to multiple event types
- How to create event-driven workflows
- Topic-based routing patterns

## The Pattern

Event-driven architecture allows agents to communicate without direct coupling. In this pattern:

1. **Publishers** emit events when something happens (data changes, actions complete, etc.)
2. **Topics** organize events into logical channels using Soorma's predefined topics (e.g., "business-facts", "action-requests")
3. **Subscribers** listen to topics and react to specific event types
4. **The Event Service** handles routing and delivery

This example focuses on teaching the fundamentals: how to publish events, how to subscribe to them, and how to create event chains.

**Note:** Soorma uses fixed topics. Domain events like orders, inventory, and payments all use the `business-facts` topic. See [TOPICS.md](../../docs/TOPICS.md) for details.

## Use Case

A simple order processing flow demonstrating event patterns:
- Customer places an order → `order.placed` event published
- Worker handles it and publishes → `inventory.reserved` event
- Worker handles it and publishes → `payment.completed` event  
- Worker handles it and publishes → `order.shipped` event

Each step is triggered by an event, demonstrating event-driven patterns. (Note: In this example, one worker handles all events for simplicity. Real systems would have separate workers per domain.)

## Code Walkthrough

### Publisher ([publisher.py](publisher.py))

The publisher demonstrates how to emit events to the platform:

```python
from soorma import EventClient

client = EventClient(agent_id="order-service", source="order-service")
await client.connect()

# Publish an event
await client.publish(
    event_type="order.placed",
    topic="business-facts",  # Domain events use business-facts topic
    data={
        "order_id": "ORD-001",
        "items": ["laptop", "mouse"],
        "total": 1500.00
    }
)
```

**Key Points:**
- `EventClient` is used for publishing and subscribing (not just for Workers)
- Events have a `type` (what happened) and go to a `topic` (logical channel)
- Data can be any JSON-serializable dictionary
- Publishing is asynchronous

### Subscriber ([subscriber.py](subscriber.py))

The subscriber demonstrates multiple event handlers:

```python
from soorma import Worker

worker = Worker(
    name="order-processor",
    capabilities=["order-processing"],
    events_consumed=["order.placed", "inventory.reserved", "payment.completed"],
    events_produced=["inventory.reserve", "payment.process", "order.shipped"],
)

@worker.on_event("order.placed")
async def handle_order(event, context):
    # Process order and publish next event
    await context.bus.publish(
        event_type="inventory.reserve",
        topic="business-facts",  # All domain events use business-facts
        data={"order_id": event["data"]["order_id"]}
    )

@worker.on_event("inventory.reserved")
async def handle_inventory(event, context):
    # Continue the workflow
    await context.bus.publish(
        event_type="payment.process",
        topic="business-facts",  # All domain events use business-facts
        data={"order_id": event["data"]["order_id"]}
    )
```

**Key Points:**
- `events_consumed` lists all event types this worker handles
- `events_produced` lists all event types this worker can publish
- Multiple `@worker.on_event()` decorators handle different events
- Each handler can publish new events, creating a chain
- One worker handles the entire flow (for simplicity in this example)
- In a real system, different workers would handle different event types

## Running the Example

### Prerequisites

**Terminal 1: Start Platform Services**

```bash
# From soorma-core root directory
soorma dev --build
```

**Leave this running** for all examples.

### Quick Start

**Terminal 2: Run the example**

```bash
cd examples/02-events-simple
./start.sh
```

This starts the subscriber agent.

**Terminal 3: Publish events**

```bash
python publisher.py
```

### Manual Steps

**After starting platform services above...**

**Terminal 2: Start the Subscriber**

```bash
cd examples/02-events-simple
python subscriber.py
```

You should see the worker start and indicate it's listening for events.

**Terminal 3: Publish Events**

```bash
python publisher.py
```

Watch the subscriber terminal - you'll see it receive and process each event in the workflow chain.

## Expected Output

**Publisher:**
```
Publishing order.placed event...
Publishing inventory.check event...
Publishing payment.authorize event...
All events published!
```

**Subscriber:**
```
📦 Order placed: ORD-001
   Items: laptop, mouse
   Total: $1500.00
   → Publishing inventory.reserve event

📊 Inventory check: ORD-001
   Checking availability...
   → Publishing inventory.reserved event

💳 Payment authorized: ORD-001
   Amount: $1500.00
   → Publishing payment.completed event
```

## Key Takeaways

✅ **Events enable loose coupling** - Publishers don't know who's listening  
✅ **Topics organize event streams** - Use Soorma's predefined topics for type safety  
✅ **Event chains create flows** - Handlers can publish new events to continue processing  
✅ **Multiple handlers per agent** - One Worker can handle many event types  
✅ **Declarative event contracts** - `events_consumed` and `events_produced` document agent behavior  

## Common Patterns

### Fan-Out
One event triggers multiple handlers:
```python
# When order.placed arrives, multiple services react:
@worker1.on_event("order.placed")  # Inventory service
@worker2.on_event("order.placed")  # Analytics service
@worker3.on_event("order.placed")  # Notification service
```

### Sequential Chain
Events trigger in sequence:
```python
order.placed → inventory.reserved → payment.completed → order.shipped
```

### Conditional Routing
Publish different events based on conditions:
```python
@worker.on_event("order.placed")
async def handle_order(event, context):
    if event["data"]["total"] > 1000:
        await context.bus.publish("order.priority", "priority-orders", ...)
    else:
        await context.bus.publish("order.standard", "orders", ...)
```

## Next Steps

- **[03-events-structured](../03-events-structured/)** - Learn how to add rich metadata to events for LLM-based selection
- **[05-memory-working](../05-memory-working/)** - Share state across event handlers in a workflow
- **[08-planner-worker-basic](../08-planner-worker-basic/)** - Combine events with goal-driven orchestration

---

**📖 Additional Resources:**
- [Event Patterns Documentation](../../docs/EVENT_PATTERNS.md)
- [Design Patterns](../../docs/DESIGN_PATTERNS.md)
