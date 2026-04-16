# 01-hello-tool - Calculator Tool Example

**Concepts:** Tool pattern, stateless operations, synchronous request/response, multiple handlers, auth token provider  
**Difficulty:** Beginner  
**Time:** 5 minutes  
**Prerequisites:** None (first example!)

---

## What You'll Learn

This example demonstrates the **Tool pattern** - the simplest agent model in Soorma:

- ✅ **Multiple `@on_invoke()` handlers** - One tool, multiple operations
- ✅ **Stateless operations** - No memory between requests
- ✅ **Synchronous responses** - Handler returns result immediately
- ✅ **InvocationContext** - Lightweight request context
- ✅ **Caller-specified routing** - Response goes where caller wants
- ✅ **Error handling** - Graceful handling of edge cases (division by zero)
- ✅ **Shared auth provider** - Example bootstraps once and injects bearer-token management into both tool and client

---

## The Tool Pattern

**Tools** are the simplest agent model:

| Characteristic | Tool |
|----------------|------|
| **State** | Stateless (no memory) |
| **Response** | Synchronous (returns immediately) |
| **Completion** | Automatic (framework handles it) |
| **Use Case** | Simple calculations, lookups, transformations |

**When to use Tools:**
- ✅ Pure functions (output depends only on input)
- ✅ Fast operations (< 1 second)
- ✅ No need to wait for external events
- ✅ No need to delegate to other agents

**When NOT to use Tools:**
- ❌ Need to maintain state across requests
- ❌ Need to wait for async completion
- ❌ Need to delegate to other agents
- ❌ Long-running operations

*(For those cases, use [Worker pattern](../02-hello-worker) instead)*

---

## Auth Provider Concept

This example talks to secured Soorma infrastructure services, so the calculator tool and the driver client both need bearer tokens.

Rather than hard-coding tenant IDs or building `Authorization` headers manually, the example uses the shared auth-provider pattern:

1. `start.sh` primes `examples.shared.auth` for `01-hello-tool`.
2. The shared helper bootstraps the example tenant once and persists metadata under `.soorma/01-hello-tool-identity.json`.
3. The same provider requests, caches, and refreshes JWTs when the client or tool needs them.
4. The provider is injected through `auth_token_provider=...` so the example code stays focused on Tool behavior rather than auth plumbing.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Client                                │
│  • Publishes request to action-requests                      │
│  • Subscribes to response on action-results                  │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            │ math.add.requested
                            │ (on action-requests topic)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Calculator Tool                            │
│  • Listens on action-requests topic                          │
│  • Has 4 handlers:                                           │
│    - @on_invoke("math.add.requested")                        │
│    - @on_invoke("math.subtract.requested")                   │
│    - @on_invoke("math.multiply.requested")                   │
│    - @on_invoke("math.divide.requested")                     │
│  • Returns result synchronously                              │
│  • Publishes to caller's response_event                      │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            │ math.result
                            │ (on action-results topic)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                        Client                                │
│  • Receives result                                           │
└─────────────────────────────────────────────────────────────┘
```

---

## Code Walkthrough

### 1. Tool Creation

```python
from examples.shared.auth import build_example_token_provider

EXAMPLE_TOKEN_PROVIDER = build_example_token_provider("01-hello-tool", __file__)

calculator = Tool(
    name="calculator-tool",
    description="Performs basic arithmetic operations",
    default_response_event="calculator.completed",  # Fallback
    auth_token_provider=EXAMPLE_TOKEN_PROVIDER,
)
```

**Key points:**
- `default_response_event` is optional - used if caller doesn't specify one
- Tool has no state - just configuration
- The auth token provider is injected once at initialization so the tool can connect to secured infrastructure without embedding auth logic into handlers

### 2. Handler Registration

```python
@calculator.on_invoke("math.add.requested")
async def handle_add(request: InvocationContext, context: PlatformContext):
    a = request.data.get("a", 0)
    b = request.data.get("b", 0)
    result = a + b
    
    return {
        "request_id": request.request_id,
        "operation": "add",
        "result": result,
        "inputs": {"a": a, "b": b}
    }
```

**Key points:**
- `@on_invoke(event_type)` - Registers handler for specific event type
- Handler receives `InvocationContext` with request data
- Handler returns dict - Tool auto-publishes to response_event
- No need to manually publish response!

### 3. Multiple Handlers

```python
@calculator.on_invoke("math.add.requested")
async def handle_add(...): ...

