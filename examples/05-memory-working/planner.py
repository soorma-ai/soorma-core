"""
Planner agent that initializes workflow state and orchestrates tasks.

This agent:
1. Receives a goal
2. Decomposes it into tasks
3. Stores state in working memory (using WorkflowState helper)
4. Triggers the first task
"""

import asyncio
from typing import Any, Dict
import uuid
from soorma import Worker
from soorma.context import PlatformContext
from soorma.workflow import WorkflowState


planner = Worker(
    name="workflow-planner",
    description="Decomposes goals into tasks and manages workflow state",
    capabilities=["planning", "orchestration"],
    events_consumed=["goal.received"],
    events_produced=["task.assigned", "workflow.completed"],
)


@planner.on_event("goal.received", topic="action-requests")
async def handle_goal(event: Dict[str, Any], context: PlatformContext):
    """
    Receive a goal, decompose into tasks, and initialize workflow.
    """
    data = event.get("data", {})
    goal = data.get("goal")
    plan_id = str(uuid.uuid4())
    
    # Extract tenant_id and user_id from event envelope (infrastructure metadata)
    tenant_id = event.get("tenant_id", "00000000-0000-0000-0000-000000000000")
    user_id = event.get("user_id", "00000000-0000-0000-0000-000000000001")
    
    print(f"\n📋 New Goal: {goal}")
    print(f"   Plan ID: {plan_id}")
    print(f"   Tenant: {tenant_id}, User: {user_id}")
    
    # Initialize workflow state using WorkflowState helper
    state = WorkflowState(
        context.memory, 
        plan_id,
        tenant_id=tenant_id,
        user_id=user_id
    )
    
    # Store goal and status
    print("   Initializing workflow state...")
    await state.set("goal", goal)
    await state.set("status", "planning")
    await state.record_action("planning.started")
    
    # Decompose into tasks (simplified - in real scenario, use LLM)
    tasks = ["research", "draft", "review"]
    await state.set("tasks", tasks)
    await state.set("current_task_index", 0)
    await state.set("results", {})
    
    print(f"   ✓ Decomposed into {len(tasks)} tasks: {tasks}")
    
    # Update status and trigger first task
    await state.set("status", "in_progress")
    await state.record_action("workflow.started")
    
    print(f"   Triggering first task: {tasks[0]}")
    
    await context.bus.publish(
        event_type="task.assigned",
        topic="action-requests",
        data={
            "plan_id": plan_id,
            "task": tasks[0],
            "goal": goal,
            "task_index": 0
        },
        tenant_id=tenant_id,
        user_id=user_id,
    )
    
    print("   ✓ Workflow initialized\n")


if __name__ == "__main__":
    print("🎯 Workflow Planner with Working Memory")
    print("=" * 50)
    print("This planner uses WorkflowState to manage plan-scoped state.")
    print("\nListening for goal.received events...")
    print("\nStart other agents:")
    print("  python worker.py   (in another terminal)")
    print("  python coordinator.py   (in another terminal)")
    print("\nThen submit goals:")
    print("  python client.py 'Write a blog post about Docker'")
    print()
    
    planner.run()
