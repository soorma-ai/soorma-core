# Soorma Core SDK

**The Open Source Foundation for AI Agents.**

Soorma is an agentic infrastructure platform based on the **DisCo (Distributed Cognition)** architecture. It provides a standardized control plane for building production-grade multi-agent systems, including Registry, Event Bus, Memory, Tracker, and Identity services.

[![PyPI version](https://img.shields.io/pypi/v/soorma-core?color=amber&label=pypi)](https://pypi.org/project/soorma-core/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🚧 Status: Day 0 (Pre-Alpha)

We're in active pre-launch refactoring to solidify architecture and APIs before v1.0. The SDK and infrastructure are functional for building multi-agent systems.

**Learn more:** [soorma.ai](https://soorma.ai)

### What's New in v0.9.0

- **🔐 JWT-First Service Auth** - SDK and service documentation now reflect the current bearer-token runtime model and trusted admin exception paths
- **🪪 Identity Bootstrap Hardening** - `soorma dev` bootstraps persisted local RS256/JWKS signing material for local stacks by default
- **🏷️ Unified Release Alignment** - SDK, shared libraries, and backend services are aligned on `0.9.0`

### Highlights from v0.8.2

- **🔍 Agent Discovery** - `context.registry.discover()` finds active agents by consumed event; returns `DiscoveredAgent` list with schema helpers
- **📋 Schema Registry** - Register and retrieve JSON payload schemas via `context.registry.register_schema()` / `get_schema()` / `list_schemas()`
- **🔗 A2A Gateway** - `A2AGateway` adapter exposes any Soorma agent via the Agent-to-Agent (A2A) protocol (`GET /.well-known/agent.json`, `POST /`)
- **🔌 EventSelector** - Discover agents that handle a specific event before publishing
- **📦 soorma-nats** - New shared `NATSClient` library (`libs/soorma-nats/`); Tracker Service no longer depends on SDK
- **✅ Integration Test Suite** - 11 in-process tests (E2E discovery, multi-tenant isolation, A2A round-trip)

### Highlights from v0.8.1

- **🤖 ChoreographyPlanner** - LLM-based autonomous orchestration (50+ model providers via LiteLLM)
- **📊 PlanContext** - State machine for multi-step workflows with pause/resume
- **📈 TrackerClient** - Event-driven observability and progress tracking
- **🎯 Pattern Selection Framework** - Choose the right pattern for your use case
- **🔐 BYO Model Credentials** - Developer-controlled LLM providers (OpenAI, Azure, Anthropic, Ollama)

**Install with LLM support:** `pip install soorma-core[ai]`

## Installation

> **During Pre-Launch:** We recommend installing from local source to stay synchronized with breaking changes:

```bash
# Clone the repository
git clone https://github.com/soorma-ai/soorma-core.git
cd soorma-core

# Install from source
pip install -e sdk/python
```

> **After v1.0 Release:** Standard PyPI installation will be recommended: `pip install soorma-core`

**Requirements:** Python 3.11+

## Quick Start

> **Note:** Infrastructure runs locally via Docker. Clone the repo to get started.

```bash
# 1. Clone the repository
git clone https://github.com/soorma-ai/soorma-core.git
cd soorma-core

# 2. Start local infrastructure
soorma dev --build

# 3. Run the Hello World example
cd examples/01-hello-world
python worker.py

# 4. In another terminal, send a request
python client.py Alice
```

**Next steps:** See the [Examples Guide](https://github.com/soorma-ai/soorma-core/blob/main/examples/README.md) for a complete learning path.

## Core Concepts

Soorma provides **four agent patterns** for building distributed AI systems:

- **Tool** - Synchronous, stateless operations (< 1 second)
- **Worker** - Asynchronous, stateful tasks with delegation
- **Planner** - Multi-step workflows with manual state machine control
- **ChoreographyPlanner** - Autonomous LLM-based orchestration

**Platform Services:**
- `context.registry` - Service discovery, agent registration, schema registry & A2A discovery (`discover()`, `register_schema()`, `list_schemas()`)
- `context.memory` - Distributed state (Semantic, Episodic, Working, Plan context)
- `context.bus` - Event choreography (pub/sub)
- `context.tracker` - Observability & progress tracking

**Learn more:** See the [comprehensive documentation](https://github.com/soorma-ai/soorma-core) for architecture details, patterns, and API references.

## Agent Models

### Tool Model (Synchronous)

Tools handle fast, stateless operations that return immediate results:

```python
from soorma import Tool
from soorma.agents.tool import InvocationContext

tool = Tool(name="calculator")

@tool.on_invoke("calculate.add")
async def add_numbers(request: InvocationContext, context):
    numbers = request.data["numbers"]
    return {"sum": sum(numbers)}  # Auto-published to caller
```

**Characteristics:**
- ⚡ **Stateless:** No persistence between calls
- 🚀 **Fast:** Returns immediately (< 1 second)
- 🔄 **Auto-complete:** SDK publishes response automatically
- 📊 **Use cases:** Calculations, lookups, validations

**Example:** [01-hello-tool](https://github.com/soorma-ai/soorma-core/tree/main/examples/01-hello-tool)

### Worker Model (Asynchronous with Delegation)

Workers handle multi-step, stateful tasks with delegation:

```python
from soorma import Worker
from soorma.task_context import TaskContext, ResultContext, DelegationSpec

worker = Worker(name="order-processor")

@worker.on_task("order.process.requested")
async def process_order(task: TaskContext, context):
    # Save state
    task.state["order_id"] = task.data["order_id"]
    await task.save()
    
    # Delegate to sub-workers
    await task.delegate_parallel([
        DelegationSpec("inventory.reserve.requested", {...}, "inventory.reserved"),
        DelegationSpec("payment.process.requested", {...}, "payment.processed"),
    ])

@worker.on_result("inventory.reserved")
@worker.on_result("payment.processed")
async def handle_result(result: ResultContext, context):
    task = await result.restore_task()
    task.update_sub_task_result(result.correlation_id, result.data)
    
    # Complete when all results arrived
    if task.aggregate_parallel_results(task.state["group_id"]):
        await task.complete({"status": "completed"})
```

**Characteristics:**
- 💾 **Stateful:** TaskContext persists across delegations
- 🔄 **Asynchronous:** Manual completion with `task.complete()`
- 🎯 **Delegation:** Sequential or parallel sub-tasks
- ⚙️ **Use cases:** Workflows, long-running operations, coordination

**Delegation Patterns:**
- **Sequential:** `task.delegate()` - One sub-task at a time
- **Parallel:** `task.delegate_parallel()` - Fan-out with aggregation
- **Multi-level:** Workers can delegate to Workers (arbitrary depth)

**Example:** [08-worker-basic](https://github.com/soorma-ai/soorma-core/tree/main/examples/08-worker-basic)

### Planner Model (Multi-Step Workflows)

Planners orchestrate multi-step workflows using state machines:

```python
from soorma import Planner
from soorma.plan_context import PlanContext
from soorma_common.state import StateConfig, StateTransition, StateAction

planner = Planner(name="approval-workflow")

# Define state machine
states = [
    StateConfig(
        name="pending_review",
        transitions=[StateTransition(event="review.approved", next_state="pending_execution")],
        actions=[StateAction(event="review.requested", data={...})]
    ),
    # ... more states
]

@planner.on_goal("approval.workflow.requested")
async def start_workflow(goal, context):
    plan = await PlanContext.create_from_goal(goal, states, context)
    await plan.execute_next(context)  # Execute first state's actions

@planner.on_transition()
async def handle_transition(event, context, plan, next_state):
    await plan.execute_next(context)  # Execute next state's actions
```

**Characteristics:**
- 🎯 **Manual control:** Developer defines all state transitions
- 💾 **Stateful:** PlanContext persists across events
- 🔄 **Re-entrant:** Pause/resume for human-in-the-loop workflows
- 📊 **Use cases:** Approval workflows, multi-stage pipelines

**Example:** [09-planner-basic](https://github.com/soorma-ai/soorma-core/tree/main/examples/09-planner-basic)

### ChoreographyPlanner Model (Autonomous Orchestration)

ChoreographyPlanner uses LLMs to autonomously decide next actions:

```python
from soorma.ai.choreography import ChoreographyPlanner

planner = ChoreographyPlanner(
    name="research-planner",
    reasoning_model="gpt-4o",  # or azure/gpt-4o, anthropic/claude-3-opus, ollama/llama2, etc.
    api_key=os.getenv("OPENAI_API_KEY"),  # BYO credentials
    system_instructions="You are a research assistant...",
    max_actions=10  # Circuit breaker
)

@planner.on_goal("research.requested")
async def handle_research(goal, context):
    plan = await planner.reason_and_execute(
        goal=goal.data["query"],
        context=context,
        custom_context={"domain": "AI research"}  # Business logic injection
    )
```

**Characteristics:**
- 🤖 **Autonomous:** LLM decides which events to publish and when to complete
- 🌐 **Event discovery:** Queries Registry for available capabilities
- ✅ **Validation:** Prevents LLM hallucinations via event schema checks
- 💰 **Cost-aware:** Configurable planning strategies (balanced|conservative|aggressive)
- 🔐 **BYO credentials:** Developer controls LLM provider and API keys
- 📊 **Use cases:** Research workflows, adaptive planning, dynamic orchestration

**Installation:** `pip install soorma-core[ai]` (includes LiteLLM for 50+ model providers)

**Example:** [10-choreography-basic](https://github.com/soorma-ai/soorma-core/tree/main/examples/10-choreography-basic)

### Pattern Comparison

| Feature | Tool | Worker | Planner | ChoreographyPlanner |
|---------|------|--------|---------|---------------------|
| Execution | Synchronous | Asynchronous | Multi-step | Multi-step |
| State | Stateless | TaskContext | PlanContext | PlanContext |
| Completion | Auto | Manual | Manual | Auto (LLM decides) |
| Delegation | ❌ No | ✅ Yes | ✅ Yes | ✅ Yes |
| Control | Full | High | Full | Autonomous |
| LLM Required | ❌ No | ❌ No | ❌ No | ✅ Yes |
| Latency | < 100ms | Seconds | Varies | 1-10s per decision |
| Cost | Free | Free | Free | LLM API costs |
| Example | Calculator | Order processing | Approval workflow | Research assistant |

**Choosing a pattern:** See the [Pattern Selection Guide](https://github.com/soorma-ai/soorma-core/blob/main/docs/agent_patterns/README.md) for decision criteria and flowcharts.

## CLI Reference

| Command | Description |
|---------|-------------|
| `soorma init <name>` | Create a new agent project |
| `soorma dev` | Start local infrastructure |
| `soorma dev --build` | Build and start (first time) |
| `soorma dev --status` | Show infrastructure status |
| `soorma dev --logs` | View infrastructure logs |
| `soorma dev --stop` | Stop infrastructure |
| `soorma dev --stop --clean` | Stop and remove all data |
| `soorma version` | Show SDK version |

The `soorma dev` command runs infrastructure (Registry, NATS, Event Service, Memory Service) in Docker while your agent code runs natively on the host for fast iteration and debugging.

## Documentation & Resources

**📚 Complete Documentation:** [github.com/soorma-ai/soorma-core](https://github.com/soorma-ai/soorma-core)

**Key Guides:**
- [Examples Guide](https://github.com/soorma-ai/soorma-core/blob/main/examples/README.md) - Progressive learning path from hello-world to advanced patterns
- [Developer Guide](https://github.com/soorma-ai/soorma-core/blob/main/docs/DEVELOPER_GUIDE.md) - Development workflows and testing
- [Agent Patterns](https://github.com/soorma-ai/soorma-core/blob/main/docs/agent_patterns/README.md) - Tool, Worker, Planner models and DisCo pattern
- [Event System](https://github.com/soorma-ai/soorma-core/blob/main/docs/event_system/README.md) - Event-driven architecture, topics, messaging
- [Memory System](https://github.com/soorma-ai/soorma-core/blob/main/docs/memory_system/README.md) - CoALA framework and memory types
- [Discovery](https://github.com/soorma-ai/soorma-core/blob/main/docs/discovery/README.md) - Registry and capability discovery

**🎓 Learning Path:**
1. [01-hello-world](https://github.com/soorma-ai/soorma-core/tree/main/examples/01-hello-world) - Basic Worker pattern
2. [01-hello-tool](https://github.com/soorma-ai/soorma-core/tree/main/examples/01-hello-tool) - Stateless Tool pattern
3. [02-events-simple](https://github.com/soorma-ai/soorma-core/tree/main/examples/02-events-simple) - Event pub/sub
4. [03-events-structured](https://github.com/soorma-ai/soorma-core/tree/main/examples/03-events-structured) - LLM-based event selection
5. [04-memory-working](https://github.com/soorma-ai/soorma-core/tree/main/examples/04-memory-working) - Workflow state
6. [05-memory-semantic](https://github.com/soorma-ai/soorma-core/tree/main/examples/05-memory-semantic) - RAG patterns
7. [06-memory-episodic](https://github.com/soorma-ai/soorma-core/tree/main/examples/06-memory-episodic) - Multi-agent chatbot
8. [08-worker-basic](https://github.com/soorma-ai/soorma-core/tree/main/examples/08-worker-basic) - Task delegation (parallel)
9. [09-planner-basic](https://github.com/soorma-ai/soorma-core/tree/main/examples/09-planner-basic) - State machine workflows
10. [10-choreography-basic](https://github.com/soorma-ai/soorma-core/tree/main/examples/10-choreography-basic) - Autonomous LLM planning
11. [11-discovery-llm](https://github.com/soorma-ai/soorma-core/tree/main/examples/11-discovery-llm) - LLM-based dynamic discovery & lightweight dispatch
12. [12-event-selector](https://github.com/soorma-ai/soorma-core/tree/main/examples/12-event-selector) - Intelligent event routing with EventSelector
13. [13-a2a-gateway](https://github.com/soorma-ai/soorma-core/tree/main/examples/13-a2a-gateway) - A2A protocol gateway integration

## Contributing & Support

- **Repository:** [github.com/soorma-ai/soorma-core](https://github.com/soorma-ai/soorma-core)
- **Issues:** [Report bugs or request features](https://github.com/soorma-ai/soorma-core/issues)
- **Discussions:** [Ask questions](https://github.com/soorma-ai/soorma-core/discussions)
- **Changelog:** [Release notes](https://github.com/soorma-ai/soorma-core/blob/main/CHANGELOG.md)

## License

MIT License - see [LICENSE](https://github.com/soorma-ai/soorma-core/blob/main/LICENSE) for details.