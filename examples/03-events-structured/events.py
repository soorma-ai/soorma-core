#!/usr/bin/env python3
"""
Event Definitions

Defines structured events with rich metadata for LLM-based reasoning.
Events are automatically registered by the SDK when agents start.
"""

from typing import Optional
from pydantic import BaseModel, Field
from soorma_common import EventDefinition, EventTopic


# =============================================================================
# Ticket Routing Event Payloads
# =============================================================================

class TicketCreatedPayload(BaseModel):
    ticket_id: str = Field(..., description="Unique ticket identifier")
    customer: str = Field(..., description="Customer name")
    description: str = Field(..., description="Issue description")
    priority: str = Field(..., description="Priority level")


class Tier1RoutePayload(BaseModel):
    ticket_id: str = Field(..., description="Ticket to route")
    category: str = Field(..., description="Issue category")
    priority: str = Field(..., description="Priority level")


class Tier2RoutePayload(BaseModel):
    ticket_id: str = Field(..., description="Ticket to route")
    category: str = Field(..., description="Issue category")
    severity: str = Field(..., description="Severity level")
    technical_area: str = Field(..., description="Technical domain")


class SpecialistRoutePayload(BaseModel):
    ticket_id: str = Field(..., description="Ticket to route")
    specialist_type: str = Field(..., description="Required specialist type")
    urgency: str = Field(..., description="Urgency level")


class ManagementEscalationPayload(BaseModel):
    ticket_id: str = Field(..., description="Ticket to escalate")
    escalation_reason: str = Field(..., description="Reason for escalation")
    customer_tier: str = Field(..., description="Customer tier/priority")


class AutoclosePayload(BaseModel):
    ticket_id: str = Field(..., description="Ticket to close")
    reason: str = Field(..., description="Reason for auto-closure")


# =============================================================================
# Event Definitions
# =============================================================================

# Ticket created (business fact)
TICKET_CREATED_EVENT = EventDefinition(
    event_name="ticket.created",
    topic=EventTopic.BUSINESS_FACTS,
    description="A support ticket has been created",
    payload_schema=TicketCreatedPayload.model_json_schema(),
)

# Routing events (action requests)
TIER1_ROUTE_EVENT = EventDefinition(
    event_name="ticket.route.tier1",
    topic=EventTopic.ACTION_REQUESTS,
    description="Route ticket to Tier 1 general support for common issues like password resets, account questions, basic troubleshooting",
    payload_schema=Tier1RoutePayload.model_json_schema(),
)

TIER2_ROUTE_EVENT = EventDefinition(
    event_name="ticket.route.tier2",
    topic=EventTopic.ACTION_REQUESTS,
    description="Route ticket to Tier 2 technical support for technical issues requiring specialized knowledge like API errors, integration problems, performance issues",
    payload_schema=Tier2RoutePayload.model_json_schema(),
)

SPECIALIST_ROUTE_EVENT = EventDefinition(
    event_name="ticket.route.specialist",
    topic=EventTopic.ACTION_REQUESTS,
    description="Route ticket to domain specialist for complex issues requiring deep expertise in specific domains like security, data migration, custom integrations",
    payload_schema=SpecialistRoutePayload.model_json_schema(),
)

MANAGEMENT_ESCALATION_EVENT = EventDefinition(
    event_name="ticket.escalate.management",
    topic=EventTopic.ACTION_REQUESTS,
    description="Escalate ticket to management for critical issues, VIP customers, or situations requiring management attention",
    payload_schema=ManagementEscalationPayload.model_json_schema(),
)

AUTOCLOSE_EVENT = EventDefinition(
    event_name="ticket.autoclose",
    topic=EventTopic.ACTION_REQUESTS,
    description="Automatically close ticket for spam, duplicate tickets, or tickets that can be resolved with automated responses",
    payload_schema=AutoclosePayload.model_json_schema(),
)

# All routing events for easy access
ROUTING_EVENTS = [
    TIER1_ROUTE_EVENT,
    TIER2_ROUTE_EVENT,
    SPECIALIST_ROUTE_EVENT,
    MANAGEMENT_ESCALATION_EVENT,
    AUTOCLOSE_EVENT,
]


if __name__ == "__main__":
    """Print event definitions for review."""
    print("=" * 70)
    print("  Structured Event Definitions")
    print("=" * 70)
    print()
    
    print("Ticket Creation:")
    print("-" * 70)
    print(f"📧 {TICKET_CREATED_EVENT.event_name}")
    print(f"   Topic: {TICKET_CREATED_EVENT.topic}")
    print(f"   Description: {TICKET_CREATED_EVENT.description}")
    
    print("\n" + "=" * 70)
    print("Routing Events:")
    print("-" * 70)
    for event in ROUTING_EVENTS:
        print(f"\n📧 {event.event_name}")
        print(f"   Topic: {event.topic}")
        print(f"   Description: {event.description}")
    
    print("\n" + "=" * 70)
    print(f"Total events defined: {1 + len(ROUTING_EVENTS)}")
    print("=" * 70)
