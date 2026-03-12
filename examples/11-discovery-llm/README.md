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
| `ctx.registry.discover()` — find agents by capability at runtime | `planner.py` |
| `ctx.registry.get_event()` + `get_schema()` — resolve schema from event name | `planner.py` |
| `planner.generate_payload()` — LLM generates conforming payload **(both directions)** | `planner.py` |
| `goal.dispatch()` — lightweight dispatch, auto-propagates tenant/user/correlation context | `planner.py` |
| `ctx.memory.get_goal_metadata()` — retrieve client routing metadata in result handler | `planner.py` |
| `@planner.on_event()` — receive worker result, normalize via schema + LLM, forward to client | `planner.py` |
| `events_consumed=[EventDefinition(...)]` — client declares + auto-registers response schema | `client.py` |
| Canonical event names + `correlation_id` filtering | `client.py` |

---

## Architecture

```
client.py                planner.py                         worker.py
─────────                ──────────                         ─────────
publish                  @on_goal("research.goal")
research.goal    ──────► SDK auto-saves goal metadata
(response_event=         (response_event, response_schema_name,
 research.completed,      tenant_id, user_id) → working memory
 response_schema_name=   discover() → get worker schema
 research_result_v1)     generate_payload()  ← LLM
                         goal.dispatch(                     @on_task("research.requested")
                           "research.requested",   ────────► task.complete(raw_findings)
                           response_event=                             │
                           "research.worker.completed")               │
                                                                       │
                         @on_event(                                    │
                           "research.worker.completed")  ◄─────────────┘
                         memory.get_goal_metadata()
                           → response_schema_name, response_event
                         registry.get_schema("research_result_v1")
                         generate_payload()  ← LLM normalizes raw result
                         bus.respond("research.completed", ...)
◄────────────────────────
research.completed
```

**Symmetric schema-driven dispatch — both directions use the same pattern:**
- Outbound to worker: discover worker schema at runtime → LLM generates conforming request payload
- Outbound to client: look up planner's declared response schema → LLM normalizes worker result

**Key principles:**
- The client owns the response schema contract (see "Client-Owned Schema" section below).
- `research.worker.completed` is an internal planner↔worker event. The client never sees it.
- Canonical event names throughout; `correlation_id` ties request to response.

---

## Planner Pattern: Lightweight Dispatch

This example uses the **lightweight dispatch pattern** — the simplest planner pattern for
single-worker, single-hop workflows. It is the planner-side counterpart of `task.delegate()`
on the worker side.

### What it is

The planner receives a goal, does work (discovery, LLM payload generation), fires one
`goal.dispatch()`, and handles the result in a separate `@on_event()` handler. No state
machine. No persisted plan record.

```python
# on_goal: receive goal, dispatch to worker
@planner.on_goal("research.goal")
async def handle_goal(goal: GoalContext, context: PlatformContext):
    ...
    await goal.dispatch(
        event_type="research.requested",
        data=payload,
        response_event="research.worker.completed",
    )
    # Handler returns — planner is done for now

# on_event: receive worker result, respond to client
@planner.on_event("research.worker.completed", topic=EventTopic.ACTION_RESULTS)
async def handle_result(event: EventEnvelope, context: PlatformContext):
    goal_meta = await context.memory.get_goal_metadata(
        correlation_id=event.correlation_id, ...)
    await context.bus.respond(event_type=goal_meta["response_event"], ...)
```

### `goal.dispatch()` — why it exists

`goal.dispatch()` is the planner-side equivalent of `task.delegate()`. It wraps
`context.bus.request()` and automatically propagates `tenant_id`, `user_id`,
`correlation_id`, and `session_id` from the `GoalContext` envelope — so the full
context chain is preserved end-to-end without any manual threading.

```python
# ✅ Correct — context propagated automatically
await goal.dispatch(event_type="research.requested", data=payload,
                    response_event="research.worker.completed")

# ❌ Wrong — manual threading is fragile and easy to forget
await context.bus.request(event_type="research.requested", data=payload,
                          response_event="research.worker.completed",
                          correlation_id=goal.correlation_id,   # manual
                          tenant_id=goal.tenant_id,             # manual
                          user_id=goal.user_id)                 # manual
```

Missing any of those three causes cascading failures: the worker's `task.complete()`
publishes a result event with null tenant/user, and any memory lookup in the result
handler then fails with 422 or a missing-tenant-id error.

### Goal metadata storage

The `@on_goal` SDK hook automatically saves routing metadata
(`response_event`, `response_schema_name`, `tenant_id`, `user_id`) to working memory
under `plan_id=correlation_id`. The result handler retrieves it via
`context.memory.get_goal_metadata(correlation_id, ...)`. No manual boilerplate.

`correlation_id` is used as the working memory scope because no formal `PlanContext` (and
therefore no generated `plan_id`) exists in this pattern. It is a valid UUID and naturally
isolates each goal's metadata from all others.

### When to use lightweight dispatch

| Use lightweight dispatch when… | Use PlanContext when… |
|---|---|
| Single worker, single hop | Multiple workers, multiple steps |
| Linear: request → result → respond | Branching or conditional flows |
| No resumability needed | Must survive crashes / restarts |
| Workflow fits in two event handlers | Requires `on_transition()` state machine |

### Contrast with PlanContext pattern

`PlanContext` creates a **durable plan record** in the Memory Service, with a formal
state machine (`start → research → complete`). `on_transition()` restores and
advances that state machine as each result arrives. The plan's UUID is the memory scope.

```python
# PlanContext pattern (examples 09, 10)
plan = await PlanContext.create_from_goal(goal=goal, context=context,
                                          state_machine=states, current_state="start")
await plan.execute_next()   # Fires initial task, handler returns

@planner.on_transition()
async def handle_transition(event, context, plan: PlanContext, next_state):
    plan.current_state = next_state
    await plan.execute_next()   # SDK restores plan, advances state
```

See [09-planner-basic](../09-planner-basic/) for a complete `PlanContext` walkthrough and
[10-choreography-basic](../10-choreography-basic/) for a multi-step state machine with
`ChoreographyPlanner`.

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
