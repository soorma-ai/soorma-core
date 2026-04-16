#!/usr/bin/env python3
"""
Event Subscriber

Demonstrates how to subscribe to and handle multiple event types.
This simulates various services reacting to events in an order workflow.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from soorma import Worker
from soorma.context import PlatformContext
from soorma_common import EventDefinition
from soorma_common.events import EventEnvelope, EventTopic

from examples.shared.auth import build_example_token_provider


EXAMPLE_NAME = "02-events-simple"
EXAMPLE_TOKEN_PROVIDER = build_example_token_provider(EXAMPLE_NAME, __file__)


# Define event types
ORDER_PLACED_EVENT = EventDefinition(
    event_name="order.placed",
    topic=EventTopic.BUSINESS_FACTS,
    description="Order has been placed"
)

INVENTORY_RESERVED_EVENT = EventDefinition(
    event_name="inventory.reserved",
    topic=EventTopic.BUSINESS_FACTS,
    description="Inventory has been reserved for the order"
)

PAYMENT_COMPLETED_EVENT = EventDefinition(
    event_name="payment.completed",
    topic=EventTopic.BUSINESS_FACTS,
    description="Payment has been processed"
)

ORDER_COMPLETED_EVENT = EventDefinition(
    event_name="order.completed",
    topic=EventTopic.BUSINESS_FACTS,
    description="Order processing completed"
)


# Create a Worker that handles multiple event types
worker = Worker(
    name="order-processor",
    description="Processes order workflow events in a chain",
    capabilities=["order-processing", "inventory", "payment"],
    events_consumed=[
        ORDER_PLACED_EVENT,
        INVENTORY_RESERVED_EVENT,
        PAYMENT_COMPLETED_EVENT,
        ORDER_COMPLETED_EVENT,
    ],
    events_produced=[
        INVENTORY_RESERVED_EVENT,
        PAYMENT_COMPLETED_EVENT,
        ORDER_COMPLETED_EVENT,
    ],
    auth_token_provider=EXAMPLE_TOKEN_PROVIDER,
)


@worker.on_event("order.placed", topic=EventTopic.BUSINESS_FACTS)
async def handle_order_placed(event: EventEnvelope, context: PlatformContext):
    """
    Handle when a new order is placed.
    This starts the workflow by reserving inventory.
    """
    data = event.data or {}
    order_id = data.get("order_id")
    items = data.get("items", [])
    total = data.get("total")
    
    # Extract metadata for propagation
    correlation_id = event.correlation_id
    trace_id = event.trace_id or event.id  # Use event ID as trace root if no trace_id
    parent_event_id = event.id
    
    print("\n" + "=" * 60)
    print("📦 Order placed!")
    print("=" * 60)
    print(f"   Order ID: {order_id}")
    print(f"   Items: {', '.join(items)}")
    print(f"   Total: ${total:.2f}")
    print(f"   Trace ID: {trace_id[:8]}...")
    print()
    
    # Simulate inventory reservation (in real system, another service would do this)
    print("   Reserving inventory...")
    print("   ✓ Items reserved!")
    print()
    
    # Announce fact: inventory is now reserved (propagate metadata for traceability)
    print("   → Announcing inventory.reserved event...")
    await context.bus.announce(
        event_type="inventory.reserved",
        data={
            "order_id": order_id,
            "items": items,
        },
        correlation_id=correlation_id,
        trace_id=trace_id,
        parent_event_id=parent_event_id,
    )
    print("   ✓ Event announced\n")


@worker.on_event("inventory.reserved", topic=EventTopic.BUSINESS_FACTS)
async def handle_inventory_reserved(event: EventEnvelope, context: PlatformContext):
    """
    Handle when inventory has been reserved.
    This triggers payment processing.
    """
    data = event.data or {}
    order_id = data.get("order_id")
    items = data.get("items", [])
    
    # Extract metadata for propagation
    correlation_id = event.correlation_id
    trace_id = event.trace_id
    parent_event_id = event.id
    
    print("\n" + "=" * 60)
    print("🔒 Inventory reserved!")
    print("=" * 60)
    print(f"   Order ID: {order_id}")
    print(f"   Items: {', '.join(items)}")
    print(f"   Trace ID: {trace_id[:8]}...")
    print()
    
    # Simulate payment processing (in real system, another service would do this)
    print("   Processing payment...")
    print("   ✓ Payment processed!")
    print()
    
    # Announce fact: payment is now completed (propagate metadata)
    print("   → Announcing payment.completed event...")
    await context.bus.announce(
        event_type="payment.completed",
        data={
            "order_id": order_id,
            "status": "completed",
        },
        correlation_id=correlation_id,
        trace_id=trace_id,
        parent_event_id=parent_event_id,
    )
    print("   ✓ Event announced\n")


@worker.on_event("payment.completed", topic=EventTopic.BUSINESS_FACTS)
async def handle_payment_completed(event: EventEnvelope, context: PlatformContext):
    """
    Handle when payment has been completed.
    This finalizes the order.
    """
    data = event.data or {}
    order_id = data.get("order_id")
    
    # Extract metadata for propagation
    correlation_id = event.correlation_id
    trace_id = event.trace_id
    parent_event_id = event.id
    
    print("\n" + "=" * 60)
    print("💳 Payment completed!")
    print("=" * 60)
    print(f"   Order ID: {order_id}")
    print(f"   Trace ID: {trace_id[:8]}...")
    print()
    
    # Finalize order (in real system, trigger fulfillment/shipping)
    print("   Finalizing order...")
    print("   ✓ Order finalized!")
    print()
    
    # Announce fact: order is now completed (propagate metadata)
    print("   → Announcing order.completed event...")
    await context.bus.announce(
        event_type="order.completed",
        data={
            "order_id": order_id,
            "status": "completed",
        },
        correlation_id=correlation_id,
        trace_id=trace_id,
        parent_event_id=parent_event_id,
    )
    print("   ✓ Event announced\n")


@worker.on_event("order.completed", topic=EventTopic.BUSINESS_FACTS)
async def handle_order_completed(event: EventEnvelope, context: PlatformContext):
    """
    Handle order completion.
    This is the final step in the workflow.
    """
    data = event.data or {}
    order_id = data.get("order_id")
    trace_id = event.trace_id
    
    print("\n" + "=" * 60)
    print("🎉 Order workflow completed!")
    print("=" * 60)
    print(f"   Order ID: {order_id}")
    print(f"   Trace ID: {trace_id[:8]}...")
    print("   All steps finished successfully!")
    print("   (Same trace_id propagated through entire chain)")
    print("=" * 60)
    print()


@worker.on_startup
async def startup():
    """Called when the worker starts."""
    print("\n" + "=" * 60)
    print("🚀 Order Processor Worker started!")
    print("=" * 60)
    print(f"   Name: {worker.name}")
    print(f"   Capabilities: {worker.capabilities}")
    print()
    print("   Listening for events (chain):")
    print("   • order.placed → inventory.reserved")
    print("   • inventory.reserved → payment.completed")
    print("   • payment.completed → order.completed")
    print("   • order.completed (end)")
    print()
    print("   Press Ctrl+C to stop")
    print("=" * 60)
    print()


@worker.on_shutdown
async def shutdown():
    """Called when the worker stops."""
    print("\n👋 Order Processor Worker shutting down\n")


if __name__ == "__main__":
    worker.run()
