# Soorma Core

**The Open Source Foundation for AI Agents.**

Soorma is an agentic infrastructure platform based on the **DisCo (Distributed Cognition)** architecture. It solves the fragmentation in the AI agent ecosystem by providing a standardized **Control Plane** (Gateway, Registry, State, Pub/Sub).

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
# Scaffold a new agent project
soorma init my-agent
cd my-agent

# Set up virtual environment
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Start Local Development

```bash
# Start the local Soorma stack (Registry + NATS)
soorma dev

# In another terminal, run your agent
python -m my_agent.agent
```

### Deploy to Soorma Cloud

```bash
soorma deploy  # Coming soon!
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `soorma init <name>` | Scaffold a new agent project |
| `soorma dev` | Start infra + run agent with hot reload |
| `soorma dev --build` | Build service images from source first |
| `soorma dev --detach` | Start infra only (background) |
| `soorma dev --infra-only` | Start infra without running agent |
| `soorma dev --no-watch` | Disable hot reload |
| `soorma dev --stop` | Stop the development stack |
| `soorma dev --status` | Show stack status |
| `soorma dev --logs` | View infrastructure logs |
| `soorma deploy` | Deploy to Soorma Cloud (coming soon) |
| `soorma version` | Show CLI version |

### Building Service Images

If no pre-built images exist (Registry, etc.), you have several options:

```bash
# Option 1: Auto-build (looks for soorma-core in common locations)
soorma dev --build

# Option 2: Set path explicitly
export SOORMA_CORE_PATH=/path/to/soorma-core
soorma dev --build

# Option 3: Manual build from soorma-core root
cd /path/to/soorma-core
docker build -f services/registry/Dockerfile -t registry-service .
# Future services will have similar commands
```

## How `soorma dev` Works

The CLI implements an **"Infra in Docker, Code on Host"** pattern for optimal DX:

```
┌────────────────────────────────────────────────┐
│            Your Machine                        │
├────────────────────────────────────────────────┤
│  Docker Containers (Infrastructure)            │
│  ┌──────────┐  ┌──────────┐                   │
│  │ Registry │  │   NATS   │                   │
│  │  :8081   │  │  :4222   │                   │
│  └──────────┘  └──────────┘                   │
│        ▲              ▲                        │
│        └──── localhost ────┘                   │
│                 ▲                              │
│  ┌──────────────┴──────────────┐              │
│  │ Native Python (Your Agent)  │              │
│  │ • Hot reload on file change │              │
│  │ • Full debugger support     │              │
│  └─────────────────────────────┘              │
└────────────────────────────────────────────────┘
```

**Benefits:**
- ⚡ **Fast iteration** - No docker build cycle, instant reload
- 🔍 **Debuggable** - Attach VS Code/PyCharm debugger
- 🎯 **Production parity** - Same infrastructure as prod

## The DisCo Architecture

Unlike single-threaded loops (LangChain/AutoGen), Soorma enables **Autonomous Choreography**.

```python
from soorma import Agent, event_handler

# Define a long-lived, event-driven agent
agent = Agent(
    name="MarketAnalyst",
    description="Analyzes market trends",
    version="0.1.0",
)

@event_handler("research.requested")
async def handle_research(event):
    # React to events, don't just loop
    analysis = await analyze_trends(event["query"])
    await agent.emit("research.completed", {"analysis": analysis})

agent.run()
```

## Roadmap
* [x] **v0.1.0**: Core SDK & CLI (`soorma init`, `soorma dev`)
* [ ] **v0.2.0**: Managed Cloud Deployment (`soorma deploy`)
* [ ] **v1.0.0**: Enterprise GA

## License
MIT