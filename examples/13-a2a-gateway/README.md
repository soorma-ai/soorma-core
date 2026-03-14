# Example 13 — A2A Gateway Interoperability

This example demonstrates the **A2A (Agent-to-Agent) protocol** gateway
pattern: an external HTTP client sends a request using the Google A2A
specification, the gateway converts it into a Soorma internal event, the
internal agent processes it, and the gateway returns an A2A-compatible
response.

```
External A2A client
       │
       │  POST /a2a/tasks/send (A2A Task JSON)
       ▼
┌──────────────────────┐
│   gateway_service.py  │  FastAPI — A2AGatewayHelper converts A2A ↔ Soorma DTO
└────────┬──────┬───────┘
         │ pub  │ sub (Future resolved on correlation_id match)
         ▼      │
   action-requests      action-results
   (NATS topic)  ──────────────────────
                         │
                         ▼
              ┌─────────────────────┐
              │  internal_agent.py   │  Soorma Worker — knows nothing about A2A
              └─────────────────────┘
```

---

## What This Demonstrates

| Pattern | API Used |
|---------|----------|
| A2A Agent Card generation | `A2AGatewayHelper.agent_to_card()` |
| A2A Task → Soorma event | `A2AGatewayHelper.task_to_event()` |
| Soorma event → A2A response | `A2AGatewayHelper.event_to_response()` |
| Async request-response via NATS | `EventClient` + `asyncio.Future` |
| Internal worker (standard pattern) | `Worker`, `@worker.on_task`, `task.complete()` |

**Key insight:** The internal agent (`internal_agent.py`) knows nothing
about the A2A protocol — it handles ordinary Soorma `research.requested`
events.  The gateway handles all protocol translation via
`A2AGatewayHelper`, keeping the agent reusable across multiple integration
patterns.

---

## Quick Start

### 1. Start the Soorma dev stack

```bash
# From soorma-core root
soorma dev
# Ensure Registry (port 8081) and Event Service (port 8082) are healthy
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env — set SOORMA_DEVELOPER_TENANT_ID and SOORMA_USER_ID
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
# soorma + soorma-common must already be installed (see repo README)
```

### 4. Run the example

```bash
chmod +x start.sh
./start.sh
```

### 5. Run the client driver (in a second terminal)

```bash
# Full demo: show Agent Card, then send 3 tasks
python client.py

# Just view the Agent Card
python client.py card

# Send a single task
python client.py send "Research quantum computing"

# Free-text shorthand — same as send
python client.py What is blockchain?
```

---

## Client Driver (`client.py`)

The client mirrors how a real external A2A caller would interact with the
gateway — using plain HTTP, with no Soorma SDK imports:

1. **Discover** — `GET /.well-known/agent.json` → parse the Agent Card,
   display the name, description, and available skills.
2. **Use** — read `skills[0].inputSchema` to understand accepted input,
   then `POST /a2a/tasks/send` with a conforming message.

This separation is the point: external callers only need to understand the A2A
spec, not anything about NATS, Soorma events, or internal agent topology.

---

## Manual Test (curl)

### Discover agent capabilities (A2A Agent Card)

```bash
curl -s http://localhost:9000/.well-known/agent.json | python -m json.tool
```

**Expected response** (skills aggregated from all registered internal agents):

```json
{
  "name": "Soorma A2A Gateway",
  "description": "Gateway exposing Soorma internal agents via the A2A protocol.",
  "url": "http://localhost:9000",
  "version": "1.0.0",
  "skills": [
    {
      "id": "web_research",
      "name": "web_research",
      "description": "Research a topic and return a concise summary. ...",
      "tags": [],
      "inputSchema": {"$ref": "a2a_research_request_v1"}
    }
  ],
  "authentication": {"schemes": ["none"]}
}
```

### Send an A2A Task

```bash
curl -s -X POST http://localhost:9000/a2a/tasks/send \
  -H "Content-Type: application/json" \
  -d '{
    "id": "task-001",
    "message": {
      "role": "user",
      "parts": [{"type": "text", "text": "Research quantum computing"}]
    }
  }' | python -m json.tool
```

**Expected response** (result data carried in `message.parts`):

```json
{
  "id": "task-001",
  "sessionId": null,
  "status": "completed",
  "message": {
    "role": "agent",
    "parts": [
      {
        "type": "data",
        "data": {
          "summary": "Quantum computing leverages superposition and entanglement...",
          "topic": "Research quantum computing",
          "sources_consulted": 3
        }
      }
    ]
  },
  "error": null
}
```

