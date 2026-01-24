#!/usr/bin/env python3
"""
Hello World Worker Agent

The simplest possible Soorma agent - demonstrates the Worker pattern.
A Worker listens for events and responds to them.
"""

from typing import Any, Dict
from soorma import Worker
from soorma.context import PlatformContext


# Create a Worker instance
worker = Worker(
    name="hello-worker",
    description="A simple greeting agent",
    capabilities=["greeting"],
    events_consumed=["greeting.requested"],
    events_produced=["greeting.completed"],
)


@worker.on_event("greeting.requested", topic="action-requests")
async def handle_greeting(event: Dict[str, Any], context: PlatformContext):
    """Handle greeting requests and respond with a friendly message."""
    print(f"\n📨 Received greeting request")
    
    # Extract data from the event
    data = event.get("data", {})
    name = data.get("name", "World")
    
    print(f"   Name: {name}")
    
    # Create the greeting
    greeting = f"Hello, {name}! 👋"
    print(f"   Generated: {greeting}\n")
    
    # Send response using respond() convenience method
    await context.bus.respond(
        event_type="greeting.completed",
        data={
            "greeting": greeting,
            "name": name,
        },
        correlation_id=event.get("correlation_id"),
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
