# Soorma Core

**The Open Source Foundation for AI Agents.**

Soorma is an agentic infrastructure platform based on the **DisCo (Distributed Cognition)** architecture. It provides a standardized **Control Plane** (Gateway, Registry, Event Bus, State Tracker, Memory) for building production-grade multi-agent systems.

## 🚧 Status: Pre-Alpha

We are currently building the core runtime. This package provides early access to the SDK and CLI.

**Join the waitlist:** [soorma.ai](https://soorma.ai)

## Prerequisites

- **Python 3.11+** is required.

## Quick Start

> **Note:** Docker images are not yet published. You must clone the repo and build locally.

### 1. Clone Repository and Build Infrastructure

```bash
# Clone the repository (needed for Docker images)
git clone https://github.com/soorma-ai/soorma-core.git
cd soorma-core

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the SDK from PyPI
pip install soorma-core

# Build infrastructure containers (required first time)
soorma dev --build
```

> 💡 **Alternative:** To install SDK from local source (for development/customization):
> ```bash
> pip install -e sdk/python
> ```

### 2. Run the Hello World Example

```bash
# Terminal 1: Start infrastructure
soorma dev

# Terminal 2: Start the worker
cd examples/01-hello-world
bash start.sh

# Terminal 3: Send a request
python client.py Alice
```

### 3. Create a New Agent Project

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
# Start infrastructure (runs in background)
soorma dev --build

# In another terminal, run your agent
python -m my_worker.agent
```

Infrastructure management:

```bash
# Start infrastructure (default)
soorma dev --start

# Check status
soorma dev --status

# View logs
soorma dev --logs

# Stop infrastructure
soorma dev --stop

# Stop and remove all data/volumes (clean slate)
soorma dev --stop --clean
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
    
    # Working Memory (plan-scoped state)
    data = await context.memory.retrieve(f"cache:{task.data['key']}")
    await context.memory.store("result:123", {"value": 42})
    
    # Semantic Memory (knowledge base)
    await context.memory.store_knowledge(
        "Machine learning is a subset of AI",
        metadata={"source": "textbook", "chapter": 1}
    )
    knowledge = await context.memory.search_knowledge("What is ML?", limit=3)
    
    # Episodic Memory (interaction history)
    await context.memory.log_interaction(
        agent_id="analyst",
        role="assistant",
        content="Analysis complete",
        user_id=task.user_id
    )
    history = await context.memory.get_recent_history("analyst", task.user_id, limit=10)
    
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
| `context.memory` | Distributed State (CoALA) | **Semantic:** `store_knowledge()`, `search_knowledge()` <br> **Episodic:** `log_interaction()`, `get_recent_history()`, `search_interactions()` <br> **Procedural:** `get_relevant_skills()` <br> **Working:** `store()`, `retrieve()`, `delete()` |
| `context.bus` | Event Choreography | `publish()`, `subscribe()`, `request()` |
| `context.tracker` | Observability | `start_plan()`, `emit_progress()`, `complete_task()` |

## Advanced Usage

### Structured Agent Registration

For simple agents, you can pass a list of strings as capabilities. For more control, use `AgentCapability` objects to define schemas and descriptions.

```python
from soorma import Agent, Context
from soorma.models import AgentCapability

async def main(context: Context):
    # Define structured capabilities
    capabilities = [
        AgentCapability(
            name="analyze_sentiment",
            description="Analyzes the sentiment of a given text",
            input_schema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to analyze"}
                },
                "required": ["text"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "score": {"type": "number", "description": "Sentiment score (-1 to 1)"}
                }
            }
        )
    ]

    # Register with structured capabilities
    await context.register(
        name="sentiment-analyzer",
        capabilities=capabilities
    )

    # ... rest of agent logic
```

### Event Registration

You can register custom event schemas that your agent produces or consumes.

```python
from soorma.models import EventDefinition

async def main(context: Context):
    # Register a custom event schema
    await context.registry.register_event(
        EventDefinition(
            event_type="analysis.completed",
            description="Emitted when text analysis is complete",
            schema={
                "type": "object",
                "properties": {
                    "text_id": {"type": "string"},
                    "result": {"type": "object"}
                },
                "required": ["text_id", "result"]
            }
        )
    )
```

### AI Integration

The SDK provides specialized tools for AI agents (like LLMs) to interact with the system dynamically.

#### AI Event Toolkit

The `EventToolkit` allows agents to discover events and generate valid payloads without hardcoded DTOs.

```python
from soorma.ai.event_toolkit import EventToolkit

async with EventToolkit() as toolkit:
    # 1. Discover events
    events = await toolkit.discover_events(topic="action-requests")
    
    # 2. Get detailed info
    info = await toolkit.get_event_info("web.search.request")
    
    # 3. Create validated payload (handles schema validation)
    payload = await toolkit.create_payload(
        "web.search.request",
        {"query": "AI trends 2025"}
    )
```

#### OpenAI Function Calling

You can expose Registry capabilities directly to OpenAI-compatible LLMs using `get_tool_definitions()`.

```python
from soorma.ai.tools import get_tool_definitions, execute_ai_tool
import openai

# 1. Get tool definitions
tools = get_tool_definitions()

# 2. Call LLM
response = await openai.ChatCompletion.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Find events related to search"}],
    tools=tools
)

# 3. Execute tool calls
tool_call = response.choices[0].message.tool_calls[0]
result = await execute_ai_tool(
    tool_call.function.name,
    json.loads(tool_call.function.arguments)
)
```

## CLI Commands

> **First-time setup:** Run `soorma dev --build --infra-only` to build Docker images before using other commands.

| Command | Description |
|---------|-------------|
| `soorma init <name>` | Scaffold a new agent project |
| `soorma init <name> --type planner` | Create a Planner agent |
| `soorma init <name> --type worker` | Create a Worker agent (default) |
| `soorma init <name> --type tool` | Create a Tool service |
| `soorma dev` | Start infra + run agent with hot reload |
| `soorma dev --build` | Build service images from source first |
| `soorma dev --build --infra-only` | Build images without running agent (first-time setup) |
| `soorma dev --infra-only` | Start infra without running agent |
| `soorma dev --stop` | Stop the development stack |
| `soorma dev --stop --clean` | Stop stack and remove all data/volumes |
| `soorma dev --status` | Show stack status |
| `soorma dev --logs` | View infrastructure logs |
| `soorma deploy` | Deploy to Soorma Cloud (coming soon) |
| `soorma version` | Show CLI version |

## How `soorma dev` Works

The CLI implements an **"Infra in Docker, Code on Host"** pattern for optimal DX:

```
┌────────────────────────────────────────────────────────────────────┐
│                         Your Machine                               │
├────────────────────────────────────────────────────────────────────┤
│  Docker Containers (Infrastructure)                                │
│  ┌──────────┐  ┌──────────┐  ┌───────────────┐  ┌────────────────┐ │
│  │ Registry │  │   NATS   │  │ Event Service │  │ Memory Service │ │
│  │  :8000   │  │  :4222   │  │     :8001     │  │     :8002      │ │
│  └──────────┘  └──────────┘  └───────────────┘  └────────────────┘ │
│        ▲            ▲               ▲                   ▲          │
│        └────────────── localhost ───────────────────────┘          │
│                          ▲                                         │
│  ┌───────────────────────┴───────────────────┐                     │
│  │    Native Python (Your Agent)             │                     │
│  │  • Hot reload on file change              │                     │
│  │  • Full debugger support                  │                     │
│  │  • Auto-connects to all services          │                     │
│  └───────────────────────────────────────────┘                     │
└────────────────────────────────────────────────────────────────────┘
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

## Documentation

### Core Concepts
- [Event Architecture](docs/EVENT_ARCHITECTURE.md) - Event-driven agent choreography patterns
- [Memory Service SDK](docs/MEMORY_SERVICE.md) - CoALA framework memory types and usage

### API Reference
- **Registry Client**: Service discovery and capability registration
- **Event Client**: Publish/subscribe event choreography
- **Memory Client**: Persistent memory for autonomous agents (Semantic, Episodic, Procedural, Working)
- **Platform Context**: Unified API for all platform services

### Examples

See the **[Examples Guide](../../examples/README.md)** for a complete catalog of examples with a progressive learning path.

## Roadmap

* [x] **v0.1.0**: Core SDK & CLI (`soorma init`, `soorma dev`)
* [x] **v0.1.1**: Event Service & DisCo Trinity (Planner, Worker, Tool)
* [x] **v0.2.0**: Subscriber Groups & Unified Versioning
* [x] **v0.3.0**: Structured Registration & LLM-friendly Discovery
* [x] **v0.4.0**: Multi-provider LLM support & Autonomous choreography improvements
* [x] **v0.5.0**: Memory Service (CoALA framework) & PostgreSQL infrastructure
* [ ] **v0.6.0**: State Tracker & Workflow observability
* [ ] **v1.0.0**: Enterprise GA

## License

MIT