#!/usr/bin/env python3
"""
Hello World Worker Agent

The simplest possible Soorma agent - demonstrates the Worker pattern.
A Worker listens for events and responds to them.
"""

from soorma import Worker


# Create a Worker instance
worker = Worker(
    name="hello-worker",
    description="A simple greeting agent",
    capabilities=["greeting"],
    events_consumed=["greeting.requested"],
    events_produced=["greeting.completed"],
)


@worker.on_event("greeting.requested")
async def handle_greeting(event, context):
    """
    Handle greeting requests.
    
    Args:
        event: Event dictionary containing event data
        context: PlatformContext with access to registry, memory, and bus
    
    Returns:
        The handler doesn't need to return anything - it publishes events instead
    """
    print(f"\n📨 Received greeting request")
    
    # Extract data from the event
    data = event.get("data", {})
    name = data.get("name", "World")
    
    print(f"   Name: {name}")
    
    # Create the greeting
    greeting = f"Hello, {name}! 👋"
    print(f"   Generated: {greeting}\n")
    
    # Publish the response event
    await context.bus.publish(
        event_type="greeting.completed",
        topic="action-results",
        data={
            "greeting": greeting,
            "name": name,
        }
    )
    print("✅ Response published")


@worker.on_startup
async def startup():
    """Called when the worker starts."""
    print("\n" + "=" * 50)
    print("🚀 Hello Worker started!")
    print("=" * 50)
    print(f"   Name: {worker.name}")
    print(f"   Capabilities: {worker.capabilities}")
    print("   Listening for 'greeting.requested' events...")
    print("   Press Ctrl+C to stop\n")


@worker.on_shutdown
async def shutdown():
    """Called when the worker stops."""
    print("\n👋 Hello Worker shutting down\n")


if __name__ == "__main__":
    worker.run()
