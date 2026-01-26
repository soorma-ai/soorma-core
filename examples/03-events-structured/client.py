#!/usr/bin/env python3
"""
Client - Create Support Tickets

Creates test support tickets to demonstrate LLM-based event selection.
Each ticket will be analyzed by the LLM to determine the best routing.
"""

import sys
import asyncio
from soorma import EventClient
from soorma_common.events import EventTopic


SAMPLE_TICKETS = [
    {
        "description": "I forgot my password and the reset link isn't working",
        "priority": "normal",
        "customer": "Alice",
        "expected_route": "tier1 (common issue)",
    },
    {
        "description": "Getting 500 internal server error when calling POST /api/v2/users",
        "priority": "high",
        "customer": "Bob",
        "expected_route": "tier2 (technical API issue)",
    },
    {
        "description": "Need to integrate custom SAML SSO provider with specific claims mapping",
        "priority": "high",
        "customer": "Charlie",
        "expected_route": "specialist (complex integration)",
    },
    {
        "description": "URGENT: Production database is down, all services failing",
        "priority": "critical",
        "customer": "Dana (Enterprise)",
        "expected_route": "management (critical business impact)",
    },
    {
        "description": "This is a duplicate of ticket #12345",
        "priority": "low",
        "customer": "Eve",
        "expected_route": "autoclose (duplicate)",
    },
]


async def create_ticket(description: str, priority: str = "normal", customer: str = "Test User"):
    """Create a support ticket and wait for routing."""
    
    # Create EventClient
    client = EventClient(
        agent_id="ticket-client",
        source="ticket-client",
    )
    
    # Generate ticket ID
    import time
    ticket_id = f"TICK-{int(time.time() * 1000) % 10000:04d}"
    
    print("=" * 70)
    print("  Creating Support Ticket")
    print("=" * 70)
    print(f"   ID: {ticket_id}")
    print(f"   Customer: {customer}")
    print(f"   Priority: {priority}")
    print(f"   Issue: {description}")
    print("=" * 70)
    print()
    
    # Connect to platform
    await client.connect(topics=[])
    
    # Publish ticket creation event (business fact)
    print("📤 Publishing ticket.created event...")
    await client.publish(
        event_type="ticket.created",
        topic=EventTopic.BUSINESS_FACTS,
        data={
            "ticket_id": ticket_id,
            "customer": customer,
            "description": description,
            "priority": priority,
        },
    )
    print("   ✓ Ticket created!")
    print()
    print("Check the llm_event_selector.py terminal to see the routing decision.")
    print()
    
    await client.disconnect()


async def create_sample_tickets():
    """Create all sample tickets with a delay between each."""
    print("\n" + "=" * 70)
    print("  Creating Sample Tickets for Testing")
    print("=" * 70)
    print()
    print(f"Will create {len(SAMPLE_TICKETS)} test tickets...")
    print()
    
    for i, ticket in enumerate(SAMPLE_TICKETS, 1):
        print(f"\n--- Ticket {i}/{len(SAMPLE_TICKETS)} ---")
        print(f"Expected route: {ticket['expected_route']}")
        print()
        
        await create_ticket(
            description=ticket["description"],
            priority=ticket["priority"],
            customer=ticket["customer"],
        )
        
        # Wait between tickets to see routing decisions clearly
        if i < len(SAMPLE_TICKETS):
            print("Waiting 3 seconds before next ticket...")
            await asyncio.sleep(3)
    
    print("\n" + "=" * 70)
    print("✅ All sample tickets created!")
    print("=" * 70)
    print()


async def main():
    """Main entry point."""
    
    # Check if custom description was provided
    if len(sys.argv) > 1:
        # Create single ticket with custom description
        description = " ".join(sys.argv[1:])
        await create_ticket(
            description=description,
            priority="normal",
            customer="CLI User",
        )
    else:
        # Show usage and create sample tickets
        print()
        print("Usage:")
        print("  python client.py \"your issue description\"")
        print()
        print("  Or run without arguments to create sample tickets:")
        print("  python client.py")
        print()
        
        response = input("Create sample tickets? [y/N]: ")
        if response.lower() == 'y':
            await create_sample_tickets()
        else:
            print("\nExample:")
            print('  python client.py "My API key is not working"')
            print()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Interrupted\n")
