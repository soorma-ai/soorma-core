# Soorma Core SDK

**The Open Source Foundation for AI Agents.**

Soorma is an agentic infrastructure platform based on the **DisCo (Distributed Cognition)** architecture. It provides a standardized **Control Plane** (Registry, Event Bus, Memory Service) for building production-grade multi-agent systems.

[![PyPI version](https://img.shields.io/pypi/v/soorma-core?color=amber&label=pypi)](https://pypi.org/project/soorma-core/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🚧 Status: Day 0 (Pre-Alpha)

**Current Version:** 0.7.2

We're in active pre-launch refactoring to solidify architecture and APIs before v1.0. The SDK and infrastructure are functional for building multi-agent systems.

**Learn more:** [soorma.ai](https://soorma.ai)

## Installation

```bash
pip install soorma-core
```

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

- **Worker** - Executes domain-specific cognitive tasks
- **Tool** - Provides atomic, stateless operations
- **Planner** - Orchestrates multi-agent workflows

**Platform Services:**
- `context.registry` - Service discovery
- `context.memory` - Distributed state (Semantic, Episodic, Working memory)
- `context.bus` - Event choreography
- `context.tracker` - Observability

**Learn more:** See the [comprehensive documentation](https://github.com/soorma-ai/soorma-core) for architecture details, patterns, and API references.

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