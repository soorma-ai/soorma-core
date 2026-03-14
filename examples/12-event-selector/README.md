# Example 12: EventSelector — Intelligent Ticket Routing

This example demonstrates **LLM-based event routing** using `EventSelector`. A ticket
router receives generic support tickets and dynamically selects the correct specialist
worker — without any hard-coded `if/elif` routing logic.

## What You'll Learn

| Concept | Where |
|---------|-------|
| `EventSelector` — LLM picks the right event from the Registry catalogue | `router.py` |
| `selector.select_event(state)` — structured state drives the LLM decision | `router.py` |
| `selector.publish_decision(decision, ...)` — explicit `response_event` per §3 | `router.py` |
| Workers self-register event types so the router discovers them automatically | `*_worker.py` |
| `EventSelectionError` fallback — safe default when LLM routing fails | `router.py` |
| Inline `payload_schema` on `AgentCapability` — SDK auto-registers at startup | `*_worker.py` |

## Architecture

```
  Ticket Client
       │
       │  ticket.submitted
       ▼
  ┌─────────────┐
  │   Router    │   EventSelector discovers all workers on action-requests topic
  │             │───▶ Registry.discover_events(topic=ACTION_REQUESTS)
  │             │◀─── [ticket.technical, ticket.billing, ticket.escalation]
  │             │
  │             │   LLM selects best match from ticket content
  │             │───▶ LiteLLM (gpt-4o-mini)
  │             │◀─── EventDecision(event_type="ticket.billing", payload={...})
  └─────────────┘
       │
       │  ticket.billing  (or technical / escalation)
       ▼
  ┌────────────────────────────────────────────────┐
  │  technical-worker │ billing-worker │ escalation-worker  │
  └────────────────────────────────────────────────┘
       │
       │  ticket.resolved
       ▼
  Ticket Client
```

## The Key Pattern: No Hard-Coded Routing

Traditional ticket routers use brittle `if/elif` chains:

```python
# ❌ Hard-coded routing — breaks every time a new team is added
if "bug" in subject or "crash" in subject:
    publish("ticket.technical", payload)
elif "charge" in subject or "refund" in subject:
    publish("ticket.billing", payload)
else:
    publish("ticket.escalation", payload)
```

With `EventSelector`, the router discovers available worker events from the Registry
and delegates the routing decision to the LLM:

```python
# ✅ Dynamic routing — works with any workers that register themselves
selector = EventSelector(
    context=context,
    topic=EventTopic.ACTION_REQUESTS,
    model="gpt-4o-mini",
)
decision = await selector.select_event(state={
    "subject": "API returns 500 on /orders endpoint",
    "description": "Getting server errors since yesterday's deploy...",
})
await selector.publish_decision(decision, correlation_id=task.task_id)
# → LLM selects ticket.technical, SDK validates it exists, publishes it
```

New workers register themselves and the router automatically learns about them —
no router code changes required.

## File Structure

```
12-event-selector/
├── README.md              # This file
├── .env.example           # Required environment variables
├── requirements.txt       # Python dependencies
├── start.sh               # Start all agents
├── technical_worker.py    # Handles bug reports and API errors
├── billing_worker.py      # Handles charge disputes and refunds
├── escalation_worker.py   # Handles legal threats and enterprise churn
└── router.py              # Routes tickets using EventSelector
```

## Prerequisites

1. Platform services running: `soorma dev --build`
2. An LLM API key configured in your `.env`

## Quick Start

```bash
# 1. Copy and configure environment
cp .env.example .env
# Edit .env — set OPENAI_API_KEY (or ANTHROPIC_API_KEY + LLM_MODEL)

# 2. Install dependencies (uses the project's shared venv)
pip install -r requirements.txt

# 3. Start all agents
./start.sh
```

## Send a Test Ticket

With `./start.sh` running, open a second terminal and use the test client:

```bash
# Technical ticket (API bug report) — routes to technical-worker
python client.py technical

# Billing ticket (charge dispute) — routes to billing-worker
python client.py billing

# Escalation ticket (enterprise churn risk) — routes to escalation-worker
python client.py escalation
```

Or send a raw event manually:

## Expected Output

```
[technical-worker]  ▶ Received: ticket.technical
[technical-worker]  Ticket: TKT-001  Customer: Acme Corp
[technical-worker]  Subject: 'API returns 500 on /orders endpoint ...'  Priority: medium
[technical-worker]  ✓ Triaged — action: create_jira_ticket

[billing-worker]  ▶ Received: ticket.billing
[billing-worker]  Ticket: TKT-002  Customer: Beta Ltd
[billing-worker]  Subject: 'Charged twice for February invoice'  Amount: $2400.00
[billing-worker]  ✓ Processed — action: investigate_charge

[escalation-worker]  ▶ Received: ticket.escalation
[escalation-worker]  Ticket: TKT-003  Customer: Gamma Enterprise
[escalation-worker]  Subject: 'Evaluating contract renewal ...'  Reason: enterprise_churn
[escalation-worker]  Contract value: $250,000
[escalation-worker]  ✓ Routed to: account_management
```

## EventSelector Error Handling

If the LLM fails to produce a valid routing decision (malformed JSON, hallucinated event
name, or API error), `EventSelector` raises `EventSelectionError`. The router handles
this gracefully by routing to escalation as a safe fallback:

```python
try:
    decision = await selector.select_event(state=routing_state)
    await selector.publish_decision(decision, correlation_id=task.task_id)
except EventSelectionError as exc:
    # Safe fallback — never drop a ticket
    await context.bus.publish(
        topic=EventTopic.ACTION_REQUESTS,
        event_type="ticket.escalation",
        data={...},
        correlation_id=task.task_id,
    )
```

## Architecture Compliance

- ✅ **Two-layer SDK:** `EventSelector(context=ctx, ...)` — no direct Registry or LiteLLM imports in router
- ✅ **Event Choreography §3:** Explicit `response_event="ticket.resolved"` in `publish_decision()`
- ✅ **Schema auto-registration:** Workers declare `payload_schema` inline; SDK handles Registry calls
- ✅ **No hard-coded event names in router:** All routing events discovered dynamically

## Next Steps

- **Example 13:** [13-a2a-gateway](../13-a2a-gateway/) — Expose a Soorma agent to external HTTP clients via the A2A protocol
- **Docs:** [EventSelector Architecture](../../docs/discovery/ARCHITECTURE.md)
