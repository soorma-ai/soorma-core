# 04 - Working Memory (Distributed Request/Response Workflow)

**Concepts:** Working memory, Plan-scoped state, Distributed async workflow, Request/Response orchestration, WorkflowState helper  
**Difficulty:** Intermediate  
**Prerequisites:** [01-hello-world](../01-hello-world/), [02-events-simple](../02-events-simple/)

## What You'll Learn

- How to share plan-scoped state across distributed agents
- How to use WorkflowState for clean, multi-tenant state management
- How to orchestrate with Request/Response (no chaining)
- Why working memory enables async, distributed workflows

**Note:** This example uses a fixed 3-task workflow (research → draft → review) to demonstrate WorkflowState mechanics. For dynamic, LLM-based task generation from user goals, see example 08-planner-worker-basic (coming soon).

## Prerequisites

**Multi-tenancy:**

This example uses `tenant_id` and `user_id` from the event envelope (set by the client when publishing). Agents extract these IDs from the `EventEnvelope` and pass them to `WorkflowState` to ensure proper isolation.

## The Pattern

**Working Memory** is for temporary plan-scoped state shared across agents collaborating on a goal. In this example:
- The client requests a workflow from the planner and specifies a response event
- The planner stores client-request info in working memory (correlation_id, response_event, IDs)
- The planner requests tasks from the worker and LISTENS for responses
- The worker executes tasks and responds directly to the planner
- The planner decides next steps and finally responds to the client

Everything is scoped by `plan_id`, ensuring isolation across workflows.

## Code Walkthrough

### Raw Memory API Usage ([memory_api_demo.py](memory_api_demo.py))

Direct usage of Memory API using standalone MemoryClient (more verbose):

```python
from soorma.memory.client import MemoryClient

memory = MemoryClient()

# Store state (requires tenant_id/user_id for each call)
await memory.set_plan_state(
    plan_id=plan_id,
    key="research_data",
    value={"findings": [...]},
    tenant_id=tenant_id,
    user_id=user_id
)

# Retrieve state
response = await memory.get_plan_state(
    plan_id, 
    "research_data",
    tenant_id=tenant_id,
    user_id=user_id
)
data = response.value
```

**Note:** This is the low-level API. Agents should use `WorkflowState` helper instead.

### WorkflowState Helper (Recommended)

The `WorkflowState` wrapper simplifies the API by 8x:

```python
from soorma.workflow import WorkflowState

# Create helper (tenant_id/user_id from event envelope)
state = WorkflowState(
    context.memory, 
    plan_id,
    tenant_id=event.tenant_id,
    user_id=event.user_id
)

# Clean operations
await state.set("research_data", {"findings": [...]})
data = await state.get("research_data")
await state.record_action("research.completed")
history = await state.get_action_history()
```

**Benefits:** No repeated parameters, built-in action tracking, proper multi-tenant isolation.

### Planner Agent ([planner.py](planner.py))

Orchestrates by storing client info and listening for worker responses:

```python
@planner.on_event("workflow.start", topic=EventTopic.ACTION_REQUESTS)
async def handle_workflow_start(event: EventEnvelope, context: PlatformContext):
    plan_id = str(uuid.uuid4())
    state = WorkflowState(context.memory, plan_id, 
                         tenant_id=event.tenant_id, user_id=event.user_id)
    
    # CRITICAL: Store client request info (correlation_id, response_event)
    await state.set("client_correlation_id", event.correlation_id)
    await state.set("client_response_event", event.response_event or "workflow.completed")
    
    # Initialize workflow (fixed tasks for demo)
    await state.set("tasks", ["research", "draft", "review"])
    await state.set("current_task_index", 0)
    
    # Start workflow - request first task
    await context.bus.request(
        event_type="task.assigned",
        response_event="task.completed",
        data={"plan_id": plan_id, "task": "research"},
        correlation_id=plan_id,  # Use plan_id so planner knows to listen
        tenant_id=event.tenant_id,
        user_id=event.user_id,
    )
```

**Response handler for task completions:**

```python
@planner.on_event("task.completed", topic=EventTopic.ACTION_RESULTS)
async def handle_task_completed(event: EventEnvelope, context: PlatformContext):
    plan_id = event.data.get("plan_id")
    state = WorkflowState(context.memory, plan_id,
                         tenant_id=event.tenant_id, user_id=event.user_id)
    
    # Store task result
    await state.set(event.data.get("task"), event.data.get("result"))
    
    # Decide next step
    tasks = await state.get("tasks")
    current_index = await state.get("current_task_index")
    next_index = current_index + 1
    
    if next_index < len(tasks):
        # More tasks - request next one
        await state.set("current_task_index", next_index)
        await context.bus.request(
            event_type="task.assigned",
            response_event="task.completed",
            data={"plan_id": plan_id, "task": tasks[next_index]},
            correlation_id=plan_id,
            tenant_id=event.tenant_id,
            user_id=event.user_id,
        )
    else:
        # All done - respond to client with stored info
        client_correlation_id = await state.get("client_correlation_id")
        client_response_event = await state.get("client_response_event")
        
        results = {t: await state.get(t) for t in tasks}
        await context.bus.respond(
            event_type=client_response_event,
            data={"plan_id": plan_id, "results": results},
            correlation_id=client_correlation_id,
            tenant_id=event.tenant_id,
            user_id=event.user_id,
        )
```

