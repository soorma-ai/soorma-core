# Hello World - DisCo Trinity Example

This example demonstrates how Planner, Worker, and Tool agents collaborate using the **Soorma SDK classes**.

## SDK Classes Used

```python
from soorma import Planner, Worker, Tool
from soorma.agents.planner import Goal, Plan, Task
from soorma.agents.worker import TaskContext
from soorma.agents.tool import ToolRequest
```

## The Use Case

A simple "Hello World" workflow:
1. **Client** submits a goal: "Say hello to {name}"
2. **Planner** receives the goal and creates a plan with tasks
3. **Worker** receives tasks and executes them
4. **Tool** (optional) performs stateless operations

## SDK Patterns

### Planner - `@planner.on_goal()`

```python
planner = Planner(
    name="hello-planner",
    capabilities=["greeting"],
)

@planner.on_goal("greeting.goal")
async def plan_greeting(goal: Goal, context) -> Plan:
    return Plan(
        goal=goal,
        tasks=[Task(name="greet", assigned_to="hello-worker", data=goal.data)],
    )

planner.run()
```

### Worker - `@worker.on_task()`

```python
worker = Worker(
    name="hello-worker",
    capabilities=["greet"],
)

@worker.on_task("greet")
async def handle_greet(task: TaskContext, context) -> dict:
    await task.report_progress(0.5, "Processing...")
    return {"greeting": f"Hello, {task.data['name']}!"}

worker.run()
```

### Tool - `@tool.on_invoke()`

```python
tool = Tool(
    name="greeting-tool",
    capabilities=["greet"],
)

@tool.on_invoke("greet")
async def handle_greet(request: ToolRequest, context) -> dict:
    return {"greeting": f"Hello, {request.data['name']}!"}

tool.run()
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Event Service                            │
│     (greeting.goal → action.request → action.result)            │
└─────────────────────────────────────────────────────────────────┘
        │                      │                      │
        ▼                      ▼                      ▼
   ┌─────────┐           ┌─────────┐            ┌─────────┐
   │ Planner │           │ Worker  │            │  Tool   │
   │         │           │         │            │         │
   │@on_goal │           │@on_task │            │@on_invoke
   └─────────┘           └─────────┘            └─────────┘
```

## Running the Example

### Prerequisites

From the `soorma-core` root directory:

```bash
# Create and activate virtual environment (if not already done)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\\Scripts\\activate

# Install SDK from PyPI
pip install soorma-core

# Build Docker images (first time only)
soorma dev --build
```

### 1. Start the dev infrastructure

```bash
soorma dev --infra-only
```

This starts:
- Event Service on http://localhost:8082
- Registry Service on http://localhost:8081

### 2. Run each agent in separate terminals

From the `soorma-core` root directory:

**Terminal 1 - Start the Planner:**
```bash
python examples/hello-world/planner_agent.py
```

**Terminal 2 - Start the Worker:**
```bash
python examples/hello-world/worker_agent.py
```

### 3. Submit a goal

**Terminal 3 - Run the client:**
```bash
python examples/hello-world/client.py "World"
```

Or with a custom name:
```bash
python examples/hello-world/client.py "Alice"
```

### Expected Output

**Client Terminal:**
```
==================================================
  Soorma Hello World - Client
==================================================

🎯 Submitting goal: Say hello to World

📤 Goal submitted!

📊 Waiting for result...
--------------------------------------------------

🎉 Result: Hello, World! 👋

==================================================
```

**Planner Terminal:**
```
📋 Planner received goal
   Goal ID: abc-123
   Data: {'name': 'World', 'description': 'Say hello to World'}

📝 Created plan: plan-456
   Tasks: 1
   - greet -> hello-worker
```

**Worker Terminal:**
```
⚙️  Worker received task: greet
   Task ID: task-789
   Data: {'name': 'World'}

   💬 Hello, World! 👋
```

## Files

| File | Description |
|------|-------------|
| `planner_agent.py` | Uses `Planner` class with `@on_goal()` decorator |
| `worker_agent.py` | Uses `Worker` class with `@on_task()` decorator |
| `tool_agent.py` | Uses `Tool` class with `@on_invoke()` decorator |
| `client.py` | Uses `EventClient` to submit goals |

## Environment Variables

The agents use these environment variables (with defaults):

```bash
export SOORMA_REGISTRY_URL=http://localhost:8081
export SOORMA_EVENT_SERVICE_URL=http://localhost:8082
```

These are automatically set when you run `soorma dev`.
