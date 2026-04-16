"""
Manual working memory state management (without WorkflowState helper).

This demonstrates the raw Memory API. Compare with planner.py to see
how WorkflowState simplifies the code.
"""

import asyncio
import sys
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from soorma.memory.client import MemoryServiceClient

from examples.shared.auth import build_example_token_provider


EXAMPLE_NAME = "04-memory-working"


async def demonstrate_raw_memory_api():
    """Show raw Memory API operations for working memory."""
    token_provider = build_example_token_provider(EXAMPLE_NAME, __file__)
    await token_provider.get_token()
    tenant_id = await token_provider.get_platform_tenant_id()
    user_id = await token_provider.get_bootstrap_admin_principal_id()
    
    # Create Memory client directly (not through PlatformContext)
    memory = MemoryServiceClient(auth_token_provider=token_provider)
    plan_id = str(uuid.uuid4())
    
    print(f"📋 Plan ID: {plan_id}\n")
    print("Demonstrating manual working memory operations...")
    print("=" * 60)
    
    # Store goal
    print("\n1. Storing goal...")
    await memory.set_plan_state(
        plan_id=plan_id,
        key="goal",
        value={"text": "Write a blog post about Docker"},
        service_tenant_id=tenant_id,
        service_user_id=user_id
    )
    print("   ✓ Stored goal")
    
    # Store tasks
    print("\n2. Storing task list...")
    await memory.set_plan_state(
        plan_id=plan_id,
        key="tasks",
        value={"list": ["research", "draft", "review"]},
        service_tenant_id=tenant_id,
        service_user_id=user_id
    )
    print("   ✓ Stored tasks")
    
    # Store progress
    print("\n3. Storing progress...")
    await memory.set_plan_state(
        plan_id=plan_id,
        key="progress",
        value={"current_task": "research", "completed": []},
        service_tenant_id=tenant_id,
        service_user_id=user_id
    )
    print("   ✓ Stored progress")
    
    # Retrieve state
    print("\n4. Retrieving state...")
    goal_response = await memory.get_plan_state(plan_id, "goal", tenant_id, user_id)
    tasks_response = await memory.get_plan_state(plan_id, "tasks", tenant_id, user_id)
    progress_response = await memory.get_plan_state(plan_id, "progress", tenant_id, user_id)
    
    print(f"   Goal: {goal_response.value['text']}")
    print(f"   Tasks: {tasks_response.value['list']}")
    print(f"   Progress: {progress_response.value['current_task']}")
    
    # Update progress
    print("\n5. Updating progress...")
    progress_data = progress_response.value
    progress_data["completed"].append("research")
    progress_data["current_task"] = "draft"
    
    await memory.set_plan_state(
        plan_id=plan_id,
        key="progress",
        value=progress_data,
        service_tenant_id=tenant_id,
        service_user_id=user_id
    )
    print("   ✓ Updated progress")
    
    # Verify update
    updated_response = await memory.get_plan_state(plan_id, "progress", tenant_id, user_id)
    print(f"   New progress: {updated_response.value}")
    
    # Delete single key
    print("\n6. Deleting a single key...")
    delete_key_response = await memory.delete_plan_state(
        plan_id=plan_id,
        key="progress",  # Remove progress tracking
        service_tenant_id=tenant_id,
        service_user_id=user_id
    )
    if delete_key_response.deleted:
        print("   ✓ Deleted 'progress' key")
    else:
        print("   ✗ Key not found")
    
    # Delete all state for plan
    print("\n7. Cleaning up all state for the plan...")
    delete_all_response = await memory.delete_plan_state(
        plan_id=plan_id,
        service_tenant_id=tenant_id,
        service_user_id=user_id
    )
    print(f"   ✓ Deleted {delete_all_response.count_deleted} state entries")
    
    print("\n" + "=" * 60)
    print("\n💡 This is verbose! See planner.py for WorkflowState helper.")
    print("   WorkflowState also provides: state.delete(key) and state.cleanup()")
    print()
    
    # Clean up
    await memory.close()


if __name__ == "__main__":
    asyncio.run(demonstrate_raw_memory_api())