**How it applies the concepts:**
- Stores client request info in working memory before delegating to workers
- Uses `plan_id` as correlation_id in requests (so planner knows which response matches which request)
- Listens for `task.completed` responses from workers
- Retrieves client info from working memory when workflow completes
- Responds back to client using client-specified response_event

### Worker Agent ([worker.py](worker.py))

Executes tasks and updates shared state, responding to the planner’s expected response event:

```python
from soorma_common.events import EventEnvelope, EventTopic
from soorma.context import PlatformContext

@worker.on_event("task.assigned", topic=EventTopic.ACTION_REQUESTS)
async def handle_task(event: EventEnvelope, context: PlatformContext):
    plan_id = event.data.get("plan_id")
    task = event.data.get("task")
    
    # Access shared state via plan_id
    state = WorkflowState(context.memory, plan_id,
                         tenant_id=event.tenant_id, user_id=event.user_id)
    
    # Can read results from previous tasks
    research_data = await state.get("research", {})
    
    # Execute task and store result
    result = execute_task(task, research_data)
    await state.set(task, result)
    await state.record_action(f"{task}.completed")
    
    # Respond to planner
    await context.bus.respond(
        event_type=event.response_event or "task.completed",
        data={"plan_id": plan_id, "task": task, "result": result},
        correlation_id=event.correlation_id,
        tenant_id=event.tenant_id,
        user_id=event.user_id,
    )
```

**How it applies the concepts:**
- Accesses shared state using same `plan_id`
- Can read/build on results from previous tasks in the workflow
- Stores results for next agent to access
- Responds directly to planner (worker doesn't know about client)

## Running the Example

### Prerequisites

```bash
# From soorma-core root directory
soorma dev --build
```

### Step 1: Explore Raw Memory API

```bash
cd examples/04-memory-working
python memory_api_demo.py
```

Demonstrates direct Memory API calls before the helper.

### Step 2: Run the Workflow

```bash
# Terminal 1: Start agents
./start.sh

# Terminal 2: Start workflow  
python client.py
```

Watch the workflow: client → planner (stores plan) → workers (read/write shared state) → planner (listen for responses) → client (final response).

## Key Takeaways

**Working memory is for plan-scoped, temporary state:**
- Isolated by `plan_id` (not shared across workflows)
- Shared between agents via tenant/user scoping
- Perfect for multi-step tasks where agents build on each other's work

**Orchestration pattern with distributed responses:**
- Planner stores client info BEFORE delegating to workers
- Uses `plan_id` as correlation_id for its internal requests
- Workers respond without knowing about the original client
- Planner collects responses and orchestrates next steps

**WorkflowState helper reduces boilerplate by 8x:**
- Handles memory client lifecycle
- Automatically includes tenant_id/user_id in all operations
- Provides action history tracking out of the box
- Better than manual API for most workflows

## Best Practices

1. **Always scope by plan_id**: Ensures isolation between workflows
2. **Use WorkflowState helper**: Simpler than manual Memory API calls
3. **Store client context in planner**: Before delegating, never lost when workers respond
4. **Use default values in get()**: `get(key, default_value)` prevents errors on missing keys
5. **Track action history**: Audit trail helps debugging distributed workflows

### Common Patterns

**Pattern: Task Handoff**
```python
# Agent A stores result
await state.set("research_data", results)

# Agent B retrieves result
research_data = await state.get("research_data", {})
```

**Pattern: Progress Tracking**
```python
await state.record_action("research.completed")
await state.record_action("analysis.completed")

history = await state.get_action_history()  # Full audit trail
```

**Pattern: Cleanup After Completion**
```python
# After workflow is done and client has been notified:
# Clean up all working memory for the plan
count = await state.cleanup()
print(f"Cleaned up {count} state entries")

# Or delete a single key (e.g., for sensitive data):
deleted = await state.delete("api_key")
if deleted:
    print("Sensitive data removed")
```

**When to cleanup:**
- After plan/workflow completes
- When reclaiming resources in long-running systems  
- Before archiving workflow execution
- For sensitive data (credentials, PII) - immediate cleanup recommended

See [memory_api_demo.py](memory_api_demo.py) and [planner.py](planner.py) for additional patterns.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Memory Service not responding" | Ensure `soorma dev` is running and Memory Service is healthy |
| "KeyError: 'goal'" | Planner must initialize state before workers try to read it |
| "State not shared between agents" | Verify all agents use identical plan_id in event data |
| "WorkflowState import error" | Install SDK: `pip install -e ../../sdk/python` |

## Next Steps

- **[05-memory-semantic](../05-memory-semantic/)** - RAG and knowledge management with LLM routing (recommended next)
- **[06-memory-episodic](../06-memory-episodic/)** - Conversation history and audit trails
- **[08-planner-worker-basic](../08-planner-worker-basic/)** - Full Planner-Worker pattern (coming soon)
- **[09-app-research-advisor](../09-app-research-advisor/)** - Advanced choreography (coming soon)
- **[docs/MEMORY_PATTERNS.md](../../docs/MEMORY_PATTERNS.md)** - Deep dive on memory types

## Additional Resources

- [Memory Patterns Guide](../../docs/MEMORY_PATTERNS.md)
- [WorkflowState API Reference](../../sdk/python/README.md#workflowstate)
- [Design Patterns](../../docs/DESIGN_PATTERNS.md) - Trinity and Choreography patterns
