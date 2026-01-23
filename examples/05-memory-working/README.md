# 05 - Working Memory (Plan State Management)

**Concepts:** Working memory, Plan-scoped state, Multi-agent collaboration, WorkflowState helper  
**Difficulty:** Intermediate  
**Prerequisites:** [01-hello-world](../01-hello-world/), [02-events-simple](../02-events-simple/)

## What You'll Learn

- How to share state between agents in a workflow
- How to use WorkflowState helper for clean state management
- When to use working memory vs other memory types
- Plan-scoped data isolation

## Prerequisites

**Multi-tenancy:**

This example requires tenant_id and user_id to be provided at runtime when memory operations are invoked. In production, these typically come from the event envelope or authentication context. For this example, the client script includes them in the event payload, and the agents extract them from the event data.

## The Pattern

**Working Memory** is for temporary, plan-scoped state that needs to be shared across multiple agents working on the same goal. It's perfect for:
- Multi-agent workflows (Planner → Worker → Worker)
- Passing data between choreographed agents
- Tracking workflow progress
- Temporary state that doesn't need long-term persistence

State is scoped to a `plan_id`, ensuring isolation between different workflows.

## Code Walkthrough

### Manual State Management ([manual_state.py](manual_state.py))

Direct usage of Memory API using standalone MemoryClient (more verbose):

```python
from soorma.memory.client import MemoryClient

# For example purposes - use hardcoded tenant/user IDs
# In production, these come from authentication/event context
tenant_id = "00000000-0000-0000-0000-000000000000"
user_id = "00000000-0000-0000-0000-000000000000"

# Create Memory client directly
memory = MemoryClient()
plan_id = str(uuid.uuid4())

# Store state (must provide tenant_id/user_id for each call)
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

# Clean up
await memory.close()
```

**Note:** This demonstrates the low-level Memory Service API. In agent handlers, you would extract tenant_id/user_id from the event envelope rather than hardcoding them.

### WorkflowState Helper ([planner.py](planner.py))

Simplified API (recommended):

```python
from soorma.workflow import WorkflowState

# Extract tenant_id and user_id from event envelope (infrastructure metadata)
tenant_id = event.get("tenant_id", "00000000-0000-0000-0000-000000000000")
user_id = event.get("user_id", "00000000-0000-0000-0000-000000000001")

# Create WorkflowState with runtime IDs
state = WorkflowState(
    context.memory, 
    plan_id,
    tenant_id=tenant_id,
    user_id=user_id
)

# Record actions
await state.record_action("research.started")

# Store data
await state.set("research_data", {"findings": [...]})

# Retrieve data
data = await state.get("research_data")

# Get action history
history = await state.get_action_history()
```

**Benefits:**
- Proper multi-tenancy isolation
- Single agent serves multiple users
- 8:1 code reduction vs manual approach
- Built-in action history tracking
- Cleaner error handling
- Consistent patterns

### Planner Agent ([planner.py](planner.py))

Decomposes goals and stores task state:

```python
@planner.on_event("goal.received", topic="action-requests")
async def handle_goal(event, context):
    data = event.get("data", {})
    goal = data.get("goal")
    plan_id = str(uuid.uuid4())
    
    # Extract tenant_id and user_id from event envelope (infrastructure metadata)
    tenant_id = event.get("tenant_id", "00000000-0000-0000-0000-000000000000")
    user_id = event.get("user_id", "00000000-0000-0000-0000-000000000001")
    
    # Initialize workflow state with runtime IDs
    state = WorkflowState(
        context.memory, 
        plan_id,
        tenant_id=tenant_id,
        user_id=user_id
    )
    await state.set("goal", goal)
    await state.set("status", "planning")
    
    # Decompose into tasks
    tasks = ["research", "draft", "review"]
    await state.set("tasks", tasks)
    await state.set("current_task_index", 0)
    
    # Trigger first task (pass IDs as envelope metadata)
    await context.bus.publish(
        event_type="task.assigned",
        topic="action-requests",
        data={
            "plan_id": plan_id,
            "task": tasks[0],
            "goal": goal,
            "task_index": 0
        },
        tenant_id=tenant_id,
        user_id=user_id,
    )
```

### Worker Agent ([worker.py](worker.py))

Executes tasks and updates shared state:

```python
@worker.on_event("task.assigned", topic="action-requests")
async def handle_task(event, context):
    data = event.get("data", {})
    plan_id = data.get("plan_id")
    task = data.get("task")
    
    # Extract tenant_id and user_id from event envelope (infrastructure metadata)
    tenant_id = event.get("tenant_id", "00000000-0000-0000-0000-000000000000")
    user_id = event.get("user_id", "00000000-0000-0000-0000-000000000001")
    
    # Access plan state with runtime IDs
    state = WorkflowState(
        context.memory, 
        plan_id,
        tenant_id=tenant_id,
        user_id=user_id
    )
    goal = await state.get("goal")
    
    # Execute task
    result = f"Completed {task} for: {goal}"
    
    # Store result
    await state.record_action(f"{task}.completed")
    await state.set(f"{task}_result", result)
    
    # Notify completion (pass IDs as envelope metadata)
    await context.bus.publish(
        event_type="task.completed",
        topic="action-results",
        data={
            "plan_id": plan_id,
            "task": task,
            "result": result
        },
        tenant_id=tenant_id,
        user_id=user_id,
    )
```

