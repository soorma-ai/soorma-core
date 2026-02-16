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

**Note:** Soorma uses fixed topics for type safety. Domain events (orders, inventory, payments) use the `business-facts` topic. See [Event System](../../docs/event_system/README.md) for details.

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

The publisher creates an EventClient and publishes the initial event:

```python
client = EventClient(agent_id="order-service", source="order-service")
await client.connect(topics=[])  # Empty list since we only publish

await client.publish(
    event_type="order.placed",
    topic=EventTopic.BUSINESS_FACTS,
    data={"order_id": "ORD-001", "items": [...], "total": 1500.00},
)
```

**How it applies the concepts:**
- `EventClient` is for publishing/subscribing (agents can be clients too)
- `topic=EventTopic.BUSINESS_FACTS` indicates this is a domain event (not a command or request)
- Data is any JSON-serializable dictionary
- This single event triggers the entire event chain in the subscriber

### Subscriber ([subscriber.py](subscriber.py))

The subscriber is a Worker with multiple event handlers that form an event chain:

```python
worker = Worker(
    name="order-processor",
    events_consumed=["order.placed", "inventory.reserved", "payment.completed", "order.completed"],
    events_produced=["inventory.reserved", "payment.completed", "order.completed"],
)

@worker.on_event("order.placed", topic=EventTopic.BUSINESS_FACTS)
async def handle_order_placed(event: EventEnvelope, context: PlatformContext):
    # Extract event data and metadata
    order_id = event.data.get("order_id")
    trace_id = event.trace_id or event.id  # Start trace here if not already traced
    
    # Do work...
    
    # Announce next event with propagated metadata
    await context.bus.announce(
        event_type="inventory.reserved",
        data={"order_id": order_id, ...},
        correlation_id=event.correlation_id,
        trace_id=trace_id,                    # Keep same trace throughout chain
        parent_event_id=event.id,             # Track causality
    )
```

**How it applies the concepts:**
- `events_consumed` and `events_produced` declare all events this worker handles
- Multiple `@worker.on_event()` decorators handle different event types
- **Metadata propagation is key**: Each handler extracts `trace_id` and passes it to the next announcement
  - `trace_id` - Same throughout the chain (enables end-to-end traceability)
  - `parent_event_id` - Points to the event that triggered this announcement (causality tracking)
  - `correlation_id` - Groups related events (passed through unchanged)
- `context.bus.announce()` publishes business facts (use for domain events, not requests)
- Each handler's `announce()` call triggers the next handler's subscription
- **In a real system**, different workers would handle different events (inventory service, payment service, etc.)

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

**Subscriber (watch the chain flow - each handler announces the next event):**
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
1. Publisher sends **one** initial event (`order.placed`) using `client.publish()`
2. Each handler does its work and **announces** the **next** event using `context.bus.announce()`
3. **Metadata flows through**: The same `trace_id` and `correlation_id` appear in every step - creating end-to-end traceability
4. **Causality tracking**: `parent_event_id` tracks which event triggered which
5. Uses `announce()` not `publish()` for business facts - proper abstraction for domain events

This is **event choreography** with **distributed tracing** - no central orchestrator, just services reacting to domain facts with full observability!

## Key Takeaways

✅ **Events enable loose coupling** - Publishers don't know who's listening  
✅ **Event types identify what happened** - Use descriptive past-tense names like "order.placed"  
✅ **Method matters** - `announce()` for business facts/domain events, `publish()` for commands/requests  
✅ **Propagate metadata** - `trace_id` tracks causality, `correlation_id` groups related events, `parent_event_id` shows causality  
✅ **Event chains create workflows** - Handlers announce new events to continue processing  
✅ **Multiple handlers per agent** - One Worker can handle many event types  
✅ **Declarative contracts** - `events_consumed` and `events_produced` document agent behavior  
✅ **Traceability** - All downstream events can reference the original trace for full observability  

## Common Patterns

### Fan-Out (different agents):
```python
from soorma_common.events import EventTopic

# When order.placed arrives, multiple services react:
@worker1.on_event("order.placed", topic=EventTopic.BUSINESS_FACTS)  # Inventory service
@worker2.on_event("order.placed", topic=EventTopic.BUSINESS_FACTS)  # Analytics service
@worker3.on_event("order.placed", topic=EventTopic.BUSINESS_FACTS)  # Notification service
```

### Sequential Chain
Events trigger in sequence to create a workflow:
```python
order.placed → inventory.reserved → payment.completed → order.shipped
```

### Conditional Events
Publish different event types based on conditions:
```python
@worker.on_event("order.placed", topic=EventTopic.BUSINESS_FACTS)
async def handle_order(event: EventEnvelope, context: PlatformContext):
    data = event.data or {}
    total = data.get("total", 0)
    
    # Announce different events based on logic
    event_type = "order.priority" if total > 1000 else "order.standard"
    
    await context.bus.announce(
        event_type=event_type,
        data=data,
        correlation_id=event.correlation_id,
        trace_id=event.trace_id or event.id,
        parent_event_id=event.id,
    )
```

## Next Steps

- **[03-events-structured](../03-events-structured/)** - Learn how to add rich metadata to events for LLM-based selection
- **[04-memory-working](../04-memory-working/)** - Share state across event handlers in a workflow
- **08-planner-worker-basic (coming soon)** - Combine events with goal-driven orchestration

---

**📖 Additional Resources:**
- [Event System Documentation](../../docs/event_system/README.md)
- [Agent Patterns](../../docs/agent_patterns/README.md)
