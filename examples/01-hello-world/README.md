# 01 - Hello World

**Concepts:** Basic agent lifecycle, Worker pattern, Event handling  
**Difficulty:** Beginner  
**Prerequisites:** None

## What You'll Learn

- How to create a basic Worker agent
- How to register event handlers using decorators
- How to receive and process events
- How to publish events as responses

## The Pattern

The Worker pattern is the simplest way to build a reactive agent in Soorma. A Worker:
1. Registers itself with the platform
2. Subscribes to specific event types
3. Processes events when they arrive
4. Publishes result events

This is the foundation for all Soorma agents.

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
@worker.on_event("greeting.requested")
async def handle_greeting(event, context):
    name = event.get("data", {}).get("name", "World")
    greeting = f"Hello, {name}! 👋"
    
    # Publish result event
    await context.bus.publish(
        event_type="greeting.completed",
        topic="action-results",
        data={"greeting": greeting}
    )
```

**Key Points:**
- `Worker()` creates an agent instance with a name and capabilities
- `events_consumed` declares which events this agent listens to
- `events_produced` declares which events this agent can publish
- `@worker.on_event()` decorator registers handlers for specific event types
- Event handlers receive the `event` data and `context` (platform services)
- Use `context.bus.publish()` to send response events

### Client ([client.py](client.py))

The client demonstrates how to interact with your agent:
1. Creates an `EventClient` to communicate with the platform
2. Subscribes to response events
3. Publishes a request event
4. Waits for and displays the response

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