### Coordinator Pattern ([coordinator.py](coordinator.py))

Advances workflow through multiple stages:

```python
@coordinator.on_event("task.completed", topic="action-results")
async def handle_task_completion(event, context):
    data = event.get("data", {})
    plan_id = data.get("plan_id")
    
    # Extract tenant_id and user_id from event envelope (infrastructure metadata)
    tenant_id = event.get("tenant_id", "00000000-0000-0000-0000-000000000000")
    user_id = event.get("user_id", "00000000-0000-0000-0000-000000000001")
    
    state = WorkflowState(
        context.memory, 
        plan_id,
        tenant_id=tenant_id,
        user_id=user_id
    )
    tasks = await state.get("tasks")
    current_index = await state.get("current_task_index")
    
    # Move to next task
    next_index = current_index + 1
    
    if next_index < len(tasks):
        await state.set("current_task_index", next_index)
        # Trigger next task...
    else:
        # All tasks complete
        await state.set("status", "completed")
```

## Running the Example

### Prerequisites

Make sure platform services are running:

```bash
# From soorma-core root directory
soorma dev --build
```

### Step 1: Manual State Example

```bash
cd examples/05-memory-working
python manual_state.py
```

See direct Memory API usage.

### Step 2: Run Multi-Agent Workflow

```bash
# Terminal 1: Start all agents
./start.sh

# Terminal 2: Submit goal
python client.py "Write a blog post about Docker"
```

The start.sh script runs planner, worker, and coordinator together. Watch state flow between agents!

## Key Takeaways

### When to Use Working Memory

✅ **Use working memory for:**
- Temporary workflow state
- Data shared between agents in a plan
- Progress tracking
- Multi-step task decomposition

❌ **Don't use working memory for:**
- Long-term knowledge (use Semantic Memory)
- Conversation history (use Episodic Memory)
- Cross-plan data (not isolated by plan_id)

### Best Practices

1. **Always use plan_id**: Ensures state isolation between workflows
2. **Use WorkflowState helper**: Reduces boilerplate by 8x
3. **Track action history**: `record_action()` creates audit trail
4. **Provide default values**: Always use `get(key, default)` to handle missing keys gracefully
5. **Clean up after completion**: Delete plan state when workflow finishes (future enhancement)
6. **Handle missing keys**: `get()` returns None if key doesn't exist, use defaults for safety

### Common Patterns

**Pattern 1: Plan Initialization**
```python
data = event.get("data", {})
plan_id = str(uuid.uuid4())

# Extract IDs from event envelope (infrastructure metadata)
tenant_id = event.get("tenant_id", "00000000-0000-0000-0000-000000000000")
user_id = event.get("user_id", "00000000-0000-0000-0000-000000000001")

state = WorkflowState(
    context.memory, 
    plan_id,
    tenant_id=tenant_id,
    user_id=user_id
)

await state.set("goal", goal_text)
await state.set("status", "in_progress")
await state.set("tasks", task_list)
```

**Pattern 2: Task Handoff**
```python
# Worker A stores result
await state.set("research_data", results)
await state.record_action("research.completed")

# Worker B retrieves result
research_data = await state.get("research_data")
# ... use data ...
```

**Pattern 3: Progress Tracking**
```python
# Record each step
await state.record_action("step1.completed")
await state.record_action("step2.completed")

# Check progress
history = await state.get_action_history()
# ["step1.completed", "step2.completed"]
```

**Pattern 4: Conditional Workflow**
```python
status = await state.get("status")

if status == "needs_revision":
    # Go back to drafting
    await state.set("current_stage", "draft")
elif status == "approved":
    # Move forward
    await state.set("current_stage", "publish")
```

## Troubleshooting

**"Memory Service not responding"**
- Ensure `soorma dev` is running
- Check Memory Service health: `curl http://localhost:8083/health`

**"KeyError: 'goal'"**
- Ensure planner has initialized state with `set("goal", ...)`
- Worker might be running before planner
- Check plan_id matches between agents

**"State not shared between agents"**
- Verify all agents use the same plan_id
- plan_id must be passed in event data
- Check no typos in state keys

**"WorkflowState import error"**
- Ensure SDK is installed: `pip install soorma-core`
- Or install from source: `pip install -e ../../sdk/python`

## Next Steps

- **[08-planner-worker-basic](../08-planner-worker-basic/)** - Full Planner-Worker pattern (coming soon)
- **[09-app-research-advisor](../09-app-research-advisor/)** - Advanced choreography (coming soon)
- **[docs/MEMORY_PATTERNS.md](../../docs/MEMORY_PATTERNS.md)** - Deep dive on memory types

## Additional Resources

- [Memory Patterns Guide](../../docs/MEMORY_PATTERNS.md)
- [WorkflowState API Reference](../../sdk/python/README.md#workflowstate)
- [Design Patterns](../../docs/DESIGN_PATTERNS.md) - Trinity and Choreography patterns
