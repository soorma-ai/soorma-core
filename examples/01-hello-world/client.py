#!/usr/bin/env python3
"""
Hello World Client

Sends greeting requests to the Worker agent and receives responses.
This demonstrates how to interact with Soorma agents using the EventClient.
"""

import sys
import asyncio
from soorma import EventClient


async def send_greeting_request(name: str = "World"):
    """Send a greeting request and wait for the response."""
    
    # Create EventClient
    client = EventClient(
        agent_id="hello-client",
        source="hello-client",
    )
    
    print("=" * 50)
    print("  Soorma Hello World - Client")
    print("=" * 50)
    print()
    
    # Track when we receive a response
    response_received = asyncio.Event()
    response_data = {}
    
    # Define response handler
    @client.on_event("greeting.completed", topic="action-results")
    async def on_response(event):
        """Handle the greeting response from the worker."""
        data = event.get("data", {})
        response_data.update(data)
        response_received.set()
    
    # Connect to the platform
    await client.connect(topics=["action-results"])
    
    print(f"🎯 Sending greeting request for: {name}")
    
    # Publish the request event using respond pattern
    from uuid import uuid4
    correlation_id = str(uuid4())
    
    await client.publish(
        event_type="greeting.requested",
        topic="action-requests",
        data={"name": name},
        correlation_id=correlation_id,
        response_event="greeting.completed",
        response_topic="action-results",
    )
    
    print("📤 Request sent!")
    print("📊 Waiting for response...")
    print("-" * 50)
    
    try:
        # Wait for the response (with timeout)
        await asyncio.wait_for(response_received.wait(), timeout=10.0)
        
        # Display the response
        greeting = response_data.get("greeting", "No greeting received")
        print(f"\n🎉 Response: {greeting}\n")
        
    except asyncio.TimeoutError:
        print("\n⚠️  Timeout waiting for response")
        print("   Make sure the Worker agent is running!")
        print("   Run: python worker.py\n")
    finally:
        await client.disconnect()
    
    print("=" * 50)


async def main():
    """Main entry point."""
    # Get name from command line argument, default to "World"
    name = sys.argv[1] if len(sys.argv) > 1 else "World"
    await send_greeting_request(name)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Interrupted\n")
