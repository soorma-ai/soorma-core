#!/usr/bin/env python3
"""
Hello World Worker Agent

The simplest possible Soorma agent - demonstrates the Worker pattern.
A Worker listens for events and responds to them.
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


EXAMPLE_NAME = "01-hello-world"
EXAMPLE_TOKEN_PROVIDER = build_example_token_provider(EXAMPLE_NAME, __file__)


# Define event types
GREETING_REQUESTED_EVENT = EventDefinition(
    event_name="greeting.requested",
    topic=EventTopic.ACTION_REQUESTS,
    description="Request to generate a greeting"
)

GREETING_COMPLETED_EVENT = EventDefinition(
    event_name="greeting.completed",
    topic=EventTopic.ACTION_RESULTS,
    description="Greeting generation completed"
)


# Create a Worker instance
worker = Worker(
    name="hello-worker",
    description="A simple greeting agent",
    capabilities=["greeting"],
    events_consumed=[GREETING_REQUESTED_EVENT],
    events_produced=[GREETING_COMPLETED_EVENT],
    auth_token_provider=EXAMPLE_TOKEN_PROVIDER,
)


@worker.on_event("greeting.requested", topic=EventTopic.ACTION_REQUESTS)
async def handle_greeting(event: EventEnvelope, context: PlatformContext):
    """Handle greeting requests and respond with a friendly message."""
    print(f"\n📨 Received greeting request")
    
    # Extract data from the event - EventEnvelope.data is typed as Optional[Dict[str, Any]]
    data = event.data or {}
    name = data.get("name", "World")
    
    print(f"   Name: {name}")
    
    # Create the greeting
    greeting = f"Hello, {name}! 👋"
    print(f"   Generated: {greeting}\n")
    
    # Extract response event from request (caller specifies expected response)
    response_event_type = event.response_event or "greeting.completed"
    
    # Send response using respond() convenience method
    await context.bus.respond(
        event_type=response_event_type,
        data={
            "greeting": greeting,
            "name": name,
        },
        correlation_id=event.correlation_id,
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
