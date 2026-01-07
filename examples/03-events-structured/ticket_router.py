#!/usr/bin/env python3
"""
Ticket Router Agent

Demonstrates an agent with domain-specific logic using LLM utilities.
This agent routes support tickets to appropriate teams using LLM reasoning.

AGENT-SPECIFIC CODE:
This file contains only the domain logic specific to ticket routing:
- Event definitions (what events this agent handles)
- LLM prompt template (domain-specific instructions)
- Event handler with business logic
- Demo handlers showing routing results

The generic LLM utilities are in llm_utils.py (future SDK).
"""

import os
from soorma import Worker
from events import (
    TICKET_CREATED_EVENT,
    TIER1_ROUTE_EVENT,
    TIER2_ROUTE_EVENT,
    SPECIALIST_ROUTE_EVENT,
    MANAGEMENT_ESCALATION_EVENT,
    AUTOCLOSE_EVENT,
)
from llm_utils import (
    discover_events,
    select_event_with_llm,
    validate_and_publish,
)


# Create worker for ticket routing
# SDK will automatically register these event definitions
worker = Worker(
    name="ticket-router",
    description="Routes support tickets using LLM-based event selection",
    capabilities=["ticket-routing", "llm-decision-making"],
    events_consumed=[TICKET_CREATED_EVENT],
    events_produced=[
        TIER1_ROUTE_EVENT,
        TIER2_ROUTE_EVENT,
        SPECIALIST_ROUTE_EVENT,
        MANAGEMENT_ESCALATION_EVENT,
        AUTOCLOSE_EVENT,
    ],
)


# Domain-specific LLM prompt template for ticket routing
TICKET_ROUTING_PROMPT = """You are a support ticket routing assistant. Analyze the ticket and select the most appropriate routing action.

TICKET INFORMATION:
{context_data}

AVAILABLE ROUTING OPTIONS:
{events}

INSTRUCTIONS:
1. Analyze the ticket to understand the issue type and complexity
2. Consider which team is best equipped to handle this:
   - Tier 1: Simple issues (password resets, basic questions)
   - Tier 2: Technical issues (API errors, integrations)
   - Specialist: Complex domain-specific problems
   - Management: Urgent escalations, VIP customers
   - Autoclose: Spam, duplicates, already resolved
3. Select the most appropriate routing event
4. Provide a brief explanation of your decision

Return your decision as JSON:
{{
    "event_name": "the exact event name to use",
    "reason": "brief explanation of why this is the best choice",
    "data": {{
        "ticket_id": "from ticket data",
        "category": "inferred category",
        "priority": "from ticket or inferred"
    }}
}}
"""


@worker.on_event("ticket.created")
async def route_ticket(event, context):
    """
    Main event handler: Routes incoming tickets using LLM reasoning.
    
    This demonstrates the clean agent code when using LLM utilities:
    1. Discover available routing options
    2. Let LLM select best option using domain-specific prompt
    3. Validate and publish the decision
    """
    data = event.get("data", {})
    ticket_id = data.get("ticket_id", "Unknown")
    description = data.get("description", "No description")
    
    print("\n" + "=" * 70)
    print("📧 New ticket received")
    print("=" * 70)
    print(f"   ID: {ticket_id}")
    print(f"   Customer: {data.get('customer', 'Unknown')}")
    print(f"   Issue: {description}")
    print(f"   Priority: {data.get('priority', 'normal')}")
    print()
    
    # Step 1: Discover available routing events (generic utility)
    print("🔍 Discovering routing options from Registry...")
    try:
        events = await discover_events(context, topic="action-requests")
        print(f"   Found {len(events)} routing options\n")
    except Exception as e:
        print(f"   ✗ Failed to discover events: {e}")
        return
    
    # Step 2: Use LLM to select the best event (generic utility + domain prompt)
    print("🤖 Analyzing ticket with LLM...")
    try:
        decision = await select_event_with_llm(
            prompt_template=TICKET_ROUTING_PROMPT,  # Agent-specific
            context_data=data,                      # Current ticket
            events=events,                          # Discovered options
            model=os.getenv("LLM_MODEL")            # Optional override
        )
        
        print(f"   Selected: {decision['event_name']}")
        print(f"   Reason: {decision['reason']}")
        print()
        
    except Exception as e:
        print(f"   ✗ LLM selection failed: {e}")
        print("   Make sure OPENAI_API_KEY is set in your environment")
        return
    
    # Step 3: Validate and publish (generic utility)
    print(f"📤 Publishing: {decision['event_name']}")
    success = await validate_and_publish(
        decision=decision,
        events=events,
        topic="action-requests",
        context=context
    )
    
    if success:
        print("=" * 70)
        print()


# Demo handlers to show routing results
@worker.on_event("ticket.route.tier1")
async def handle_tier1_routing(event, context):
    """Handler to demonstrate the event was received."""
    data = event.get("data", {})
    print(f"\n🎯 Tier 1 received ticket: {data.get('ticket_id')}")
    print("   Assigning to general support queue...\n")


@worker.on_event("ticket.route.tier2")
async def handle_tier2_routing(event, context):
    """Handler to demonstrate the event was received."""
    data = event.get("data", {})
    print(f"\n🎯 Tier 2 received ticket: {data.get('ticket_id')}")
    print("   Assigning to technical specialist...\n")


@worker.on_event("ticket.route.specialist")
async def handle_specialist_routing(event, context):
    """Handler to demonstrate the event was received."""
    data = event.get("data", {})
    print(f"\n🎯 Specialist received ticket: {data.get('ticket_id')}")
    print("   Assigning to domain expert...\n")


@worker.on_event("ticket.escalate.management")
async def handle_management_escalation(event, context):
    """Handler to demonstrate the event was received."""
    data = event.get("data", {})
    print(f"\n🚨 Management escalation for ticket: {data.get('ticket_id')}")
    print("   Notifying management team...\n")


@worker.on_event("ticket.autoclose")
async def handle_autoclose(event, context):
    """Handler to demonstrate the event was received."""
    data = event.get("data", {})
    print(f"\n✅ Auto-closing ticket: {data.get('ticket_id')}")
    print(f"   Reason: {data.get('reason')}\n")


@worker.on_startup
async def startup():
    """Called when the worker starts."""
    print("\n" + "=" * 70)
    print("🚀 Ticket Router (LLM Event Selector) started!")
    print("=" * 70)
    print(f"   Name: {worker.name}")
    print(f"   Model: {os.getenv('LLM_MODEL', 'gpt-4o-mini')}")
    print()
    print("   Capabilities:")
    print("   • Discovers routing events from Registry")
    print("   • Uses LLM to select appropriate routing")
    print("   • Validates events before publishing")
    print()
    print("   Listening for: ticket.created events")
    print("   Press Ctrl+C to stop")
    print("=" * 70)
    print()


@worker.on_shutdown
async def shutdown():
    """Called when the worker stops."""
    print("\n👋 Ticket Router shutting down\n")


if __name__ == "__main__":
    worker.run()
