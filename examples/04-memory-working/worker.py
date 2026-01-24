"""
Worker agent that executes tasks using shared workflow state.

This agent:
1. Receives task assignments
2. Accesses plan state from working memory
3. Executes the task
4. Stores results back to working memory
5. Notifies completion
"""

import asyncio
from typing import Any, Dict
from soorma import Worker
from soorma.context import PlatformContext
from soorma.workflow import WorkflowState


worker = Worker(
    name="task-worker",
    description="Executes tasks from workflow plans",
    capabilities=["task-execution", "research", "drafting", "review"],
    events_consumed=["task.assigned"],
    events_produced=["task.completed"],
)


@worker.on_event("task.assigned", topic="action-requests")
async def handle_task(event: Dict[str, Any], context: PlatformContext):
    """
    Execute an assigned task using plan state from working memory.
    """
    data = event.get("data", {})
    plan_id = data.get("plan_id")
    task = data.get("task")
    task_index = data.get("task_index")
    
    # Extract tenant_id and user_id from event envelope (infrastructure metadata)
    tenant_id = event.get("tenant_id", "00000000-0000-0000-0000-000000000000")
    user_id = event.get("user_id", "00000000-0000-0000-0000-000000000001")
    
    print(f"\n⚙️  Task Assigned: {task}")
    print(f"   Plan ID: {plan_id}")
    
    # Access plan state
    state = WorkflowState(
        context.memory, 
        plan_id,
        tenant_id=tenant_id,
        user_id=user_id
    )
    workflow_name = await state.get("workflow_name", "demo-workflow")
    
    print(f"   Workflow: {workflow_name}")
    print(f"   Executing {task}...")
    
    # Simulate task execution with hardcoded results (demo purposes)
    # Real applications would do actual work based on task and context
    await asyncio.sleep(1)  # Simulate work
    
    result = None
    if task == "research":
        result = {
            "findings": [
                "Docker is a containerization platform",
                "Benefits: portability, isolation, efficiency",
                "Use cases: microservices, CI/CD, dev environments"
            ]
        }
    elif task == "draft":
        # Access research results from state
        research_result = await state.get("research", {})
        result = {
            "content": f"# Blog Post\n\nBased on research: {research_result}"
        }
    elif task == "review":
        draft_result = await state.get("draft", {})
        result = {
            "approved": True,
            "comments": "Looks good!"
        }
    else:
        result = {"status": "completed"}
    
    # Store result in working memory
    await state.set(task, result)
    await state.record_action(f"{task}.completed")
    
    # Get action history for logging
    history = await state.get_action_history()
    
    print(f"   ✓ Task completed")
    print(f"   Action history: {history}")
    
    # Notify completion
    await context.bus.publish(
        event_type="task.completed",
        topic="action-results",
        data={
            "plan_id": plan_id,
            "task": task,
            "task_index": task_index,
            "result": result
        },
        tenant_id=tenant_id,
        user_id=user_id,
    )
    
    print()


if __name__ == "__main__":
    print("👷 Task Worker with Working Memory")
    print("=" * 50)
    print("This worker accesses plan state via WorkflowState.")
    print("\nListening for task.assigned events...")
    print("\nEnsure planner and coordinator are running:")
    print("  python planner.py")
    print("  python coordinator.py")
    print()
    
    worker.run()
