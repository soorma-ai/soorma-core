# 01 - Hello World

**Concepts:** Worker pattern, Event handling, Request/Response, Auth token provider  
**Difficulty:** Beginner  
**Prerequisites:** None

This example now bootstraps a local identity domain under the shared `.soorma/` directory on first run, then uses a reusable token provider to request, cache, and refresh JWTs for later runs.

## What You'll Learn

- How to create a Worker agent
- How to handle events with `@worker.on_event()` decorator
- **Best practice: Use `respond()` for request/response patterns**
- How clients send requests and receive responses
- Why secured infrastructure access is injected through an auth token provider instead of hard-coded headers or one-off token calls

## The Pattern

The Worker pattern is a simple way to build reactive agents in Soorma. A Worker:
1. Declares its capabilities (what it can do)
2. Registers event handlers using `@worker.on_event()` decorator
3. Receives events on subscribed topics
4. Processes the request
5. Sends response using `context.bus.respond()` convenience method

**Key advantage**: The `respond()` method is semantically correct for request/response patterns - it knows to publish responses to the `action-results` topic and requires a correlation_id to link responses to their requests.

## Auth Provider Concept

The example talks to secured Soorma infrastructure services, so both the worker and the client need a way to obtain bearer tokens without embedding auth logic into every event call.

This is what the auth token provider does:

1. It bootstraps the example's local identity metadata once and persists it under `.soorma/`.
2. It requests JWTs from Identity Service when needed.
3. It caches and refreshes those JWTs before expiry.
4. It is injected into SDK clients and agents through `auth_token_provider`, so the rest of the example can focus on Worker and Event patterns instead of auth plumbing.

In this example, the provider comes from `examples.shared.auth.build_example_token_provider(...)`. The worker hands it to `Worker(...)`, and the client hands it to `EventClient(...)`.

## Code Walkthrough

### Worker Agent ([worker.py](worker.py))

The Worker demonstrates the basic pattern:

```python
from examples.shared.auth import build_example_token_provider

EXAMPLE_NAME = "01-hello-world"
EXAMPLE_TOKEN_PROVIDER = build_example_token_provider(EXAMPLE_NAME, __file__)

worker = Worker(
    name="hello-worker",
    description="A simple greeting agent",
    capabilities=["greeting"],
    events_consumed=[GREETING_REQUESTED_EVENT],
    events_produced=[GREETING_COMPLETED_EVENT],
    auth_token_provider=EXAMPLE_TOKEN_PROVIDER,
)

@worker.on_event("greeting.requested", topic=EventTopic.ACTION_REQUESTS)
async def handle_greeting(event: EventEnvelope, context: PlatformContext):
    data = event.data or {}
    name = data.get("name", "World")
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
- `EXAMPLE_TOKEN_PROVIDER` is injected once into the worker so all infrastructure-facing SDK calls use the same bearer-token lifecycle
- `events_consumed` and `events_produced` declare the agent's interface
- `@worker.on_event()` with `topic=EventTopic.ACTION_REQUESTS` subscribes to incoming requests
- `event.response_event` lets clients specify what event type they expect as response
- `context.bus.respond()` automatically publishes to `action-results` topic
- `correlation_id` links the response back to the original request

### Client ([client.py](client.py))

The Client demonstrates how to make requests and receive responses:

```python
from examples.shared.auth import build_example_token_provider

token_provider = build_example_token_provider("01-hello-world", __file__)
await token_provider.get_token()
tenant_id = await token_provider.get_platform_tenant_id()
user_id = await token_provider.get_bootstrap_admin_principal_id()

client = EventClient(
    agent_id="hello-client",
    source="hello-client",
    auth_token_provider=token_provider,
)

# Send request with response_event metadata
await client.publish(
    event_type="greeting.requested",
    topic=EventTopic.ACTION_REQUESTS,
    data={"name": name},
    correlation_id=str(uuid4()),
    response_event="greeting.completed",
    response_topic="action-results",
    tenant_id=tenant_id,
    user_id=user_id,
)

# Listen for response
@client.on_event("greeting.completed", topic=EventTopic.ACTION_RESULTS)
async def on_response(event: EventEnvelope):
    greeting = event.data.get("greeting")
    print(f"Got greeting: {greeting}")
```

**How it applies the concepts:**
- `examples.shared.auth.build_example_token_provider()` returns a reusable auth token provider that bootstraps once, persists the example principal under `.soorma/01-hello-world-identity.json`, and refreshes JWTs only when needed
- The same provider abstraction also exposes the bootstrapped `platform_tenant_id` and bootstrap admin principal ID so the example no longer relies on hard-coded tenant values
- The client passes that provider into `EventClient(...)` instead of manually managing `Authorization` headers
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

The first example run also creates `.soorma/01-hello-world-identity.json` so subsequent runs reuse the same bootstrapped principal instead of onboarding a new tenant every time.

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

The worker is configured with the shared example token provider, which injects bearer tokens into its registry, event-bus, memory, and tracker clients on demand.

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

The client reuses the same persisted example principal, then lets the shared token provider request and cache bearer tokens for Event Service access.

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
✅ **Auth is injected, not hand-coded** - The example uses one reusable auth token provider for bootstrap, token caching, and refresh  
✅ **Everything is asynchronous** - All I/O operations use `async/await`  

## Common Mistakes to Avoid

❌ **Confusing `publish()` with `respond()`** - Use `respond()` for request/response, not `publish()`  
❌ **Forgetting correlation_id** - Without it, clients can't match responses to requests  
❌ **Not extracting `response_event` from request** - Let clients specify where responses go  
❌ **Not awaiting async calls** - All I/O operations must be `await`ed  
❌ **Using wrong topic** - Requests go to `ACTION_REQUESTS`, responses to `ACTION_RESULTS`  
❌ **Skipping token provider setup** - secured local services now require the example to configure a bearer-token provider before connecting  

## Next Steps

- **[02-events-simple](../02-events-simple/)** - Learn more event publishing patterns and topics
- **[04-memory-working](../04-memory-working/)** - See request/response in a more complex orchestration scenario
- **[AGENT_PATTERNS](../../docs/AI_ASSISTANT_GUIDE.md)** - Understand Planner/Worker/Tool patterns for AI agents

---

**📖 Additional Resources:**
- [Event System Documentation](../../docs/event_system/README.md)
- [Platform Architecture](../../ARCHITECTURE.md)
