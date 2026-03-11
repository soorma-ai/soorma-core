# Example 11: LLM-Based Dynamic Discovery

> **Phase 5 — Validation & Documentation** · `examples/11-discovery-llm`

This example demonstrates **LLM-driven dynamic discovery**: a planner that has
never seen a worker before discovers it at runtime via the Registry, fetches its
payload schema, and uses an LLM to generate a well-formed request payload — all
without any hardcoded event names or schema structures.

It also demonstrates correct **request/response ownership**: the planner owns
both ends of the client contract. The worker is an internal implementation
detail that the client never knows about.

---

## What You'll Learn

| Concept | Where |
|---|---|
| Inline JSON Schema on `AgentCapability` — SDK auto-registers | `worker.py` |
| `task.complete()` — high-level response, auto-propagates all metadata | `worker.py` |
| `events_produced=[EventDefinition(...)]` — planner declares + auto-registers response schema | `planner.py` |
| `ctx.registry.discover()` — find agents by capability at runtime | `planner.py` |
| `ctx.registry.get_event()` + `get_schema()` — resolve schema from event name | `planner.py` |
| `planner.generate_payload()` — LLM generates conforming payload **(both directions)** | `planner.py` |
| `@planner.on_event()` — receive worker result, normalize via schema + LLM, forward to client | `planner.py` |
| Canonical event names + `correlation_id` filtering | `client.py` |

---

## Architecture

```
client.py                planner.py                         worker.py
─────────                ──────────                         ─────────
publish                  @on_goal("research.goal")
research.goal    ──────► discover() → get worker schema
(response_event=         generate_payload()  ← LLM
 research.completed)     bus.request(
                           "research.requested",
                           response_event=                  @on_task("research.requested")
                           "research.worker.completed") ───► task.complete(raw_findings)
                                                                       │
                         @on_event(                                    │
                           "research.worker.completed")  ◄─────────────┘
                         get_event("research.completed")
                           → get_schema("research_result_v1")
                         generate_payload()  ← LLM normalizes raw result
                         bus.respond(
◄────────────────────────  "research.completed", ...)
research.completed
```

**Symmetric schema-driven dispatch — both directions use the same pattern:**
- Outbound to worker: discover worker schema at runtime → LLM generates conforming request payload
- Outbound to client: look up planner's declared response schema → LLM normalizes worker result

**Key principles:**
- The planner owns the client contract on both sides. It declares `RESEARCH_COMPLETED_EVENT`
  with inline schema in `events_produced` — the SDK auto-registers it at startup, exactly as
  the worker auto-registers its consumed event schema.
- The client can discover the `research.completed` schema from the Registry.
- `research.worker.completed` is an internal planner↔worker event. The client never sees it.
- Canonical event names throughout; `correlation_id` ties request to response.

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

The script starts the worker first, waits for it to register with the Registry,
then starts the planner.

To trigger a research goal from a second terminal:

```bash
# Default topic
python client.py

# Custom topic
python client.py "Your research question here"
```

---

## Expected Output

**Agent terminals (worker + planner):**
```
[planner] Goal received: research.goal
[planner] Description: 'Latest advances in quantum computing, 2025'
[planner] Discovered 1 agent(s) with capability: web_research
[planner] Schema fetched: research_request_v1
[planner] LLM generated payload: {'topic': '...', 'max_results': 5, 'depth': 'standard'}
[planner] Dispatching → research.requested (internal response: research.worker.completed)
[planner] ✓ Worker request published; awaiting research.worker.completed

[worker]  ▶ Received: research.requested
[worker]  ✓ Research complete — 5 finding(s)

[planner] Worker result received: 5 finding(s) on '...'
[planner] ✓ research.completed sent to client (correlation: <id>)
```

**Client terminal:**
```
[client] ✅ Research complete!
[client] Topic:    Latest advances in quantum computing, 2025
[client] Findings: 5 result(s)
  1. Overview of ...: key concepts and recent developments
     https://example.com/research/1
  ...
```

---

## Files

| File | Purpose |
|---|---|
| `worker.py` | Research worker — inline schema, `task.complete()` response |
| `planner.py` | Discovery planner — discover → schema → LLM → dispatch → normalize → respond |
| `client.py` | Sends `research.goal`; receives `research.completed` from planner |
| `start.sh` | Starts worker then planner; Ctrl-C stops all |
| `.env.example` | Environment variable template |
| `requirements.txt` | Python dependencies |

---

## Related

- **Previous:** [10-choreography-basic](../10-choreography-basic/) — ChoreographyPlanner with known event names
- **Next:** [12-event-selector](../12-event-selector/) — EventSelector intelligent routing
- **SDK internals:** `sdk/python/soorma/agents/base._auto_register_inline_schemas()`
- **SDK method:** `sdk/python/soorma/ai/choreography.ChoreographyPlanner.generate_payload()`
