# Soorma Core SDK

**The Open Source Foundation for AI Agents.**

Soorma is an agentic infrastructure platform based on the **DisCo (Distributed Cognition)** architecture. It provides a standardized **Control Plane** (Registry, Event Bus, Memory Service) for building production-grade multi-agent systems.

## 🚧 Status: Day 0 (Pre-Alpha)

**Current Version:** 0.7.1

The SDK and core infrastructure are functional for building multi-agent systems. We're in active pre-launch refactoring to solidify architecture and APIs before v1.0.

**Learn more:** [soorma.ai](https://soorma.ai)

## Prerequisites

- **Python 3.11+** is required.

## Quick Start

> **Note:** Docker images are not yet published. You must clone the repo and build locally.

### 1. Clone Repository and Build Infrastructure

```bash
# Clone the repository
git clone https://github.com/soorma-ai/soorma-core.git
cd soorma-core

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the SDK
pip install -e sdk/python

# Build and start infrastructure (first time)
soorma dev --build
```

### 2. Run the Hello World Example

```bash
# Terminal 1: Infrastructure should be running
soorma dev

# Terminal 2: Start the worker
cd examples/01-hello-world
python worker.py

# Terminal 3: Send a request
python client.py Alice
```

You'll see a greeting response demonstrating the basic Worker pattern with event-driven request/response.

### 3. Create a New Agent Project

```bash
# Create a basic Worker agent (default)
soorma init my-worker

cd my-worker
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Start Local Development

```bash
# Start infrastructure (first time with --build)
soorma dev --build

# Subsequent starts
soorma dev

# In another terminal, run your agent
cd my-worker
python -m my_worker.agent
```

Infrastructure management:

```bash
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

## Agent Patterns

Soorma provides specialized agent classes for building distributed AI systems:

### Worker Agent

Workers execute domain-specific cognitive tasks through event handlers:

```python
from soorma import Worker, PlatformContext

worker = Worker(
    name="research-worker",
    description="Searches and analyzes papers",
    capabilities=["paper_search", "citation_analysis"],
)

@worker.on_event("research.requested", topic="action-requests")
async def handle_research(event, context: PlatformContext):
    # Extract request data
    query = event.get("data", {}).get("query")
    
    # Access shared memory
    prefs = await context.memory.retrieve(f"user:{event['session_id']}:preferences")
    
    # Perform research (your logic here)
    results = await search_papers(query, prefs)
    
    # Store results for other agents
    await context.memory.store(f"results:{event['id']}", results)
    
    # Respond with results
    await context.bus.respond(
        event_type="research.completed",
        data={"papers": results, "count": len(results)},
        correlation_id=event.get("correlation_id"),
    )

worker.run()
```

### Tool Agent

Tools provide atomic, stateless operations:

```python
from soorma import Tool, PlatformContext

tool = Tool(
    name="calculator",
    description="Performs calculations",
    capabilities=["arithmetic"],
)

@tool.on_event("calculate.requested", topic="action-requests")
async def calculate(event, context: PlatformContext):
    expression = event.get("data", {}).get("expression")
    result = safe_eval(expression)
    
    await context.bus.respond(
        event_type="calculate.completed",
        data={"result": result, "expression": expression},
        correlation_id=event.get("correlation_id"),
    )

tool.run()
```

### Planner Agent

Planners orchestrate multi-agent workflows using autonomous choreography:

```python
from soorma import Planner, PlatformContext
from soorma.ai.event_toolkit import EventToolkit

planner = Planner(
    name="research-planner",
    description="Orchestrates research workflows",
    capabilities=["orchestration"],
)

@planner.on_event("research.goal", topic="business-facts")
async def handle_goal(event, context: PlatformContext):
    # Discover available events dynamically
    async with EventToolkit() as toolkit:
        events = await toolkit.discover_events(topic="action-requests")
    
    # Use LLM to reason about which events to trigger
    # Store workflow state in working memory
    # Coordinate multiple workers autonomously
    
    # See examples/research-advisor for complete implementation
    pass

planner.run()
```

## Platform Context

Every event handler receives a `PlatformContext` that provides access to all platform services:

```python
@worker.on_event("my_event", topic="action-requests")
async def handler(event, context: PlatformContext):
    # Service Discovery
    agents = await context.registry.find_all("calculator")
    
    # Working Memory (key-value storage, plan-scoped)
    await context.memory.store("cache:123", {"value": 42})
    data = await context.memory.retrieve("cache:123")
    
    # Semantic Memory (vector search knowledge base)
    await context.memory.store_knowledge(
        content="Machine learning is a subset of AI",
        metadata={"category": "definitions", "source": "textbook"}
    )
    results = await context.memory.search_knowledge(
        query="What is ML?",
        limit=3
    )
    
    # Episodic Memory (interaction history)
    await context.memory.log_interaction(
        agent_id="assistant",
        role="assistant",
        content="Analysis complete",
        user_id="alice"
    )
    history = await context.memory.get_recent_history(
        agent_id="assistant",
        user_id="alice",
        limit=10
    )
    
    # Event Publishing
    await context.bus.publish(
        event_type="task.completed",
        topic="business-facts",
        data={"result": "done"}
    )
    
    # Request/Response Pattern
    await context.bus.respond(
        event_type="task.completed",
        data={"result": "done"},
        correlation_id=event.get("correlation_id")
    )
```

### Platform Services

| Service | Purpose | Key Methods |
|---------|---------|-------------|
| `context.registry` | Service Discovery | `find()`, `find_all()`, `register()` |
| `context.memory` | Distributed State (CoALA) | **Semantic:** `store_knowledge()`, `search_knowledge()` <br> **Episodic:** `log_interaction()`, `get_recent_history()`, `search_interactions()` <br> **Working:** `store()`, `retrieve()`, `delete()` |
| `context.bus` | Event Choreography | `publish()`, `respond()`, `request()` |
| `context.tracker` | Observability | `get_plan_status()`, `list_tasks()` |

## Advanced Usage

### Event-Driven Architecture

Soorma uses a **fixed set of topics** for event choreography. You cannot use arbitrary topic names - use the predefined topics from `soorma_common.EventTopic`:

- `action-requests` - Request another agent to perform an action
- `action-results` - Report results from completing an action
- `business-facts` - Announce domain events and state changes
- `system-events` - Platform system events (progress, heartbeat, etc.)

**See [docs/TOPICS.md](https://github.com/soorma-ai/soorma-core/blob/main/docs/TOPICS.md) for the complete list and usage guidance.**

```python
from soorma import Worker, PlatformContext

worker = Worker(
    name="order-processor",
    description="Processes customer orders",
    capabilities=["order_processing"],
)

@worker.on_event("order.placed", topic="business-facts")
async def handle_order(event, context: PlatformContext):
    order_id = event.get("data", {}).get("order_id")
    
    # Process order...
    result = await process_order(order_id)
    
    # Announce completion
    await context.bus.publish(
        event_type="order.processed",
        topic="business-facts",
        data={"order_id": order_id, "status": result}
    )

worker.run()
```

### Structured Event Registration

For complex events with validation, use `EventDefinition` with Pydantic schemas:

```python
from pydantic import BaseModel, Field
from soorma_common import EventDefinition, EventTopic

# Define payload schema
class AnalysisRequest(BaseModel):
    text: str = Field(..., description="Text to analyze")
    mode: str = Field("sentiment", description="Analysis mode")

# Define event
ANALYSIS_EVENT = EventDefinition(
    event_name="analysis.requested",
    topic=EventTopic.ACTION_REQUESTS,
    description="Request text analysis",
    payload_schema=AnalysisRequest.model_json_schema(),
)

# Use in agent registration
worker = Worker(
    name="analyzer",
    description="Analyzes text",
    capabilities=["text_analysis"],
    events_consumed=[ANALYSIS_EVENT],
    events_produced=["analysis.completed"],
)
```

The SDK automatically registers `EventDefinition` objects with the Registry on startup.

### AI Integration with LLMs

The SDK provides tools for LLM-based agents to discover and interact with events dynamically:

```python
from soorma.ai.event_toolkit import EventToolkit

async with EventToolkit() as toolkit:
    # 1. Discover available events
    events = await toolkit.discover_events(topic="action-requests")
    
    # 2. Get detailed event information
    info = await toolkit.get_event_info("web.search.request")
    
    # 3. Create validated payload
    payload = await toolkit.create_payload(
        "web.search.request",
        {"query": "AI trends 2025"}
    )
```

**For complete examples:**
- [03-events-structured](https://github.com/soorma-ai/soorma-core/tree/main/examples/03-events-structured) - LLM-based event selection
- [research-advisor](https://github.com/soorma-ai/soorma-core/tree/main/examples/research-advisor) - Autonomous choreography pattern

## CLI Commands

| Command | Description |
|---------|-------------|
| `soorma init <name>` | Scaffold a new agent project |
| `soorma dev` | Start infrastructure services |
| `soorma dev --build` | Build and start infrastructure (first time) |
| `soorma dev --status` | Show infrastructure status |
| `soorma dev --logs` | View infrastructure logs |
| `soorma dev --stop` | Stop infrastructure |
| `soorma dev --stop --clean` | Stop and remove all data/volumes |
| `soorma version` | Show SDK version |

### How `soorma dev` Works

The CLI implements an **"Infra in Docker, Code on Host"** pattern for optimal developer experience:

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
│                            ▲                                       │
│    ┌───────────────────────┴───────────────────┐                   │
│    │    Native Python (Your Agent)             │                   │
│    │  • Hot reload on file change              │                   │
│    │  • Full debugger support                  │                   │
│    │  • Auto-connects to all services          │                   │
│    └───────────────────────────────────────────┘                   │
└────────────────────────────────────────────────────────────────────┘
```

**Benefits:**
- ⚡ **Fast iteration** - No docker build cycle, instant reload
- 🔍 **Debuggable** - Attach VS Code/PyCharm debugger
- 🎯 **Production parity** - Same infrastructure as prod

**See [docs/DEVELOPER_GUIDE.md](https://github.com/soorma-ai/soorma-core/blob/main/docs/DEVELOPER_GUIDE.md) for complete development workflows.**

## Event-Driven Choreography

Unlike single-threaded agent loops, Soorma enables **Autonomous Choreography** via events. Agents discover each other through the Registry and coordinate via event topics:

```
Client              Worker A           Worker B            Tool
  │                    │                  │                  │
  │  event published   │                  │                  │
  │───────────────────>│                  │                  │
  │                    │  request event   │                  │
  │                    │─────────────────>│                  │
  │                    │                  │  invoke tool     │
  │                    │                  │─────────────────>│
  │                    │                  │  tool response   │
  │                    │                  │<─────────────────│
  │                    │  result event    │                  │
  │                    │<─────────────────│                  │
  │  response event    │                  │                  │
  │<───────────────────│                  │                  │
```

**Key Concepts:**
- **Topics** - Fixed set of event channels (action-requests, business-facts, etc.)
- **Event Types** - Specific event names within topics (e.g., "order.placed")
- **Discovery** - Agents find each other via Registry capabilities
- **Choreography** - No central orchestrator; agents coordinate via events

## Documentation

### Core Concepts
- **[Developer Guide](https://github.com/soorma-ai/soorma-core/blob/main/docs/DEVELOPER_GUIDE.md)** - Development workflows and testing strategies
- **[Design Patterns](https://github.com/soorma-ai/soorma-core/blob/main/docs/DESIGN_PATTERNS.md)** - Autonomous Choreography and Circuit Breakers
- **[Event Patterns](https://github.com/soorma-ai/soorma-core/blob/main/docs/EVENT_PATTERNS.md)** - Event-driven communication patterns
- **[Topics Guide](https://github.com/soorma-ai/soorma-core/blob/main/docs/TOPICS.md)** - Complete list of Soorma topics and usage guidance
- **[Memory Patterns](https://github.com/soorma-ai/soorma-core/blob/main/docs/MEMORY_PATTERNS.md)** - CoALA framework memory types and usage
- **[Messaging Patterns](https://github.com/soorma-ai/soorma-core/blob/main/docs/MESSAGING_PATTERNS.md)** - Queue groups, broadcasting, load balancing
- **[AI Assistant Guide](https://github.com/soorma-ai/soorma-core/blob/main/docs/AI_ASSISTANT_GUIDE.md)** - Using examples with GitHub Copilot/Cursor

### Examples

See the **[Examples Guide](https://github.com/soorma-ai/soorma-core/blob/main/examples/README.md)** for a complete catalog with progressive learning path:

- **[01-hello-world](https://github.com/soorma-ai/soorma-core/tree/main/examples/01-hello-world)** - Basic Worker pattern, event handling
- **[02-events-simple](https://github.com/soorma-ai/soorma-core/tree/main/examples/02-events-simple)** - Event pub/sub patterns
- **[03-events-structured](https://github.com/soorma-ai/soorma-core/tree/main/examples/03-events-structured)** - LLM-based event selection
- **[04-memory-working](https://github.com/soorma-ai/soorma-core/tree/main/examples/04-memory-working)** - Working memory for workflow state
- **[05-memory-semantic](https://github.com/soorma-ai/soorma-core/tree/main/examples/05-memory-semantic)** - Semantic memory (RAG)
- **[06-memory-episodic](https://github.com/soorma-ai/soorma-core/tree/main/examples/06-memory-episodic)** - Multi-agent chatbot with all memory types
- **[research-advisor](https://github.com/soorma-ai/soorma-core/tree/main/examples/research-advisor)** - Full autonomous choreography example

## Roadmap

* [x] **v0.1.0**: Core SDK & CLI (`soorma init`, `soorma dev`)
* [x] **v0.2.0**: Subscriber Groups & Unified Versioning
* [x] **v0.3.0**: Structured Registration & LLM-friendly Discovery
* [x] **v0.4.0**: Multi-provider LLM support
* [x] **v0.5.0**: Memory Service (CoALA framework) with PostgreSQL + pgvector
* [x] **v0.6.0**: Event System Refactoring (EventEnvelope, response routing, distributed tracing)
* [x] **v0.7.0**: Memory Service Stage 2 (Task/Plan Context, Sessions, State Machines)
* [x] **v0.7.1**: Documentation updates for PyPI
* [ ] **v0.8.0**: State Tracker & Workflow observability
* [ ] **v0.9.0**: Production hardening & performance optimization
* [ ] **v1.0.0**: General Availability

**See [CHANGELOG.md](https://github.com/soorma-ai/soorma-core/blob/main/CHANGELOG.md) for detailed release notes.**

## License

MIT