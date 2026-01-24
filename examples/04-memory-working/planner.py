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
    description="Initializes workflows with fixed tasks and manages workflow state",
    capabilities=["planning", "orchestration"],
    events_consumed=["workflow.start"],
    events_produced=["task.assigned", "workflow.completed"],
)


@planner.on_event("workflow.start", topic="action-requests")
async def handle_workflow_start(event: Dict[str, Any], context: PlatformContext):
    """
    Start a workflow with fixed tasks (demo purposes).
    
    This demonstrates WorkflowState mechanics. For dynamic, LLM-based
    task generation from goals, see example 08-planner-worker-basic.
    """
    data = event.get("data", {})
    workflow_name = data.get("workflow_name", "demo-workflow")
    plan_id = str(uuid.uuid4())
    
    # Extract tenant_id and user_id from event envelope (infrastructure metadata)
    tenant_id = event.get("tenant_id", "00000000-0000-0000-0000-000000000000")
    user_id = event.get("user_id", "00000000-0000-0000-0000-000000000001")
    
    print(f"\n📋 Starting Workflow: {workflow_name}")
    print(f"   Plan ID: {plan_id}")
    print(f"   Tenant: {tenant_id}, User: {user_id}")
    
    # Initialize workflow state using WorkflowState helper
    state = WorkflowState(
        context.memory, 
        plan_id,
        tenant_id=tenant_id,
        user_id=user_id
    )
    
    # Store workflow metadata and status
    print("   Initializing workflow state...")
    await state.set("workflow_name", workflow_name)
    await state.set("status", "planning")
    await state.record_action("planning.started")
    
    # Fixed task list (for demo purposes)
    # Real applications would use LLM to generate tasks from goals
    tasks = ["research", "draft", "review"]
    await state.set("tasks", tasks)
    await state.set("current_task_index", 0)
    await state.set("results", {})
    
    print(f"   ✓ Created workflow with {len(tasks)} tasks: {tasks}")
    print(f"   (Note: Task list is fixed for this demo)")
    
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
    print("\nListening for workflow.start events...")
    print("\nStart other agents:")
    print("  python worker.py   (in another terminal)")
    print("  python coordinator.py   (in another terminal)")
    print("\nThen start the workflow:")
    print("  python client.py")
    print()
    
    planner.run()
