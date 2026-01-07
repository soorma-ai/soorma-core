#!/usr/bin/env python3
"""
Event Subscriber

Demonstrates how to subscribe to and handle multiple event types.
This simulates various services reacting to events in an order workflow.
"""

from soorma import Worker


# Create a Worker that handles multiple event types
worker = Worker(
    name="order-processor",
    description="Processes order workflow events",
    capabilities=["order-processing", "inventory", "payment"],
    events_consumed=[
        "order.placed",
        "inventory.check",
        "inventory.reserve",
        "payment.authorize",
        "payment.process",
        "payment.completed",
        "order.completed",
    ],
    events_produced=[
        "inventory.reserve",
        "inventory.reserved",
        "payment.process",
        "payment.completed",
        "order.completed",
        "order.ship",
    ],
)


@worker.on_event("order.placed")
async def handle_order_placed(event, context):
    """
    Handle when a new order is placed.
    This starts the workflow by checking inventory.
    """
    data = event.get("data", {})
    order_id = data.get("order_id")
    items = data.get("items", [])
    total = data.get("total")
    
    print("\n" + "=" * 60)
    print("📦 Order placed!")
    print("=" * 60)
    print(f"   Order ID: {order_id}")
    print(f"   Items: {', '.join(items)}")
    print(f"   Total: ${total:.2f}")
    print()
    
    # Trigger next step: reserve inventory
    print("   → Publishing inventory.reserve event...")
    await context.bus.publish(
        event_type="inventory.reserve",
        topic="business-facts",
        data={
            "order_id": order_id,
            "items": items,
        },
    )
    print("   ✓ Event published\n")


@worker.on_event("inventory.check")
async def handle_inventory_check(event, context):
    """
    Handle inventory check requests.
    In a real system, this would query a database.
    """
    data = event.get("data", {})
    order_id = data.get("order_id")
    items = data.get("items", [])
    
    print("\n" + "=" * 60)
    print("📊 Inventory check requested")
    print("=" * 60)
    print(f"   Order ID: {order_id}")
    print(f"   Checking availability for: {', '.join(items)}")
    print()
    
    # Simulate inventory check (always succeeds in this example)
    print("   ✓ All items available!")
    print()
    
    # Publish inventory reserved event
    print("   → Publishing inventory.reserved event...")
    await context.bus.publish(
        event_type="inventory.reserved",
        topic="business-facts",
        data={
            "order_id": order_id,
            "items": items,
            "reserved": True,
        },
    )
    print("   ✓ Event published\n")


@worker.on_event("inventory.reserve")
async def handle_inventory_reserve(event, context):
    """
    Handle inventory reservation.
    This would actually reserve items in a real system.
    """
    data = event.get("data", {})
    order_id = data.get("order_id")
    items = data.get("items", [])
    
    print("\n" + "=" * 60)
    print("🔒 Reserving inventory")
    print("=" * 60)
    print(f"   Order ID: {order_id}")
    print(f"   Reserving: {', '.join(items)}")
    print()
    
    # Simulate reservation
    print("   ✓ Items reserved!")
    print()
    
    # Trigger next step: process payment
    print("   → Publishing payment.process event...")
    await context.bus.publish(
        event_type="payment.process",
        topic="business-facts",
        data={
            "order_id": order_id,
        },
    )
    print("   ✓ Event published\n")


@worker.on_event("payment.authorize")
async def handle_payment_authorize(event, context):
    """
    Handle payment authorization requests.
    In a real system, this would call a payment gateway.
    """
    data = event.get("data", {})
    order_id = data.get("order_id")
    amount = data.get("amount")
    customer = data.get("customer")
    
    print("\n" + "=" * 60)
    print("💳 Payment authorization requested")
    print("=" * 60)
    print(f"   Order ID: {order_id}")
    print(f"   Customer: {customer}")
    print(f"   Amount: ${amount:.2f}")
    print()
    
    # Simulate payment authorization (always succeeds)
    print("   ✓ Payment authorized!")
    print()
    
    # Publish payment completed event
    print("   → Publishing payment.completed event...")
    await context.bus.publish(
        event_type="payment.completed",
        topic="business-facts",
        data={
            "order_id": order_id,
            "amount": amount,
            "status": "completed",
        },
    )
    print("   ✓ Event published\n")


@worker.on_event("payment.process")
async def handle_payment_process(event, context):
    """
    Handle payment processing.
    This would actually charge the customer in a real system.
    """
    data = event.get("data", {})
    order_id = data.get("order_id")
    
    print("\n" + "=" * 60)
    print("💰 Processing payment")
    print("=" * 60)
    print(f"   Order ID: {order_id}")
    print()
    
    # Simulate payment processing
    print("   ✓ Payment processed!")
    print()
    
    # Complete the workflow
    print("   → Publishing order.completed event...")
    await context.bus.publish(
        event_type="order.completed",
        topic="business-facts",
        data={
            "order_id": order_id,
            "status": "completed",
        },
    )
    print("   ✓ Event published\n")


@worker.on_event("payment.completed")
async def handle_payment_completed(event, context):
    """
    Handle payment completion.
    This triggers the shipping process.
    """
    data = event.get("data", {})
    order_id = data.get("order_id")
    
    print("\n" + "=" * 60)
    print("🚚 Payment completed - initiating shipping")
    print("=" * 60)
    print(f"   Order ID: {order_id}")
    print()
    
    # Trigger shipping
    print("   → Publishing order.ship event...")
    await context.bus.publish(
        event_type="order.ship",
        topic="business-facts",
        data={
            "order_id": order_id,
        },
    )
    print("   ✓ Event published\n")


@worker.on_event("order.completed")
async def handle_order_completed(event, context):
    """
    Handle order completion.
    This is the final step in the workflow.
    """
    data = event.get("data", {})
    order_id = data.get("order_id")
    
    print("\n" + "=" * 60)
    print("🎉 Order workflow completed!")
    print("=" * 60)
    print(f"   Order ID: {order_id}")
    print("   All steps finished successfully!")
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
    print("   Listening for events:")
    print("   • order.placed")
    print("   • inventory.check")
    print("   • inventory.reserve")
    print("   • payment.authorize")
    print("   • payment.process")
    print("   • payment.completed")
    print("   • order.completed")
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
