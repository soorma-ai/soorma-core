# Soorma Core

**The Open Source Foundation for AI Agents.**

Soorma is an agentic infrastructure platform based on the **DisCo (Distributed Cognition)** architecture. It provides a standardized **Control Plane** (Gateway, Registry, Event Bus, State Tracker, Memory) for building production-grade multi-agent systems.

## 🚧 Status: Pre-Alpha

We are currently building the core runtime. This package provides early access to the SDK and CLI.

**Join the waitlist:** [soorma.ai](https://soorma.ai)

## Quick Start

### Installation

```bash
pip install soorma-core
```

### Create a New Agent Project

```bash
# Create a Worker agent (default)
soorma init my-worker

# Create a Planner agent (goal decomposition)
soorma init my-planner --type planner

# Create a Tool service (stateless operations)
soorma init my-tool --type tool

cd my-worker
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Start Local Development

```bash
# Start the local Soorma stack (Registry + NATS + Event Service)
soorma dev

# In another terminal, run your agent
python -m my_worker.agent
```

### Deploy to Soorma Cloud

```bash
soorma deploy  # Coming soon!
```

## The DisCo "Trinity"

Soorma implements the **DisCo (Distributed Cognition)** architecture with three domain service types:

| Type | Class | Purpose | Example Use Cases |
|------|-------|---------|-------------------|
| **Planner** | `Planner` | Strategic reasoning, goal decomposition | Research planning, workflow orchestration |
| **Worker** | `Worker` | Domain-specific task execution | Data processing, analysis, content generation |
| **Tool** | `Tool` | Atomic, stateless operations | API calls, calculations, file parsing |

### Planner Agent

Planners are the "brain" - they receive high-level goals and decompose them into tasks:

```python
from soorma import Planner, PlatformContext
from soorma.agents.planner import Goal, Plan, Task

planner = Planner(
    name="research-planner",
    description="Plans research workflows",
    capabilities=["research_planning"],
)

@planner.on_goal("research.goal")
async def plan_research(goal: Goal, context: PlatformContext) -> Plan:
    # Discover available workers
    workers = await context.registry.find_all("paper_search")
    
    # Decompose goal into tasks
    return Plan(
        goal=goal,
        tasks=[
            Task(name="search", assigned_to="paper_search", data=goal.data),
            Task(name="summarize", assigned_to="summarizer", depends_on=["search"]),
        ],
    )

planner.run()
```

### Worker Agent

Workers are the "hands" - they execute domain-specific cognitive tasks:

```python
from soorma import Worker, PlatformContext
from soorma.agents.worker import TaskContext

worker = Worker(
    name="research-worker",
    description="Searches and analyzes papers",
    capabilities=["paper_search", "citation_analysis"],
)

@worker.on_task("paper_search")
async def search_papers(task: TaskContext, context: PlatformContext):
    # Report progress
    await task.report_progress(0.5, "Searching...")
    
    # Access shared memory
    prefs = await context.memory.retrieve(f"user:{task.session_id}:prefs")
    
    # Your task logic
    results = await search_academic_papers(task.data["query"], prefs)
    
    # Store for downstream workers
    await context.memory.store(f"results:{task.task_id}", results)
    
    return {"papers": results, "count": len(results)}

worker.run()
```

### Tool Service

Tools are the "utilities" - stateless, deterministic operations:

```python
from soorma import Tool, PlatformContext
from soorma.agents.tool import ToolRequest

tool = Tool(
    name="calculator",
    description="Performs calculations",
    capabilities=["arithmetic", "unit_conversion"],
)

@tool.on_invoke("calculate")
async def calculate(request: ToolRequest, context: PlatformContext):
    expression = request.data["expression"]
    result = safe_eval(expression)
    return {"result": result, "expression": expression}

tool.run()
```

## Platform Context

Every handler receives a `PlatformContext` that provides access to all platform services:

```python
@worker.on_task("my_task")
async def handler(task: TaskContext, context: PlatformContext):
    # Service Discovery
    tool = await context.registry.find("calculator")
    
    # Shared Memory
    data = await context.memory.retrieve(f"cache:{task.data['key']}")
    await context.memory.store("result:123", {"value": 42})
    
    # Event Publishing
    await context.bus.publish("task.completed", {"result": "done"})
    
    # Progress Tracking (automatic for workers, manual available)
    await context.tracker.emit_progress(
        plan_id=task.plan_id,
        task_id=task.task_id,
        status="running",
        progress=0.75,
    )
```

| Service | Purpose | Methods |
|---------|---------|---------|
| `context.registry` | Service Discovery | `find()`, `register()`, `query_schemas()` |
| `context.memory` | Distributed State | `retrieve()`, `store()`, `search()` |
| `context.bus` | Event Choreography | `publish()`, `subscribe()`, `request()` |
| `context.tracker` | Observability | `start_plan()`, `emit_progress()`, `complete_task()` |

## CLI Commands

| Command | Description |
|---------|-------------|
| `soorma init <name>` | Scaffold a new agent project |
| `soorma init <name> --type planner` | Create a Planner agent |
| `soorma init <name> --type worker` | Create a Worker agent (default) |
| `soorma init <name> --type tool` | Create a Tool service |
| `soorma dev` | Start infra + run agent with hot reload |
| `soorma dev --build` | Build service images from source first |
| `soorma dev --infra-only` | Start infra without running agent |
| `soorma dev --stop` | Stop the development stack |
| `soorma dev --status` | Show stack status |
| `soorma dev --logs` | View infrastructure logs |
| `soorma deploy` | Deploy to Soorma Cloud (coming soon) |
| `soorma version` | Show CLI version |

## How `soorma dev` Works

The CLI implements an **"Infra in Docker, Code on Host"** pattern for optimal DX:

```
┌─────────────────────────────────────────────────────────────┐
│                    Your Machine                             │
├─────────────────────────────────────────────────────────────┤
│  Docker Containers (Infrastructure)                         │
│  ┌──────────┐  ┌──────────┐  ┌───────────────┐              │
│  │ Registry │  │   NATS   │  │ Event Service │              │
│  │  :8081   │  │  :4222   │  │    :8082      │              │
│  └──────────┘  └──────────┘  └───────────────┘              │
│        ▲            ▲               ▲                       │
│        └────── localhost ───────────┘                       │
│                     ▲                                       │
│  ┌──────────────────┴──────────────────┐                    │
│  │    Native Python (Your Agent)       │                    │
│  │  • Hot reload on file change        │                    │
│  │  • Full debugger support            │                    │
│  │  • Auto-connects to Event Service   │                    │
│  └─────────────────────────────────────┘                    │
└─────────────────────────────────────────────────────────────┘
```

**Benefits:**
- ⚡ **Fast iteration** - No docker build cycle, instant reload
- 🔍 **Debuggable** - Attach VS Code/PyCharm debugger
- 🎯 **Production parity** - Same infrastructure as prod

## Event-Driven Architecture

Unlike single-threaded agent loops, Soorma enables **Autonomous Choreography** via events:

```
Client                Planner              Worker              Tool
  │                     │                    │                   │
  │  goal.submitted     │                    │                   │
  │────────────────────>│                    │                   │
  │                     │  action.request    │                   │
  │                     │───────────────────>│                   │
  │                     │                    │  tool.request     │
  │                     │                    │──────────────────>│
  │                     │                    │  tool.response    │
  │                     │                    │<──────────────────│
  │                     │  action.result     │                   │
  │                     │<───────────────────│                   │
  │  goal.completed     │                    │                   │
  │<────────────────────│                    │                   │
```

## Roadmap

* [x] **v0.1.0**: Core SDK & CLI (`soorma init`, `soorma dev`)
* [x] **v0.1.1**: Event Service & DisCo Trinity (Planner, Worker, Tool)
* [ ] **v0.2.0**: Managed Cloud Deployment (`soorma deploy`)
* [ ] **v0.3.0**: Memory Service & State Tracker
* [ ] **v1.0.0**: Enterprise GA

## License

MIT