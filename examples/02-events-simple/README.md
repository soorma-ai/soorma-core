# 02 - Events Simple

**Concepts:** Event publishing, Event subscription, Event chains, Metadata propagation  
**Difficulty:** Beginner  
**Prerequisites:** [01-hello-world](../01-hello-world/)

**Teaching Focus:** This example demonstrates **production-ready patterns** you should use in real code:
- ✅ `announce()` for business facts (not low-level `publish()`)
- ✅ Metadata propagation for distributed tracing
- ✅ Event chains for workflow orchestration

## What You'll Learn

- How to publish and subscribe to domain events
- How to handle multiple event types in one agent
- How to create event chains with automatic metadata propagation
- **Best practice: Use `announce()` for business facts** (instead of low-level `publish()`)
- **Best practice: Propagate trace_id for distributed tracing**

## The Pattern

Event-driven architecture allows agents to communicate without direct coupling. In this pattern:

1. **Publishers** emit events when something happens (data changes, actions complete, etc.)
2. **Event Types** identify what happened (e.g., "order.placed", "payment.completed")
3. **Topics** organize events into logical channels - Soorma has predefined topics (e.g., "business-facts" for domain events)
4. **Subscribers** listen to topics and react to specific event types
5. **The Event Service** handles routing and delivery

This example demonstrates event publishing, subscription, and event chains - where one event handler triggers another by publishing a new event.

**Note:** Soorma uses fixed topics for type safety. Domain events (orders, inventory, payments) use the `business-facts` topic. See [TOPICS.md](../../docs/TOPICS.md) for details.

## Use Case

A simple order processing flow demonstrating event chains. This example shows how one event handler can publish new events, triggering other handlers in sequence.

**The Event Chain:**
```
publisher.py                    subscriber.py handlers
    |                                  |
    |-- order.placed ------------> handle_order_placed()
                                       |
                                       |-- inventory.reserved -----> handle_inventory_reserved()
                                                                         |
                                                                         |-- payment.completed -----> handle_payment_completed()
                                                                                                          |
                                                                                                          |-- order.completed -----> handle_order_completed()
                                                                                                                                        (END)
```

**How it works:**
1. **Publisher** publishes `order.placed` event with a trace_id (fact: an order was placed)
2. **Subscriber** receives it, extracts metadata (trace_id, parent_event_id), reserves inventory, then announces `inventory.reserved` **with the same trace_id**
3. **Subscriber** receives `inventory.reserved`, extracts metadata, processes payment, then announces `payment.completed` **with the same trace_id**
4. **Subscriber** receives `payment.completed`, extracts metadata, finalizes order, then announces `order.completed` **with the same trace_id**
5. **Subscriber** receives `order.completed` - final step shows the complete trace

The **trace_id flows through the entire chain**, creating end-to-end traceability. This is crucial for debugging distributed workflows.

Each step is triggered by an event from the previous step, creating an **event-driven workflow**. 

**Note about topics and methods:** 
- This example uses `business-facts` topic for all events because they represent domain facts (things that happened in the business)
- Uses **`bus.announce()`** instead of low-level `bus.publish()` - semantically correct for business facts where no response is expected
- Events use past-tense names (`.placed`, `.reserved`, `.completed`) to indicate they're observations of state changes, not commands
- This is the **choreography pattern** - services react to facts about what happened, no central orchestrator

In this example, one worker handles all events for simplicity. Real systems would have separate workers per domain (inventory service, payment service, etc.).

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

@worker.on_event("order.placed", topic="business-facts")
async def handle_order(event, context):
    # Process order and publish next event
    await context.bus.publish(
        event_type="inventory.reserve",
        topic="business-facts",
        data={"order_id": event["data"]["order_id"]}
    )

