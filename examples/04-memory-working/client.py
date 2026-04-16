"""
Client for triggering the demo workflow.

This example demonstrates WorkflowState mechanics with a fixed workflow.
For dynamic, goal-driven task generation, see example 08-planner-worker-basic (coming soon).

Usage:
    python client.py
"""

import asyncio
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from soorma import EventClient
from soorma_common.events import EventEnvelope, EventTopic

from examples.shared.auth import build_example_token_provider


EXAMPLE_NAME = "04-memory-working"


async def start_workflow():
    """Start the demo workflow."""
    token_provider = build_example_token_provider(EXAMPLE_NAME, __file__)
    await token_provider.get_token()
    tenant_id = await token_provider.get_platform_tenant_id()
    user_id = await token_provider.get_bootstrap_admin_principal_id()
    client = EventClient(
        agent_id="workflow-client",
        source="workflow-client",
        auth_token_provider=token_provider,
    )
    
    # Event to signal workflow completion
    workflow_completed = asyncio.Event()
    result_data = {}
    
    @client.on_event("workflow.completed", topic=EventTopic.ACTION_RESULTS)
    async def on_completion(event: EventEnvelope):
        """Handle workflow completion."""
        nonlocal result_data
        result_data = event.data or {}
        workflow_completed.set()
    
    # Connect to the platform
    await client.connect(topics=[EventTopic.ACTION_RESULTS])
    
    print("🎯 Starting demo workflow...\n")
    print("   This demonstrates a fixed 3-task workflow:")
    print("   research → draft → review\n")
    
    try:
        # Trigger workflow with tenant_id and user_id at envelope level (not in data)
        # In production, these would come from authentication/request context
        await client.publish(
            event_type="workflow.start",
            response_event="workflow.completed",
            topic=EventTopic.ACTION_REQUESTS,
            data={"workflow_name": "blog-post-demo"},
            tenant_id=tenant_id,
            user_id=user_id,
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
    asyncio.run(start_workflow())