@calculator.on_invoke("math.subtract.requested")
async def handle_subtract(...): ...

@calculator.on_invoke("math.multiply.requested")
async def handle_multiply(...): ...

@calculator.on_invoke("math.divide.requested")
async def handle_divide(...): ...
```

**Key points:**
- One tool can handle multiple event types
- Each handler is independent
- Framework routes events to correct handler

### 4. Error Handling

```python
@calculator.on_invoke("math.divide.requested")
async def handle_divide(request: InvocationContext, context: PlatformContext):
    a = request.data.get("a", 0)
    b = request.data.get("b", 0)
    
    if b == 0:
        return {
            "request_id": request.request_id,
            "operation": "divide",
            "error": "Division by zero",
            "inputs": {"a": a, "b": b}
        }
    
    result = a / b
    return {"request_id": request.request_id, "result": result}
```

**Key points:**
- Handlers can return error responses
- No exceptions thrown - graceful degradation
- Client receives structured error

### 5. InvocationContext

```python
async def handle_add(request: InvocationContext, context: PlatformContext):
    # Access request data
    a = request.data.get("a")
    b = request.data.get("b")
    
    # Access metadata
    request_id = request.request_id
    event_type = request.event_type
    response_event = request.response_event  # Where to send response
    correlation_id = request.correlation_id  # For tracing
```

**InvocationContext fields:**
- `request_id` - Unique ID for this request
- `event_type` - Event that triggered this handler
- `data` - Request payload
- `response_event` - Where to send response (caller-specified)
- `response_topic` - Topic to publish on (defaults to "action-results")
- `correlation_id` - For distributed tracing
- `tenant_id`, `user_id` - Auth context

### 6. Client Auth + Event Publish

```python
from examples.shared.auth import build_example_token_provider

token_provider = build_example_token_provider("01-hello-tool", __file__)
await token_provider.get_token()
tenant_id = await token_provider.get_platform_tenant_id()
user_id = await token_provider.get_bootstrap_admin_principal_id()

client = EventClient(
    agent_id="calculator-client",
    source="calculator-client",
    auth_token_provider=token_provider,
)

await client.publish(
    event_type=event_type,
    topic=EventTopic.ACTION_REQUESTS,
    data={"a": a, "b": b},
    correlation_id=correlation_id,
    response_event="math.result",
    response_topic="action-results",
    tenant_id=tenant_id,
    user_id=user_id,
)
```

**Key points:**
- The client uses the same shared auth-provider abstraction as the tool
- Tenant and bootstrap-admin identifiers come from the persisted bootstrap payload, not hard-coded constants
- `EventClient` receives the provider directly and resolves bearer tokens when connecting or publishing

---

## Running the Example

### Prerequisites

```bash
# 1. Make sure you're in the soorma-core root directory
cd /path/to/soorma-core

# 2. Activate virtual environment
source .venv/bin/activate

# 3. Install SDK (if not already done)
pip install -e sdk/python

# 4. Start platform services (in a separate terminal)
soorma dev --build
```

The first example run also creates `.soorma/01-hello-tool-identity.json` so later runs reuse the same bootstrapped principal instead of onboarding a new tenant every time.

### Step 1: Start the Tool

In terminal 1:

```bash
cd examples/01-hello-tool
./start.sh
```

You should see:

```
✓ Example identity bootstrap and token cache ready
Starting Calculator Tool...
Listening for events: ['math.add.requested', 'math.subtract.requested', 'math.multiply.requested', 'math.divide.requested']
Publishing to events: ['calculator.completed']
```

### Step 2: Run the Client

In terminal 2:

```bash
cd examples/01-hello-tool

# Addition
python client.py --operation add --a 10 --b 5

# Subtraction
python client.py --operation subtract --a 20 --b 8

# Multiplication
python client.py --operation multiply --a 7 --b 6

# Division
python client.py --operation divide --a 100 --b 4

# Division by zero (error case)
python client.py --operation divide --a 100 --b 0
```

### Expected Output

**Client (terminal 2):**
```
📤 Sending add request: 10.0 add 5.0
   Request ID: calc-a3b7f291
   Event Type: math.add.requested
   Response Event: math.result
📥 Response received:
   ✅ Result: 15.0
   Operation: add
   Inputs: {'a': 10.0, 'b': 5.0}
