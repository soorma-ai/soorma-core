# Soorma Core SDK

**The Open Source Foundation for AI Agents.**

Soorma is an agentic infrastructure platform based on the **DisCo (Distributed Cognition)** architecture. It provides a standardized **Control Plane** (Registry, Event Bus, Memory Service) for building production-grade multi-agent systems.

[![PyPI version](https://img.shields.io/pypi/v/soorma-core?color=amber&label=pypi)](https://pypi.org/project/soorma-core/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🚧 Status: Day 0 (Pre-Alpha)

We're in active pre-launch refactoring to solidify architecture and APIs before v1.0. The SDK and infrastructure are functional for building multi-agent systems.

**Learn more:** [soorma.ai](https://soorma.ai)

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

Soorma provides three agent types for building distributed AI systems:

- **Tool** - Synchronous, stateless operations (< 1 second)
- **Worker** - Asynchronous, stateful tasks with delegation
- **Planner** - Strategic reasoning and goal decomposition (Stage 4)

**Platform Services:**
- `context.registry` - Service discovery
- `context.memory` - Distributed state (Semantic, Episodic, Working memory)
- `context.bus` - Event choreography
- `context.tracker` - Observability

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
from soorma.task_context import TaskContext, ResultContext

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

### Comparison

| Feature | Tool | Worker |
|---------|------|--------|
| Execution | Synchronous | Asynchronous |
| State | Stateless | Stateful (TaskContext) |
| Completion | Auto | Manual (`task.complete()`) |
| Delegation | ❌ No | ✅ Yes |
| Memory I/O | ❌ No | ✅ Yes |
| Latency | < 100ms | Seconds to minutes |
| Example | Calculator | Order processing |

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
- [Design Patterns](https://github.com/soorma-ai/soorma-core/blob/main/docs/DESIGN_PATTERNS.md) - Autonomous Choreography and architectural patterns
- [Event Patterns](https://github.com/soorma-ai/soorma-core/blob/main/docs/EVENT_PATTERNS.md) - Event-driven communication
- [Memory Patterns](https://github.com/soorma-ai/soorma-core/blob/main/docs/MEMORY_PATTERNS.md) - CoALA framework memory types
- [Topics Guide](https://github.com/soorma-ai/soorma-core/blob/main/docs/TOPICS.md) - Complete list of event topics

**🎓 Learning Path:**
1. [01-hello-world](https://github.com/soorma-ai/soorma-core/tree/main/examples/01-hello-world) - Basic Worker pattern
2. [02-events-simple](https://github.com/soorma-ai/soorma-core/tree/main/examples/02-events-simple) - Event pub/sub
3. [03-events-structured](https://github.com/soorma-ai/soorma-core/tree/main/examples/03-events-structured) - LLM-based event selection
4. [04-memory-working](https://github.com/soorma-ai/soorma-core/tree/main/examples/04-memory-working) - Workflow state
5. [05-memory-semantic](https://github.com/soorma-ai/soorma-core/tree/main/examples/05-memory-semantic) - RAG patterns
6. [06-memory-episodic](https://github.com/soorma-ai/soorma-core/tree/main/examples/06-memory-episodic) - Multi-agent chatbot

## Contributing & Support

- **Repository:** [github.com/soorma-ai/soorma-core](https://github.com/soorma-ai/soorma-core)
- **Issues:** [Report bugs or request features](https://github.com/soorma-ai/soorma-core/issues)
- **Discussions:** [Ask questions](https://github.com/soorma-ai/soorma-core/discussions)
- **Changelog:** [Release notes](https://github.com/soorma-ai/soorma-core/blob/main/CHANGELOG.md)

## License

MIT License - see [LICENSE](https://github.com/soorma-ai/soorma-core/blob/main/LICENSE) for details.