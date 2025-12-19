#!/usr/bin/env python3
"""
Hello World Client

Submits goals to the Soorma platform using the EventClient.
This simulates a client application interacting with the DisCo Trinity.
"""

import sys
import asyncio
from soorma import EventClient


async def submit_goal(name: str = "World"):
    """Submit a greeting goal to the platform."""
    
    # Create EventClient for publishing and subscribing
    client = EventClient(
        agent_id="hello-client",
        source="hello-client",
    )
    
    print("=" * 50)
    print("  Soorma Hello World - Client")
    print("=" * 50)
    print()
    
    goal_data = {
        "name": name,
        "description": f"Say hello to {name}",
    }
    
    print(f"🎯 Submitting goal: Say hello to {name}")
    print()
    
    # Track completion
    completed = asyncio.Event()
    result_data = {}
    
    @client.on_event("action.result")
    async def on_result(event):
        data = event.get("data", {})
        # Check for greeting in result (nested or direct)
        result = data.get("result", data)
        if "greeting" in result or data.get("status") == "completed":
            result_data.update(data)
            completed.set()
    
    # Connect and subscribe to results
    await client.connect(topics=["action-results"])
    
    # Publish the goal to business-facts topic (where Planner subscribes)
    # The Planner uses @on_goal("greeting.goal") which subscribes to business-facts
    await client.publish(
        event_type="greeting.goal",
        topic="business-facts",  # Goals go to business-facts topic
        data=goal_data,
    )
    print("📤 Goal submitted!")
    print()
    print("📊 Waiting for result...")
    print("-" * 50)
    
    try:
        # Wait for task completion
        await asyncio.wait_for(completed.wait(), timeout=30.0)
        
        # The result is nested: result_data['result']['greeting']
        result = result_data.get("result", result_data)
        greeting = result.get("greeting", result_data.get("greeting", "No greeting received"))
        print(f"\n🎉 Result: {greeting}")
        
    except asyncio.TimeoutError:
        print("\n⚠️  Timeout waiting for result")
        print("   Make sure the Planner and Worker agents are running!")
    finally:
        await client.disconnect()
    
    print("\n" + "=" * 50)


async def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "World"
    await submit_goal(name)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Interrupted")
