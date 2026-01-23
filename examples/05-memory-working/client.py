"""
Client for submitting goals to the workflow system.

Usage:
    python client.py "Write a blog post about Docker"
    python client.py "Create a tutorial on Python asyncio"
"""

import asyncio
import sys
from soorma import EventClient


async def submit_goal(goal: str):
    """Submit a goal and wait for workflow completion."""
    client = EventClient(agent_id="workflow-client", source="workflow-client")
    
    # Event to signal workflow completion
    workflow_completed = asyncio.Event()
    result_data = {}
    
    @client.on_event("workflow.completed", topic="action-results")
    async def on_completion(event):
        """Handle workflow completion."""
        nonlocal result_data
        result_data = event.get("data", {})
        workflow_completed.set()
    
    # Connect to the platform
    await client.connect(topics=["action-results"])
    
    print(f"🎯 Submitting goal: {goal}\n")
    
    try:
        # Publish goal with tenant_id and user_id at envelope level (not in data)
        # In production, these would come from authentication/request context
        await client.publish(
            event_type="goal.received",
            topic="action-requests",
            data={"goal": goal},
            tenant_id="00000000-0000-0000-0000-000000000000",
            user_id="00000000-0000-0000-0000-000000000001",
        )
        
        print("   Waiting for workflow completion...")
        
        # Wait for completion with timeout
        try:
            await asyncio.wait_for(workflow_completed.wait(), timeout=30.0)
        except asyncio.TimeoutError:
            print("\n⏱️  Timeout: Workflow took too long")
            print("\nTroubleshooting:")
            print("1. Are all agents running?")
            print("   python planner.py")
            print("   python worker.py")
            print("   python coordinator.py")
            return
        
        # Display results
        plan_id = result_data.get("plan_id")
        results = result_data.get("results", {})
        history = result_data.get("history", [])
        
        print("\n✅ Workflow Completed!")
        print(f"   Plan ID: {plan_id}")
        print(f"\n📊 Results:")
        for task, result in results.items():
            print(f"\n   {task}:")
            print(f"      {result}")
        
        print(f"\n📝 Action History:")
        for i, action in enumerate(history, 1):
            print(f"   {i}. {action}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python client.py \"Your goal here\"")
        print("\nExamples:")
        print("  python client.py \"Write a blog post about Docker\"")
        print("  python client.py \"Create a tutorial on Python asyncio\"")
        print("  python client.py \"Research and summarize Kubernetes basics\"")
        sys.exit(1)
    
    goal = " ".join(sys.argv[1:])
    asyncio.run(submit_goal(goal))
