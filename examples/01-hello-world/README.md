# 01 - Hello World

**Concepts:** Worker pattern, Event handling, Request/Response  
**Difficulty:** Beginner  
**Prerequisites:** None

## What You'll Learn

- How to create a Worker agent
- How to handle events with `@worker.on_event()` decorator
- **Best practice: Use `respond()` for request/response patterns**
- How clients send requests and receive responses

## The Pattern

The Worker pattern is a simple way to build reactive agents in Soorma. A Worker:
1. Declares its capabilities (what it can do)
2. Registers event handlers using `@worker.on_event()` decorator
3. Receives events on subscribed topics
4. Processes the request
5. Sends response using `context.bus.respond()` convenience method

**Key advantage**: The `respond()` method is semantically correct for request/response patterns and cleaner than using low-level `publish()` directly.

## Code Walkthrough

### Worker Agent ([worker.py](worker.py))

```python
from soorma import Worker

# Create a Worker instance
worker = Worker(
    name="hello-worker",
    description="A simple greeting agent",
    capabilities=["greeting"],
    events_consumed=["greeting.requested"],
    events_produced=["greeting.completed"],
)

# Register an event handler
@worker.on_event("greeting.requested", topic="action-requests")
async def handle_greeting(event, context):
    name = event.get("data", {}).get("name", "World")
    greeting = f"Hello, {name}! 👋"
    
    # Use respond() convenience method for request/response
    await context.bus.respond(
        event_type="greeting.completed",
        data={"greeting": greeting, "name": name},
        correlation_id=event.get("correlation_id"),
    )
```

**Key Points:**
- `Worker()` creates an agent instance with a name and capabilities
- `events_consumed` declares which events this agent listens to
- `events_produced` declares which events this agent can publish
- `@worker.on_event()` decorator registers handlers for specific event types
- Event handlers receive the `event` data and `context` (platform services)
- **Use `context.bus.respond()`** for request/response - cleaner than `publish()`
  - Automatically publishes to `action-results` topic
  - Requires correlation_id to link response to request

### Client ([client.py](client.py))

The client demonstrates how to send requests to a Worker:

```python
# Send greeting.requested event
await client.publish(
    event_type="greeting.requested",
    topic="action-requests",
    data={"name": "Alice"},
    correlation_id=str(uuid4()),
    response_event="greeting.completed",
    response_topic="action-results",
)

# Listen for greeting.completed response
@client.on_event("greeting.completed", topic="action-results")
async def on_response(event):
    greeting = event["data"]["greeting"]
    print(f"Got greeting: {greeting}")
```

**Key Points:**
1. Clients publish events with `response_event` and `response_topic` metadata
2. Use `correlation_id` to link request and response
3. Subscribe to response events on the response topic
4. The Worker's `respond()` method automatically sends to the response topic

## Running the Example

### Prerequisites

**Terminal 1: Start Platform Services**

From the `soorma-core` root directory:

```bash
soorma dev --build
```

The `--build` flag builds services from your local code. **Leave this running** for all examples.

### Quick Start

**Terminal 2: Run the example**

```bash
cd examples/01-hello-world
./start.sh
```

This starts the worker agent.

**Terminal 3: Test it**

```bash
python client.py Alice
```

### Manual Steps

If you prefer to run components separately:

**After starting platform services above...**

**Terminal 2: Start the Worker Agent**

```bash
cd examples/01-hello-world
python worker.py
```

You should see:
```
🚀 Hello Worker started!
   Name: hello-worker
   Capabilities: ['greeting']
   Listening for events...
```

**Terminal 3: Send a Request**

```bash
python client.py Alice
```

Expected output:
```
🎯 Sending greeting request for: Alice
📤 Request sent!
📊 Waiting for response...
--------------------------------------------------
🎉 Response: Hello, Alice! 👋
```

## Key Takeaways

✅ **Workers are reactive** - They respond to events, not direct API calls  
✅ **Decorators make it simple** - `@worker.on_event()` handles subscription automatically  
✅ **Context provides platform services** - Access Registry, Memory, Event Bus through `context`  
✅ **Events are asynchronous** - Use `async/await` for all handlers  

## Common Mistakes to Avoid

❌ **Forgetting to run `soorma dev`** - Agents need the platform services running  
❌ **Not awaiting async calls** - All platform operations are async  
❌ **Using the wrong event name** - Event names must match exactly  

## Next Steps

- **[02-events-simple](../02-events-simple/)** - Learn more about event publishing and subscribing patterns
- **08-planner-worker-basic (coming soon)** - See the full Trinity pattern with Planner, Worker, and Tool agents

---

**📖 Additional Resources:**
- [Event Service Documentation](../../docs/EVENT_PATTERNS.md)
- [Platform Architecture](../../ARCHITECTURE.md)
