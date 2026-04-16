#!/usr/bin/env python3
"""
Event Publisher

Demonstrates how to publish events to the Soorma platform.
This simulates an order service publishing events in an order workflow.
"""

import asyncio
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from soorma import EventClient
from soorma_common.events import EventTopic

from examples.shared.auth import build_example_token_provider

EXAMPLE_NAME = "02-events-simple"


async def publish_order_workflow():
    """Publish the initial event that triggers the order workflow chain."""
    token_provider = build_example_token_provider(EXAMPLE_NAME, __file__)
    await token_provider.get_token()
    tenant_id = await token_provider.get_platform_tenant_id()
    user_id = await token_provider.get_bootstrap_admin_principal_id()
    
    # Create EventClient for publishing
    client = EventClient(
        agent_id="order-service",
        source="order-service",
        auth_token_provider=token_provider,
    )
    
    print("=" * 60)
    print("  Event Publisher - Order Workflow")
    print("=" * 60)
    print()
    
    # Connect to the platform (empty topics list since we only publish)
    await client.connect(topics=[])
    
    # Publish the initial event that starts the chain
    print("📦 Publishing order.placed event...")
    print("   (This will trigger the event chain in the subscriber)")
    print()
    await client.publish(
        event_type="order.placed",
        topic=EventTopic.BUSINESS_FACTS,
        data={
            "order_id": "ORD-001",
            "customer": "Alice",
            "items": ["laptop", "mouse"],
            "total": 1500.00,
        },
        tenant_id=tenant_id,
        user_id=user_id,
    )
    print("   ✓ Published to 'business-facts' topic\n")
    
    print("=" * 60)
    print("✅ Event published!")
    print("=" * 60)
    print()
    print("Watch the subscriber terminal to see the event chain:")
    print("  order.placed → inventory.reserved → payment.completed → order.completed")
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