```

**Tool (terminal 1):**
```
[ADD] 10.0 + 5.0 = 15.0
```

---

## Key Concepts

### 1. Topics vs Event Types

**Topics** = Infrastructure routing (where messages flow)
- `action-requests` - All action requests flow here
- `action-results` - All action results flow here

**Event Types** = Semantic identifiers (what the message means)
- `math.add.requested` - Semantic meaning: "please add two numbers"
- `math.result` - Semantic meaning: "here's your calculation result"

**Why separate?**
- Topics are fixed infrastructure channels
- Event types are dynamic business semantics
- One topic carries many event types

### 2. Caller-Specified Response Routing

```python
request.data = {
    "response_event": "math.result",  # ← Caller tells tool where to send response
    "a": 10,
    "b": 5
}
```

**Why?**
- Caller might be listening for custom event
- Multiple callers can use same tool with different response routing
- Tool doesn't hardcode where responses go

### 3. Stateless Operations

```python
@calculator.on_invoke("math.add.requested")
async def handle_add(request: InvocationContext, context: PlatformContext):
    # No access to previous requests
    # No shared state
    # Output depends ONLY on input
    result = request.data["a"] + request.data["b"]
    return {"result": result}
```

**Benefits:**
- Simple to reason about
- Easy to test
- Can scale horizontally
- No memory leaks

### 4. Automatic Response Publishing

```python
# You write:
return {"result": 42}

# Framework does:
response = EventEnvelope(
    type=request.response_event,      # From request
    data={"result": 42},              # Your return value
    topic=EventTopic.ACTION_RESULTS,  # Standard topic
    correlation_id=request.correlation_id,  # Preserved
)
await bus.publish(response)
```

You don't need to manually publish responses!

---

## Comparison: Tool vs Worker

| Feature | Tool (this example) | Worker (next example) |
|---------|---------------------|----------------------|
| **State** | Stateless | Stateful |
| **Response** | Synchronous | Asynchronous |
| **Completion** | Auto | Manual (`task.complete()`) |
| **Delegation** | No | Yes |
| **Use Case** | Simple calculations | Multi-step workflows |
| **Example** | Calculator | Research report generation |

---

## Troubleshooting

### Tool not receiving requests?

Check:
1. ✅ Platform services running? (`docker ps` should show redis, nats)
2. ✅ Tool started? (terminal 1 should show "Listening for events")
3. ✅ Correct event type in client? (must match `@on_invoke()` decorator)

### Client timeout?

Check:
1. ✅ Tool is running in terminal 1
2. ✅ No errors in tool terminal
3. ✅ Client using correct operation name

### Import errors?

Check:
1. ✅ Virtual environment activated
2. ✅ SDK installed (`pip install -e sdk/python`)
3. ✅ Running from correct directory

---

## Experiments

Try modifying the code:

1. **Add a new operation** (e.g., power, modulo)
   - Add `@on_invoke("math.power.requested")` handler
   - Update client to support new operation

2. **Add input validation**
   - Check if `a` and `b` are provided
   - Return error if missing

3. **Add response schema**
   - Use `response_schema` parameter in `@on_invoke()`
   - See validation in action

4. **Change response event**
   - Modify client to use different response_event
   - See tool adapt automatically

---

## Next Steps

Now that you understand the **Tool pattern**, explore:

1. **[02-hello-worker](../02-hello-worker)** - Asynchronous task handling *(coming soon)*
2. **[03-events-simple](../03-events-simple)** - Event pub/sub patterns
3. **[07-tool-discovery](../07-tool-discovery)** - Dynamic tool discovery *(coming soon)*

---

## Key Takeaways

✅ **Tools are stateless** - No memory between requests  
✅ **Tools return immediately** - Handler returns result synchronously  
✅ **Multiple handlers per tool** - Use `@on_invoke()` for each event type  
✅ **Auto-response publishing** - Framework handles publishing for you  
✅ **Auth is injected, not hand-coded** - The shared provider handles bootstrap, token caching, and refresh for both client and tool  
✅ **Caller-specified routing** - Response goes where caller wants  
✅ **Simple and fast** - Perfect for pure functions  

**Remember:** If you need state, delegation, or async completion, use [Worker pattern](../02-hello-worker) instead!

---

## Questions?

- **Issues:** [GitHub Issues](https://github.com/soorma-ai/soorma-core/issues)
- **Discussions:** [GitHub Discussions](https://github.com/soorma-ai/soorma-core/discussions)
- **Discord:** [Join our community](https://discord.gg/soorma)

---

**Happy coding! 🚀**
