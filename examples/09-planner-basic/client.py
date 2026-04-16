#!/usr/bin/env python3
"""
Client - Send Research Goals

Demonstrates sending goals to the planner and receiving results.
Follows the standard EventClient pattern used in other examples.
"""

import asyncio
import sys
from pathlib import Path
from uuid import uuid4

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from soorma import EventClient
from soorma_common.events import EventEnvelope, EventTopic

from examples.shared.auth import build_example_token_provider

EXAMPLE_NAME = "09-planner-basic"


async def send_research_goal(topic: str):
    """
    Send a research goal and wait for the result.
    
    Args:
        topic: Research topic (e.g., "AI agents", "quantum computing")
    """
    token_provider = build_example_token_provider(EXAMPLE_NAME, __file__)
    await token_provider.get_token()
    tenant_id = await token_provider.get_platform_tenant_id()
    user_id = await token_provider.get_bootstrap_admin_principal_id()
    # Create EventClient
    client = EventClient(
        agent_id="research-client",
        source="research-client",
        auth_token_provider=token_provider,
    )
    
    print("=" * 60)
    print("  Planner Basic - Research Client")
    print("=" * 60)
    print()
    
    # Track when we receive a response
    response_received = asyncio.Event()
    response_data = {}
    
    # Generate correlation_id before defining handler
    correlation_id = str(uuid4())
    
    # Define response handler
    @client.on_event("research.result", topic=EventTopic.ACTION_RESULTS)
    async def on_response(event: EventEnvelope):
        """Handle the research result from the planner."""
        print(f"\n📨 Received response event: {event.type}")
        print(f"   Correlation: {event.correlation_id}")
        print(f"   Expected: {correlation_id}")
        
        # Only process if correlation matches our request
        if event.correlation_id != correlation_id:
            print("   ⚠️  Correlation mismatch, ignoring")
            return
        
        print("   ✅ Correlation matched!")
        data = event.data or {}
        response_data.update(data)
        response_received.set()
    
    # Connect to the platform
    await client.connect(topics=[EventTopic.ACTION_RESULTS])
    
    print(f"🎯 Sending research goal: '{topic}'")
    print(f"   Correlation ID: {correlation_id}")
    print()
    
    # Publish the goal event
    
    await client.publish(
        event_type="research.goal",
        topic=EventTopic.ACTION_REQUESTS,
        data={"topic": topic},
        correlation_id=correlation_id,
        response_event="research.result",
        response_topic="action-results",
        tenant_id=tenant_id,
        user_id=user_id,
    )
    
    print("📤 Goal sent!")
    print("📊 Waiting for planner to complete research...")
    print("-" * 60)
    
    try:
        # Wait for the response (with timeout)
        await asyncio.wait_for(response_received.wait(), timeout=30.0)
        
        # Display the response
        # PlanContext.finalize() wraps result in {"plan_id": "...", "result": {...}}
        result = response_data.get("result", {})
        summary = result.get("summary", "No summary")
        papers_found = result.get("papers_found", 0)
        papers = result.get("papers", [])
        
        print()
        print("🎉 Research Complete!")
        print()
        print(f"Summary: {summary}")
        print(f"Papers found: {papers_found}")
        
        if papers:
            print()
            print("Papers:")
            for i, paper in enumerate(papers, 1):
                print(f"  {i}. {paper}")
        
        print()
        
    except asyncio.TimeoutError:
        print()
        print("⚠️  Timeout waiting for response")
        print("   Make sure the Planner and Worker agents are running!")
        print("   Run: ./start.sh")
        print()
    finally:
        await client.disconnect()
    
    print("=" * 60)


async def main():
    """Main entry point."""
    # Get topic from command line argument, default to "AI agents"
    topic = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "AI agents"
    await send_research_goal(topic)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Interrupted\n")