@worker.on_event("inventory.reserved", topic="business-facts")
async def handle_inventory(event, context):
    # Continue the workflow
    await context.bus.publish(
        event_type="payment.process",
        topic="business-facts",
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

When you run the example, watch for the **event chain** in the subscriber output:

**Publisher:**
```
📦 Publishing order.placed event...
   (This will trigger the event chain in the subscriber)

   ✓ Published to 'business-facts' topic

================================================================
✅ Event published!
================================================================

Watch the subscriber terminal to see the event chain:
  order.placed → inventory.reserved → payment.completed → order.completed
```

**Subscriber (watch the chain flow - each handler publishes the next event):**
```
================================================================
📦 Order placed!                           <-- 1. order.placed received
================================================================
   Order ID: ORD-001
   Items: laptop, mouse
   Total: $1500.00
   Trace ID: 3f7a8b2e...                   <-- Trace starts here

   Reserving inventory...
   ✓ Items reserved!

   → Announcing inventory.reserved event...  <-- Handler announces next event
   ✓ Event announced

================================================================
🔒 Inventory reserved!                     <-- 2. inventory.reserved received
================================================================
   Order ID: ORD-001
   Items: laptop, mouse
   Trace ID: 3f7a8b2e...                   <-- Same trace_id

   Processing payment...
   ✓ Payment processed!

   → Announcing payment.completed event...   <-- Handler announces next event
   ✓ Event announced

================================================================
💳 Payment completed!                      <-- 3. payment.completed received
================================================================
   Order ID: ORD-001
   Trace ID: 3f7a8b2e...                   <-- Same trace_id

   Finalizing order...
   ✓ Order finalized!

   → Announcing order.completed event...     <-- Handler announces next event
   ✓ Event announced

================================================================
🎉 Order workflow completed!               <-- 4. order.completed received (END)
================================================================
   Order ID: ORD-001
   Trace ID: 3f7a8b2e...                   <-- Same trace_id throughout!
   All steps finished successfully!
   (Same trace_id propagated through entire chain)
================================================================
```

**Notice the patterns:** 
1. Publisher sends **one** initial event (`order.placed`)
2. Each handler does its work and **announces** the **next** event in the chain
3. **Metadata flows through**: The same `trace_id` appears in every step - this creates end-to-end traceability
4. Uses `announce()` not `publish()` - teaches the right abstraction for business facts

This is **event choreography** with **distributed tracing** - no central orchestrator, just services reacting to domain facts with full observability!

## Key Takeaways

✅ **Events enable loose coupling** - Publishers don't know who's listening  
✅ **Event types identify what happened** - Use descriptive past-tense names like "order.placed"  
✅ **Use high-level methods** - `announce()` for facts, `request()` for work (not low-level `publish()`)  
✅ **Propagate metadata** - trace_id and parent_event_id create end-to-end traceability  
✅ **Event chains create workflows** - Handlers announce new events to continue processing  
✅ **Multiple handlers per agent** - One Worker can handle many event types  
✅ **Declarative contracts** - `events_consumed` and `events_produced` document agent behavior  

## Common Patterns

### Fan-Out (different agents):
```python
# When order.placed arrives, multiple services react:
@worker1.on_event("order.placed", topic="business-facts")  # Inventory service
@worker2.on_event("order.placed", topic="business-facts")  # Analytics service
@worker3.on_event("order.placed", topic="business-facts")  # Notification service
```

### Sequential Chain
Events trigger in sequence to create a workflow:
```python
order.placed → inventory.reserved → payment.completed → order.shipped
```

### Conditional Events
Publish different event types based on conditions:
```python
@worker.on_event("order.placed", topic="business-facts")
async def handle_order(event, context):
    if event["data"]["total"] > 1000:
        await context.bus.publish("order.priority", "business-facts", ...)
    else:
        await context.bus.publish("order.standard", "business-fact
        await context.bus.publish("order.standard", "orders", ...)
```

## Next Steps

- **[03-events-structured](../03-events-structured/)** - Learn how to add rich metadata to events for LLM-based selection
- **[04-memory-working](../04-memory-working/)** - Share state across event handlers in a workflow
- **08-planner-worker-basic (coming soon)** - Combine events with goal-driven orchestration

---

**📖 Additional Resources:**
- [Event Patterns Documentation](../../docs/EVENT_PATTERNS.md)
- [Design Patterns](../../docs/DESIGN_PATTERNS.md)
