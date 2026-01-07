#!/usr/bin/env python3
"""
Event Publisher

Demonstrates how to publish events to the Soorma platform.
This simulates an order service publishing events in an order workflow.
"""

import asyncio
from soorma import EventClient


async def publish_order_workflow():
    """Publish a sequence of events simulating an order workflow."""
    
    # Create EventClient for publishing
    client = EventClient(
        agent_id="order-service",
        source="order-service",
    )
    
    print("=" * 60)
    print("  Event Publisher - Order Workflow")
    print("=" * 60)
    print()
    
    # Connect to the platform (empty topics list since we only publish)
    await client.connect(topics=[])
    
    # Event 1: Order placed
    print("📦 Publishing order.placed event...")
    await client.publish(
        event_type="order.placed",
        topic="business-facts",
        data={
            "order_id": "ORD-001",
            "customer": "Alice",
            "items": ["laptop", "mouse"],
            "total": 1500.00,
        },
    )
    print("   ✓ Published to 'business-facts' topic\n")
    await asyncio.sleep(0.5)
    
    # Event 2: Inventory check
    print("📊 Publishing inventory.check event...")
    await client.publish(
        event_type="inventory.check",
        topic="business-facts",
        data={
            "order_id": "ORD-001",
            "items": ["laptop", "mouse"],
        },
    )
    print("   ✓ Published to 'business-facts' topic\n")
    await asyncio.sleep(0.5)
    
    # Event 3: Payment authorization
    print("💳 Publishing payment.authorize event...")
    await client.publish(
        event_type="payment.authorize",
        topic="business-facts",
        data={
            "order_id": "ORD-001",
            "amount": 1500.00,
            "customer": "Alice",
        },
    )
    print("   ✓ Published to 'business-facts' topic\n")
    
    print("=" * 60)
    print("✅ All events published!")
    print("=" * 60)
    print()
    print("Check the subscriber terminal to see the events being processed.")
    print()
    
    await client.disconnect()


async def main():
    """Main entry point."""
    await publish_order_workflow()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Interrupted\n")
