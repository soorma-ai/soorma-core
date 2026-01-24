"""
Coordinator agent that advances workflow through stages.

This agent:
1. Listens for task completions
2. Checks workflow progress
3. Triggers next task or completes workflow
"""

import asyncio
from typing import Any, Dict
from soorma import Worker
from soorma.context import PlatformContext
from soorma.workflow import WorkflowState


coordinator = Worker(
    name="workflow-coordinator",
    description="Coordinates workflow progression through tasks",
    capabilities=["coordination", "workflow-management"],
    events_consumed=["task.completed"],
    events_produced=["task.assigned", "workflow.completed"],
)


@coordinator.on_event("task.completed", topic="action-results")
async def handle_task_completion(event: Dict[str, Any], context: PlatformContext):
    """
    Handle task completion and advance workflow.
    """
    data = event.get("data", {})
    plan_id = data.get("plan_id")
    completed_task = data.get("task")
    task_index = data.get("task_index")
    
    # Extract tenant_id and user_id from event envelope (infrastructure metadata)
    tenant_id = event.get("tenant_id", "00000000-0000-0000-0000-000000000000")
    user_id = event.get("user_id", "00000000-0000-0000-0000-000000000001")
    
    print(f"\n✓ Task Completed: {completed_task}")
    print(f"   Plan ID: {plan_id}")
    
    # Access plan state
    state = WorkflowState(
        context.memory, 
        plan_id,
        tenant_id=tenant_id,
        user_id=user_id
    )
    
    tasks = await state.get("tasks", [])
    workflow_name = await state.get("workflow_name", "demo-workflow")
    current_index = await state.get("current_task_index", 0)
    
    print(f"   Progress: {current_index + 1}/{len(tasks)} tasks")
    
    # Check if there are more tasks
    next_index = current_index + 1
    
    if next_index < len(tasks):
        # More tasks to execute
        next_task = tasks[next_index]
        await state.set("current_task_index", next_index)
        
        print(f"   Triggering next task: {next_task}")
        
        await context.bus.publish(
            event_type="task.assigned",
            topic="action-requests",
            data={
                "plan_id": plan_id,
                "task": next_task,
                "task_index": next_index
            },
            tenant_id=tenant_id,
            user_id=user_id,
        )
    else:
        # All tasks completed
        await state.set("status", "completed")
        await state.record_action("workflow.completed")
        
        # Get all results
        results = {}
        for task in tasks:
            result = await state.get(task)
            results[task] = result
        
        # Get action history for audit trail
        history = await state.get_action_history()
        
        print(f"   🎉 Workflow completed!")
        print(f"   Action history: {history}")
        
        # Publish completion
        await context.bus.publish(
            event_type="workflow.completed",
            topic="action-results",
            data={
                "plan_id": plan_id,
                "workflow_name": workflow_name,
                "results": results,
                "history": history
            }
        )
    
    print()


if __name__ == "__main__":
    print("🎛️  Workflow Coordinator")
    print("=" * 50)
    print("This coordinator manages workflow progression.")
    print("\nListening for task.completed events...")
    print("\nEnsure planner and worker are running:")
    print("  python planner.py")
    print("  python worker.py")
    print()
    
    coordinator.run()
