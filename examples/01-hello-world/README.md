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

**Key advantage**: The `respond()` method is semantically correct for request/response patterns - it knows to publish responses to the `action-results` topic and requires a correlation_id to link responses to their requests.

## Code Walkthrough

### Worker Agent ([worker.py](worker.py))

The Worker demonstrates the basic pattern:

```python
worker = Worker(
    name="hello-worker",
    description="A simple greeting agent",
    capabilities=["greeting"],
    events_consumed=["greeting.requested"],
    events_produced=["greeting.completed"],
)

@worker.on_event("greeting.requested", topic=EventTopic.ACTION_REQUESTS)
async def handle_greeting(event: EventEnvelope, context: PlatformContext):
    name = event.data.get("name", "World")
    greeting = f"Hello, {name}! 👋"
    
    # Extract response_event from request (caller specifies expected response)
    response_event_type = event.response_event or "greeting.completed"
    
    # Respond using convenience method - cleaner than publish()
    await context.bus.respond(
        event_type=response_event_type,
        data={"greeting": greeting, "name": name},
        correlation_id=event.correlation_id,
    )
```

**How it applies the concepts:**
- `events_consumed` and `events_produced` declare the agent's interface
- `@worker.on_event()` with `topic=EventTopic.ACTION_REQUESTS` subscribes to incoming requests
- `event.response_event` lets clients specify what event type they expect as response
- `context.bus.respond()` automatically publishes to `action-results` topic
- `correlation_id` links the response back to the original request

### Client ([client.py](client.py))

The Client demonstrates how to make requests and receive responses:

```python
# Send request with response_event metadata
await client.publish(
    event_type="greeting.requested",
    topic=EventTopic.ACTION_REQUESTS,
    data={"name": name},
    correlation_id=str(uuid4()),
    response_event="greeting.completed",
    response_topic="action-results",
)

# Listen for response
@client.on_event("greeting.completed", topic=EventTopic.ACTION_RESULTS)
async def on_response(event: EventEnvelope):
    greeting = event.data.get("greeting")
    print(f"Got greeting: {greeting}")
```

**How it applies the concepts:**
- `correlation_id` allows matching responses to requests
- `response_event` and `response_topic` tell the Worker where/what to send back
- Handler receives responses on the specified topic
- This demonstrates the request/response handshake pattern

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

✅ **Workers are reactive** - They respond to events, not direct function calls  
✅ **Event metadata is powerful** - `correlation_id`, `response_event`, and `response_topic` enable clean request/response patterns  
✅ **Decorators simplify wiring** - `@worker.on_event()` automatically handles subscription and topic binding  
✅ **Use the right method** - `respond()` is better than `publish()` for request/response because it's semantically clear  
✅ **Context provides platform access** - Use `context.bus`, `context.memory`, `context.registry` for all platform operations  
✅ **Everything is asynchronous** - All I/O operations use `async/await`  

## Common Mistakes to Avoid

❌ **Confusing `publish()` with `respond()`** - Use `respond()` for request/response, not `publish()`  
❌ **Forgetting correlation_id** - Without it, clients can't match responses to requests  
❌ **Not extracting `response_event` from request** - Let clients specify where responses go  
❌ **Not awaiting async calls** - All I/O operations must be `await`ed  
❌ **Using wrong topic** - Requests go to `ACTION_REQUESTS`, responses to `ACTION_RESULTS`  

## Next Steps

- **[02-events-simple](../02-events-simple/)** - Learn more event publishing patterns and topics
- **[04-memory-working](../04-memory-working/)** - See request/response in a more complex orchestration scenario
- **[AGENT_PATTERNS](../../docs/AI_ASSISTANT_GUIDE.md)** - Understand Planner/Worker/Tool patterns for AI agents

---

**📖 Additional Resources:**
- [Event System Documentation](../../docs/event_system/README.md)
- [Platform Architecture](../../ARCHITECTURE.md)
