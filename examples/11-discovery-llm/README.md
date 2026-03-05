# Example 11: LLM-Based Dynamic Discovery

> **Phase 5 — Validation & Documentation** · `examples/11-discovery-llm`

This example demonstrates **LLM-driven dynamic discovery**: a planner that has
never seen a worker before discovers it at runtime via the Registry, fetches its
payload schema, and uses an LLM to generate a well-formed request payload — all
without any hardcoded event names or schema structures.

---

## What You'll Learn

| Concept | Where |
|---|---|
| Inline JSON Schema on `AgentCapability` — SDK auto-registers | `worker.py` |
| `ctx.registry.discover()` — find agents by capability | `planner.py` |
| `ctx.registry.get_schema()` — fetch schema from Registry | `planner.py` |
| `ctx.ai.generate_payload()` — LLM generates conforming payload | `planner.py` |
| `ctx.bus.request()` with explicit `response_event` | `planner.py` |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Soorma Platform (Registry + NATS + Memory)             │
└───────────────────────────┬─────────────────────────────┘
                            │
          ┌─────────────────┼──────────────────┐
          │                 │                  │
   ┌──────▼──────┐   ┌──────▼──────┐    NATS topic
   │   worker.py │   │  planner.py │    action-requests
   │             │   │             │
   │  Registers: │   │  Discovers: │
   │  - Agent    │   │  - Agents   │
   │  - Schema   │   │  - Schema   │
   │    (SDK     │   │  Generates: │
   │    auto)    │   │  - Payload  │
   └─────────────┘   └─────────────┘
```

**No `schema_registration.py` script.** The worker declares `payload_schema`
(inline JSON Schema body) on its `AgentCapability.consumed_event`. The SDK calls
`register_schema()` automatically inside `_register_with_registry()` — the
worker developer never does it explicitly.

---

## Prerequisites

- Soorma platform services running: `soorma dev --build`
- Python ≥ 3.11
- An OpenAI API key (or compatible provider)

---

## Setup

```bash
cd examples/11-discovery-llm
cp .env.example .env
# Edit .env — add your OPENAI_API_KEY

pip install -r requirements.txt
```

---

## Running

```bash
./start.sh
```

The script starts the worker first, waits 2 seconds for it to register with the
Registry, then starts the planner.

To trigger a research goal from a second terminal:

```python
# publish_goal.py  (run from inside examples/11-discovery-llm/)
import asyncio
from soorma.context import PlatformContext

async def main():
    async with PlatformContext() as ctx:
        await ctx.bus.publish(
            event_type="research.goal",
            payload={"description": "Latest advances in quantum computing, 2025"},
        )

asyncio.run(main())
```

---

## Expected Output

```
[worker]  ✓ Registered research-worker (schema: research_request_v1)
[planner] Goal received: research.goal
[planner] Discovered 1 agent(s) with capability: web_research
[planner] Schema fetched: research_request_v1
[planner] LLM generated payload: {"topic": "Latest advances in quantum computing, 2025", "max_results": 5, "depth": "standard"}
[planner] Published: research.requested → awaiting research.completed.<correlation_id>
[worker]  ▶ Received: research.requested — topic: Latest advances in quantum computing, 2025
[worker]  ✓ Research complete — 5 findings
[planner] ✓ Response received on research.completed.<correlation_id>
```

---

## Files

| File | Purpose |
|---|---|
| `worker.py` | Research worker — inline schema, handler, `worker.run()` |
| `planner.py` | Discovery planner — discover → schema → LLM → dispatch |
| `start.sh` | Starts worker (sleep 2) then planner; Ctrl-C stops all |
| `.env.example` | Environment variable template |
| `requirements.txt` | Python dependencies |

---

## Related

- **Previous:** [10-choreography-basic](../10-choreography-basic/) — ChoreographyPlanner with known event names
- **Next:** [12-event-selector](../12-event-selector/) — EventSelector intelligent routing
- **SDK internals:** `sdk/python/soorma/agents/base._auto_register_inline_schemas()`
- **Integration tests:** `sdk/python/tests/integration/test_e2e_discovery.py`
