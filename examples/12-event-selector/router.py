"""
Ticket Router — Example 12: EventSelector Intelligent Routing.

Demonstrates EventSelector for LLM-based event routing.  The router
receives a generic "ticket submitted" event, uses EventSelector to
discover all registered worker events on the action-requests topic, and
lets the LLM decide which worker should handle the ticket.

This eliminates hard-coded if/elif routing logic — new workers
self-register with the Registry and the router automatically learns about
them without any router code changes.

SDK patterns shown:
  - EventSelector(context=ctx, topic=..., model=...) — LLM-based routing
  - selector.select_event(state={...}) — LLM picks the right event
  - selector.publish_decision(decision, correlation_id=..., response_event=...) — publish
  - @worker.on_task() for the routing entry point (router is itself a Worker)
"""

import logging
import os
from typing import Any, Dict

from dotenv import load_dotenv

from soorma import Worker
from soorma.ai.selection import EventSelector, EventSelectionError
from soorma.context import PlatformContext
from soorma.task_context import TaskContext
from soorma_common import AgentCapability, EventDefinition
from soorma_common.events import EventTopic

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Event definitions
# ---------------------------------------------------------------------------

# The router consumes a generic "ticket submitted" event carrying the raw
# customer ticket.  It then uses EventSelector to decide which specialist
# worker should handle it.
TICKET_SUBMITTED_EVENT = EventDefinition(
    event_name="ticket.submitted",
    topic="action-requests",
    description="A new customer support ticket requiring routing to the correct team",
    payload_schema_name="ticket_submitted_v1",
    payload_schema={
        "type": "object",
        "properties": {
            "ticket_id": {"type": "string", "description": "Unique ticket identifier"},
            "customer": {"type": "string", "description": "Customer name or ID"},
            "subject": {"type": "string", "description": "Ticket subject line"},
            "description": {
                "type": "string",
                "description": "Full ticket description from the customer",
            },
            "metadata": {
                "type": "object",
                "description": "Optional extra context (contract_value, invoice_id, etc.)",
                "additionalProperties": True,
            },
        },
        "required": ["ticket_id", "customer", "subject", "description"],
    },
)

TICKET_ROUTED_EVENT = EventDefinition(
    event_name="ticket.routed",
    topic="action-responses",
    description="Acknowledgement that the ticket was successfully routed",
)

# ---------------------------------------------------------------------------
# Router declaration  (router is itself a Worker — it handles ticket.submitted)
# ---------------------------------------------------------------------------

router = Worker(
    name="ticket-router",
    description=(
        "Routes incoming customer support tickets to the correct specialist worker "
        "using LLM-based event selection.  No hard-coded routing rules."
    ),
    capabilities=[
        AgentCapability(
            task_name="ticket_routing",
            description=(
                "Classify and route a raw support ticket to the correct specialist: "
                "technical (bugs/API errors), billing (charges/refunds), "
                "or escalation (legal/enterprise/VIP)"
            ),
            consumed_event=TICKET_SUBMITTED_EVENT,
            produced_events=[TICKET_ROUTED_EVENT],
        )
    ],
)


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------

@router.on_task("ticket.submitted")
async def route_ticket(task: TaskContext, context: PlatformContext) -> None:
    """Route an incoming ticket to the appropriate specialist worker.

    Uses EventSelector to discover all worker events registered on the
    action-requests topic and lets the LLM decide which one best matches
    the ticket's content.

    Args:
        task: TaskContext containing the ticket payload.
        context: PlatformContext providing EventSelector access via context.toolkit
                 and context.bus for publishing the routing decision.
    """
    ticket_id: str = task.data.get("ticket_id", "unknown")
    customer: str = task.data.get("customer", "unknown")
    subject: str = task.data.get("subject", "")
    description: str = task.data.get("description", "")
    metadata: Dict[str, Any] = task.data.get("metadata", {})

    print(f"\n[router]  ▶ Received: ticket.submitted")
    print(f"[router]  Ticket: {ticket_id}  Customer: {customer}")
    print(f"[router]  Subject: {subject!r}")

    model = os.environ.get("LLM_MODEL", "gpt-4o-mini")

    # EventSelector discovers all events on the action-requests topic from the
    # Registry and asks the LLM to pick the best match.
    # Zero hard-coded event names — the router adapts automatically as new
    # workers register themselves.
    selector = EventSelector(
        context=context,
        topic=EventTopic.ACTION_REQUESTS,
        model=model,
    )

    # Build the routing state — give the LLM enough context to make a good decision
    routing_state: Dict[str, Any] = {
        "ticket_id": ticket_id,
        "customer": customer,
        "subject": subject,
        "description": description,
        # Exclude the router's own event from candidates by naming the intent
        "routing_intent": (
            "Route this ticket to the most appropriate specialist worker. "
            "Do NOT route to ticket.submitted (that is this router itself). "
            "Choose from ticket.technical, ticket.billing, or ticket.escalation "
            "based on the ticket content."
        ),
        **metadata,
    }

    try:
        print(f"[router]  Asking {model} to select routing event...")
        decision = await selector.select_event(state=routing_state)

        print(f"[router]  ✓ LLM selected: {decision.event_type}")
        print(f"[router]  Reasoning: {decision.reasoning}")

        # Publish the routing decision with explicit response_event (§3 choreography)
        await selector.publish_decision(
            decision=decision,
            correlation_id=task.task_id,
            response_event="ticket.resolved",
        )

        print(f"[router]  ✓ Ticket {ticket_id} routed to {decision.event_type}")

        # Acknowledge routing to the original publisher
        await task.complete({
            "ticket_id": ticket_id,
            "routed_to": decision.event_type,
            "reasoning": decision.reasoning,
        })

    except EventSelectionError as exc:
        # EventSelector failed to produce a valid decision — route to escalation
        # as a safe fallback rather than dropping the ticket
        logger.error(
            "[router] EventSelection failed for ticket %s: %s — falling back to escalation",
            ticket_id,
            exc,
        )
        print(f"[router]  ⚠ EventSelection failed — routing to escalation as fallback")

        await context.bus.publish(
            topic=EventTopic.ACTION_REQUESTS,
            event_type="ticket.escalation",
            data={
                "ticket_id": ticket_id,
                "customer": customer,
                "subject": subject,
                "description": description,
                "escalation_reason": "other",
            },
            correlation_id=task.task_id,
            response_event="ticket.resolved",
        )

        await task.complete({
            "ticket_id": ticket_id,
            "routed_to": "ticket.escalation",
            "reasoning": f"EventSelectionError fallback: {exc}",
        })


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    router.run()
