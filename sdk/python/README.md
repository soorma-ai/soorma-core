# Soorma Core

**The Open Source Foundation for AI Agents.**

Soorma is an agentic infrastructure platform based on the **DisCo (Distributed Cognition)** architecture. It solves the fragmentation in the AI agent ecosystem by providing a standardized **Control Plane** (Gateway, Registry, State, Pub/Sub).

## 🚧 Status: Pre-Alpha (Day 0)

We are currently building the core runtime. This package is a placeholder to reserve the namespace and provide early access to the API surface.

**Join the waitlist:** [soorma.ai](https://soorma.ai)

## The DisCo Architecture

Unlike single-threaded loops (LangChain/AutoGen), Soorma enables **Autonomous Choreography**.

```
from soorma import Worker

# Define a long-lived, event-driven worker
analyst = Worker(name="MarketAnalyst", capabilities=["analyze_trends"])

@analyst.on_event("research.requested")
async def handle(event, context):
    # React to events, don't just loop
    history = await context.memory.retrieve(tags=["Q3"])
    return {"analysis": "..."}
```

## Roadmap
* [ ] **v0.1.0**: Core SDK & Local Dev Environment (`soorma dev`)
* [ ] **v0.2.0**: Managed Cloud Deployment (`soorma deploy`)
* [ ] **v1.0.0**: Enterprise GA

## License
MIT