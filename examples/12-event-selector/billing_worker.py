"""
Billing Support Worker — Example 12: EventSelector Intelligent Routing.

Handles billing and payment related support tickets (charges, refunds,
invoices, subscription changes).

Key SDK usage:
  - AgentCapability with inline payload_schema (auto-registered at startup)
  - Worker.on_task() handler — receives TaskContext and PlatformContext
  - task.complete() to publish the response
"""

import logging
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv

from soorma import Worker
from soorma.context import PlatformContext
from soorma.task_context import TaskContext
from soorma_common import AgentCapability, EventDefinition

from examples.shared.auth import build_example_token_provider

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

EXAMPLE_NAME = "12-event-selector"
EXAMPLE_TOKEN_PROVIDER = build_example_token_provider(EXAMPLE_NAME, __file__)

# ---------------------------------------------------------------------------
# Event definitions
# ---------------------------------------------------------------------------

BILLING_TICKET_EVENT = EventDefinition(
    event_name="ticket.billing",
    topic="action-requests",
    description="A customer support ticket related to billing, charges, or payments",
    payload_schema_name="billing_ticket_v1",
    payload_schema={
        "type": "object",
        "properties": {
            "ticket_id": {"type": "string", "description": "Unique ticket identifier"},
            "customer": {"type": "string", "description": "Customer name or ID"},
            "subject": {"type": "string", "description": "Ticket subject line"},
            "description": {"type": "string", "description": "Full ticket description"},
            "amount": {
                "type": "number",
                "description": "Dollar amount in dispute (if applicable)",
            },
            "invoice_id": {
                "type": "string",
                "description": "Invoice or transaction ID (if applicable)",
            },
        },
        "required": ["ticket_id", "customer", "subject", "description"],
    },
)

TICKET_RESOLVED_EVENT = EventDefinition(
    event_name="ticket.resolved",
    topic="action-responses",
    description="Billing ticket resolution from billing-support-worker",
)

# ---------------------------------------------------------------------------
# Worker declaration
# ---------------------------------------------------------------------------

worker = Worker(
    name="billing-support-worker",
    description=(
        "Handles billing and payment support tickets: incorrect charges, "
        "refund requests, invoice disputes, and subscription changes"
    ),
    capabilities=[
        AgentCapability(
            task_name="billing_support",
            description=(
                "Process billing inquiries including charge disputes, refund requests, "
                "invoice corrections, and subscription management"
            ),
            consumed_event=BILLING_TICKET_EVENT,
            produced_events=[TICKET_RESOLVED_EVENT],
        )
    ],
    auth_token_provider=EXAMPLE_TOKEN_PROVIDER,
)


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------

@worker.on_task("ticket.billing")
async def handle_billing_ticket(task: TaskContext, context: PlatformContext) -> None:
    """Handle an incoming billing support ticket.

    Args:
        task: TaskContext containing the ticket payload.
        context: PlatformContext (used internally by task.complete()).
    """
    ticket_id: str = task.data.get("ticket_id", "unknown")
    customer: str = task.data.get("customer", "unknown")
    subject: str = task.data.get("subject", "")
    amount: float = task.data.get("amount", 0.0)

    print(f"\n[billing-worker]  ▶ Received: ticket.billing")
    print(f"[billing-worker]  Ticket: {ticket_id}  Customer: {customer}")
    print(f"[billing-worker]  Subject: {subject!r}  Amount: ${amount:.2f}")

    resolution = _process_billing_ticket(subject, amount)

    print(f"[billing-worker]  ✓ Processed — action: {resolution['action']}")

    await task.complete({
        "ticket_id": ticket_id,
        "customer": customer,
        "handled_by": "billing-support-worker",
        "resolution": resolution,
    })


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _process_billing_ticket(subject: str, amount: float) -> dict:
    """Simulate billing ticket processing logic.

    Args:
        subject: Ticket subject.
        amount: Dollar amount in dispute.

    Returns:
        Dict with 'action', 'status', and 'notes' keys.
    """
    subject_lower = subject.lower()
    if "refund" in subject_lower:
        return {
            "action": "initiate_refund",
            "status": "refund_queued",
            "notes": f"Refund of ${amount:.2f} queued for processing within 3-5 business days.",
        }
    if "cancel" in subject_lower or "subscription" in subject_lower:
        return {
            "action": "review_subscription",
            "status": "account_review",
            "notes": "Subscription change request forwarded to account management.",
        }
    return {
        "action": "investigate_charge",
        "status": "under_review",
        "notes": "Charge dispute logged for billing team review within 2 business days.",
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    worker.run()