### Try different topics

```bash
# Machine learning topic
curl -s -X POST http://localhost:9000/a2a/tasks/send \
  -H "Content-Type: application/json" \
  -d '{"id":"task-002","message":{"role":"user","parts":[{"type":"text","text":"Explain machine learning"}]}}' \
  | python -m json.tool

# Blockchain topic
curl -s -X POST http://localhost:9000/a2a/tasks/send \
  -H "Content-Type: application/json" \
  -d '{"id":"task-003","message":{"role":"user","parts":[{"type":"text","text":"What is blockchain?"}]}}' \
  | python -m json.tool
```

---

## Expected Console Output

**Internal agent** (`internal_agent.py`):

```
[research-agent] ✓ research-agent started
[research-agent]   Listening for: research.requested
[research-agent]   Publishes to:  research.completed (via task.complete)
[research-agent]   Gateway can now start routing A2A tasks.
...
[research-agent] ▶ Research requested: 'Research quantum computing'
[research-agent]   task_id=<uuid>
[research-agent]   correlation_id=task-001
[research-agent]   response_event=a2a.response
[research-agent] ✓ Research complete — publishing result
```

**Gateway service** (`gateway_service.py`):

```
INFO:     Application startup complete.
[gateway] EventClient connected — subscribed to action-results
...
[gateway] Received A2A task id=task-001
[gateway] Published research.requested (correlation_id=task-001, response_event=a2a.response)
[gateway] Received response for task task-001 (event_type=a2a.response)
[gateway] ✓ Returning A2A response for task task-001 (status=completed)
```

---

## File Structure

```
examples/13-a2a-gateway/
├── README.md               ← This file
├── .env.example            ← Environment variable template
├── requirements.txt        ← Python dependencies
├── start.sh                ← Starts all processes + shows client commands
├── client.py               ← A2A client driver: discover card, send tasks
├── gateway_service.py      ← FastAPI A2A gateway (A2AGatewayHelper + EventClient)
└── internal_agent.py       ← Soorma Worker (no A2A knowledge)
```

---

## Architecture Notes

### Why does the internal agent not know about A2A?

The A2A protocol is an **integration concern**, not a business logic concern.
The internal agent handles standard Soorma `research.requested` events — the
same events it would receive from a Soorma Planner, an `EventSelector` router,
or any other orchestrator.  The gateway handles all protocol translation.

This separation means:
- Internal agents are **reusable** across A2A clients, Soorma planners, etc.
- Protocol upgrades only require gateway changes
- Agent logic is testable without A2A infrastructure

### Response routing with `asyncio.Future`

The gateway uses a `Dict[str, asyncio.Future]` keyed by `task.id` (= `correlation_id`).

1. Before publishing, the gateway registers a `Future` for the task.
2. The NATS catch-all handler resolves the appropriate `Future` when an event
   arrives on `action-results` with a matching `correlation_id` — the standard
   Soorma request/response pattern.
3. `asyncio.wait_for()` provides the 30-second timeout.

This pattern is safe for concurrent requests because each `task.id` is unique
and futures are cleaned up in the `finally` block regardless of success or
timeout.

### `response_event` naming convention

The gateway sets `response_event="a2a.response"` — a stable, canonical event
type name shared across all tasks.  The internal agent's `task.complete()`
publishes to that event type on the `action-results` topic, carrying the
original `correlation_id` in the envelope.  The catch-all handler matches the
right waiting `Future` using `correlation_id`, not the event type name.

This is consistent with how all Soorma worker/planner pairs communicate — the
event type is semantic ("what happened"), the `correlation_id` is the per-request
tracking key.

---

## Related Examples

- **Example 11** — LLM-based discovery: planner finds worker dynamically via `ctx.registry.discover()`
- **Example 12** — EventSelector routing: LLM picks the right event+worker
- **Example 10** — Choreography: multi-step planner/worker pipeline

## SDK Reference

- `soorma.gateway.A2AGatewayHelper` — protocol conversion helpers
- `soorma.events.EventClient` — lightweight NATS pub/sub (no Worker wrapper)
- `soorma_common.a2a` — A2A protocol DTOs (`A2ATask`, `A2AAgentCard`, `A2ATaskResponse`)
