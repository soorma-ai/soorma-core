"""
Escalation Worker — Example 12: EventSelector Intelligent Routing.

Handles escalation tickets that are complex, high-value, or require
management attention (e.g. legal threats, enterprise churn risk,
regulatory complaints).

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

ESCALATION_TICKET_EVENT = EventDefinition(
    event_name="ticket.escalation",
    topic="action-requests",
    description=(
        "A customer support ticket requiring management escalation — "
        "legal threats, enterprise churn risk, or regulatory complaints"
    ),
    payload_schema_name="escalation_ticket_v1",
    payload_schema={
        "type": "object",
        "properties": {
            "ticket_id": {"type": "string", "description": "Unique ticket identifier"},
            "customer": {"type": "string", "description": "Customer name or ID"},
            "subject": {"type": "string", "description": "Ticket subject line"},
            "description": {"type": "string", "description": "Full ticket description"},
            "escalation_reason": {
                "type": "string",
                "enum": [
                    "legal_threat",
                    "enterprise_churn",
                    "regulatory_complaint",
                    "media_risk",
                    "vip_customer",
                    "other",
                ],
                "description": "Primary reason for escalation",
            },
            "contract_value": {
                "type": "number",
                "description": "Annual contract value in USD (for enterprise churn risk)",
            },
        },
        "required": ["ticket_id", "customer", "subject", "description"],
    },
)

TICKET_RESOLVED_EVENT = EventDefinition(
    event_name="ticket.resolved",
    topic="action-responses",
    description="Escalation ticket resolution from escalation-worker",
)

# ---------------------------------------------------------------------------
# Worker declaration
# ---------------------------------------------------------------------------

worker = Worker(
    name="escalation-worker",
    description=(
        "Handles high-priority escalations requiring management attention: "
        "legal threats, enterprise churn risk, regulatory complaints, and VIP customers"
    ),
    capabilities=[
        AgentCapability(
            task_name="escalation_handling",
            description=(
                "Triage and route escalations to the appropriate senior team: "
                "legal, account management, compliance, or executive sponsor"
            ),
            consumed_event=ESCALATION_TICKET_EVENT,
            produced_events=[TICKET_RESOLVED_EVENT],
        )
    ],
    auth_token_provider=EXAMPLE_TOKEN_PROVIDER,
)


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------

@worker.on_task("ticket.escalation")
async def handle_escalation(task: TaskContext, context: PlatformContext) -> None:
    """Handle an incoming escalation ticket.

    Args:
        task: TaskContext containing the escalation payload.
        context: PlatformContext (used internally by task.complete()).
    """
    ticket_id: str = task.data.get("ticket_id", "unknown")
    customer: str = task.data.get("customer", "unknown")
    subject: str = task.data.get("subject", "")
    reason: str = task.data.get("escalation_reason", "other")
    contract_value: float = task.data.get("contract_value", 0.0)

    print(f"\n[escalation-worker]  ▶ Received: ticket.escalation")
    print(f"[escalation-worker]  Ticket: {ticket_id}  Customer: {customer}")
    print(f"[escalation-worker]  Subject: {subject!r}  Reason: {reason}")
    if contract_value:
        print(f"[escalation-worker]  Contract value: ${contract_value:,.0f}")

    routing = _route_escalation(reason, contract_value)

    print(f"[escalation-worker]  ✓ Routed to: {routing['team']}")

    await task.complete({
        "ticket_id": ticket_id,
        "customer": customer,
        "handled_by": "escalation-worker",
        "routing": routing,
    })


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _route_escalation(reason: str, contract_value: float) -> dict:
    """Determine the escalation routing path.

    Args:
        reason: Escalation reason code.
        contract_value: Annual contract value in USD.

    Returns:
        Dict with 'team', 'contact', and 'sla' keys.
    """
    routes = {
        "legal_threat": {
            "team": "legal",
            "contact": "legal@company.com",
            "sla": "2 hours",
        },
        "regulatory_complaint": {
            "team": "compliance",
            "contact": "compliance@company.com",
            "sla": "4 hours",
        },
        "media_risk": {
            "team": "communications",
            "contact": "pr@company.com",
            "sla": "1 hour",
        },
        "enterprise_churn": {
            "team": "account_management",
            "contact": "enterprise@company.com",
            "sla": "1 hour" if contract_value >= 100_000 else "4 hours",
        },
        "vip_customer": {
            "team": "executive_sponsor",
            "contact": "vip-support@company.com",
            "sla": "2 hours",
        },
    }
    return routes.get(reason, {
        "team": "senior_support",
        "contact": "escalations@company.com",
        "sla": "4 hours",
    })


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    worker.run()
