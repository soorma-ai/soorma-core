"""
Technical Support Worker — Example 12: EventSelector Intelligent Routing.

Handles technical support tickets (bugs, crashes, integration issues).
Registers itself with the Registry at startup via the SDK so the router's
EventSelector can discover it and route tickets here.

Key SDK usage:
  - AgentCapability with inline payload_schema (auto-registered at startup)
  - Worker.on_task() handler — receives TaskContext and PlatformContext
  - task.complete() to publish the response
"""

import asyncio
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

TECHNICAL_TICKET_EVENT = EventDefinition(
    event_name="ticket.technical",
    topic="action-requests",
    description="A customer support ticket requiring technical investigation",
    payload_schema_name="technical_ticket_v1",
    payload_schema={
        "type": "object",
        "properties": {
            "ticket_id": {"type": "string", "description": "Unique ticket identifier"},
            "customer": {"type": "string", "description": "Customer name or ID"},
            "subject": {"type": "string", "description": "Ticket subject line"},
            "description": {"type": "string", "description": "Full ticket description"},
            "priority": {
                "type": "string",
                "enum": ["low", "medium", "high", "critical"],
                "default": "medium",
            },
        },
        "required": ["ticket_id", "customer", "subject", "description"],
    },
)

TICKET_RESOLVED_EVENT = EventDefinition(
    event_name="ticket.resolved",
    topic="action-responses",
    description="Technical ticket resolution from technical-support-worker",
)

# ---------------------------------------------------------------------------
# Worker declaration
# ---------------------------------------------------------------------------

worker = Worker(
    name="technical-support-worker",
    description=(
        "Handles technical support tickets: bug reports, API errors, "
        "integration failures, and system crashes"
    ),
    capabilities=[
        AgentCapability(
            task_name="technical_support",
            description=(
                "Investigate and resolve technical issues including bugs, "
                "crashes, API errors, and integration failures"
            ),
            consumed_event=TECHNICAL_TICKET_EVENT,
            produced_events=[TICKET_RESOLVED_EVENT],
        )
    ],
    auth_token_provider=EXAMPLE_TOKEN_PROVIDER,
)


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------

@worker.on_task("ticket.technical")
async def handle_technical_ticket(task: TaskContext, context: PlatformContext) -> None:
    """Handle an incoming technical support ticket.

    Args:
        task: TaskContext containing the ticket payload.
        context: PlatformContext (used internally by task.complete()).
    """
    ticket_id: str = task.data.get("ticket_id", "unknown")
    customer: str = task.data.get("customer", "unknown")
    subject: str = task.data.get("subject", "")
    priority: str = task.data.get("priority", "medium")

    print(f"\n[technical-worker]  ▶ Received: ticket.technical")
    print(f"[technical-worker]  Ticket: {ticket_id}  Customer: {customer}")
    print(f"[technical-worker]  Subject: {subject!r}  Priority: {priority}")

    # Simulate technical triage
    resolution = _triage_technical_ticket(subject, priority)

    print(f"[technical-worker]  ✓ Triaged — action: {resolution['action']}")

    await task.complete({
        "ticket_id": ticket_id,
        "customer": customer,
        "handled_by": "technical-support-worker",
        "resolution": resolution,
    })


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _triage_technical_ticket(subject: str, priority: str) -> dict:
    """Simulate technical triage logic.

    Args:
        subject: Ticket subject.
        priority: Priority level.

    Returns:
        Dict with 'action', 'team', and 'estimated_resolution' keys.
    """
    if priority == "critical":
        return {
            "action": "escalate_to_on_call",
            "team": "platform-engineering",
            "estimated_resolution": "1 hour",
        }
    return {
        "action": "create_jira_ticket",
        "team": "technical-support",
        "estimated_resolution": "24-48 hours",
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    worker.run()
