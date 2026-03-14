"""
Client — Example 12: EventSelector Intelligent Ticket Routing.

Submits a support ticket to the router and waits for the resolution response.
The router uses EventSelector to dynamically pick the correct specialist worker
(technical, billing, or escalation) based on the ticket content.

The client publishes a generic `ticket.submitted` event and listens for
`ticket.resolved` — it never needs to know which specialist handled it.

Usage:
    # Technical ticket (bug report)
    python client.py technical

    # Billing ticket (charge dispute)
    python client.py billing

    # Escalation ticket (enterprise churn risk)
    python client.py escalation

    # Default (technical)
    python client.py
"""

import asyncio
import sys
from typing import Any, Dict
from uuid import uuid4

from dotenv import load_dotenv

from soorma import EventClient
from soorma_common.events import EventEnvelope, EventTopic

load_dotenv()

# Authentication context — mirrors the env vars used by the agents
import os

TENANT_ID = os.environ.get("TENANT_ID", "00000000-0000-0000-0000-000000000000")
USER_ID = os.environ.get("USER_ID", "00000000-0000-0000-0000-000000000001")

TIMEOUT_SECONDS = 30.0

# ---------------------------------------------------------------------------
# Sample tickets — one per category so the CLI arg drives the scenario
# ---------------------------------------------------------------------------

SAMPLE_TICKETS: Dict[str, Dict[str, Any]] = {
    "technical": {
        "ticket_id": f"TKT-{uuid4().hex[:6].upper()}",
        "customer": "Acme Corp",
        "subject": "API returns 500 on POST /orders since yesterday's deploy",
        "description": (
            "Our integration started failing after your platform update yesterday. "
            "POST /orders returns HTTP 500 with no response body. We have retried "
            "with different payloads and the issue persists. Affects all our customers."
        ),
        "metadata": {"priority": "high"},
    },
    "billing": {
        "ticket_id": f"TKT-{uuid4().hex[:6].upper()}",
        "customer": "Beta Ltd",
        "subject": "Charged twice for February invoice — need refund",
        "description": (
            "We were billed $2,400 twice for the same billing period. "
            "Invoice INV-2026-002 appears to be a duplicate of INV-2026-001. "
            "Please process a refund for the duplicate charge."
        ),
        "metadata": {"invoice_id": "INV-2026-002", "amount": 2400.0},
    },
    "escalation": {
        "ticket_id": f"TKT-{uuid4().hex[:6].upper()}",
        "customer": "Gamma Enterprise",
        "subject": "Executive review of contract renewal — SLA violations in Q1",
        "description": (
            "Our executive team is reviewing the Annual contract renewal ($250k). "
            "We have documented 3 P1 outages in Q1 2026 that violated our SLA. "
            "We require a formal SLA credit review and executive sponsor meeting "
            "before we can proceed with renewal."
        ),
        "metadata": {"contract_value": 250_000.0},
    },
}


async def submit_ticket(ticket_type: str) -> None:
    """Submit a support ticket and wait for the routing resolution.

    Args:
        ticket_type: One of 'technical', 'billing', 'escalation'.
    """
    ticket = SAMPLE_TICKETS.get(ticket_type, SAMPLE_TICKETS["technical"])

    client = EventClient(
        agent_id="ticket-client",
        source="ticket-client",
    )

    print("=" * 60)
    print("  Example 12 — EventSelector Intelligent Routing Client")
    print("=" * 60)
    print()
    print(f"  Ticket type:  {ticket_type}")
    print(f"  Ticket ID:    {ticket['ticket_id']}")
    print(f"  Customer:     {ticket['customer']}")
    print(f"  Subject:      {ticket['subject']!r}")
    print()

    correlation_id = str(uuid4())

    response_received = asyncio.Event()
    resolution_data: dict = {}
    routing_data: dict = {}

    @client.on_event("ticket.routed", topic=EventTopic.ACTION_RESULTS)
    async def on_routed(event: EventEnvelope) -> None:
        """Receive routing acknowledgement from the router.

        Args:
            event: EventEnvelope published by router.py via task.complete().
        """
        if event.correlation_id != correlation_id:
            return
        routing_data.update(event.data or {})
        print(
            f"[client] ↳ Router selected: {routing_data.get('routed_to', '?')}"
        )
        print(f"[client]   Reasoning: {routing_data.get('reasoning', '?')}")

    @client.on_event("ticket.resolved", topic=EventTopic.ACTION_RESULTS)
    async def on_resolved(event: EventEnvelope) -> None:
        """Receive the specialist worker's resolution.

        Args:
            event: EventEnvelope published by technical/billing/escalation worker
                   via task.complete().
        """
        if event.correlation_id != correlation_id:
            return
        resolution_data.update(event.data or {})
        response_received.set()

    await client.connect(topics=[EventTopic.ACTION_RESULTS])

    # Build the payload — include all ticket fields plus optional metadata fields
    payload: Dict[str, Any] = {
        "ticket_id": ticket["ticket_id"],
        "customer": ticket["customer"],
        "subject": ticket["subject"],
        "description": ticket["description"],
        "metadata": ticket.get("metadata", {}),
    }

    print(f"[client] Submitting ticket (correlation: {correlation_id[:8]}...)...")
    print()

    await client.publish(
        event_type="ticket.submitted",
        topic=EventTopic.ACTION_REQUESTS,
        data=payload,
        correlation_id=correlation_id,
        response_event="ticket.resolved",
        response_topic=EventTopic.ACTION_RESULTS,
        tenant_id=TENANT_ID,
        user_id=USER_ID,
    )

    try:
        await asyncio.wait_for(response_received.wait(), timeout=TIMEOUT_SECONDS)

        handled_by = resolution_data.get("handled_by", "unknown")
        resolution = resolution_data.get("resolution") or resolution_data.get("routing", {})

        print()
        print("[client] ✅ Ticket resolved!")
        print(f"[client]   Handled by:   {handled_by}")
        print(f"[client]   Ticket ID:    {resolution_data.get('ticket_id', ticket['ticket_id'])}")

        if isinstance(resolution, dict):
            for key, value in resolution.items():
                print(f"[client]   {key.replace('_', ' ').title()}: {value}")

    except asyncio.TimeoutError:
        print(f"\n⚠️  Timeout after {TIMEOUT_SECONDS}s — no resolution received.")
        print("   Make sure all agents are running: ./start.sh")
        print(f"   Then try: python client.py {ticket_type}")

    finally:
        await client.disconnect()


if __name__ == "__main__":
    ticket_type = sys.argv[1] if len(sys.argv) > 1 else "technical"
    if ticket_type not in SAMPLE_TICKETS:
        print(f"Unknown ticket type: {ticket_type!r}")
        print(f"Valid types: {', '.join(SAMPLE_TICKETS)}")
        sys.exit(1)
    try:
        asyncio.run(submit_ticket(ticket_type))
    except KeyboardInterrupt:
        print("\n🛑 Interrupted")
