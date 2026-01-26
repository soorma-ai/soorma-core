"""
Worker agent that executes tasks in REQUEST/RESPONSE pattern.

This agent:
1. Receives task assignment REQUEST from planner
2. Executes the task
3. Stores results in working memory
4. Sends RESPONSE back to planner

Key: Worker responds directly to the PLANNER (requester).
     Planner orchestrates next steps based on response.
"""

import asyncio
from typing import Any, Dict
from soorma import Worker
from soorma.context import PlatformContext
from soorma.workflow import WorkflowState
from soorma_common.events import EventEnvelope, EventTopic


worker = Worker(
    name="task-worker",
    description="Executes tasks from workflow plans",
    capabilities=["task-execution", "research", "drafting", "review"],
    events_consumed=["task.assigned"],
    events_produced=["task.completed"],
)


@worker.on_event("task.assigned", topic=EventTopic.ACTION_REQUESTS)
async def handle_task(event: EventEnvelope, context: PlatformContext):
    """
    Execute an assigned task using plan state from working memory.
    """
    data = event.data or {}
    plan_id = data.get("plan_id")
    task = data.get("task")
    task_index = data.get("task_index")
    
    # Extract tenant_id and user_id from event envelope (infrastructure metadata)
    tenant_id = event.tenant_id or "00000000-0000-0000-0000-000000000000"
    user_id = event.user_id or "00000000-0000-0000-0000-000000000001"
    
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
    
    # Extract response event from request (caller/planner specifies expected response)
    response_event_type = event.response_event or "task.completed"
    
    # Notify completion using caller-specified response event
    await context.bus.respond(
        event_type=response_event_type,
        data={
            "plan_id": plan_id,
            "task": task,
            "task_index": task_index,
            "result": result
        },
        correlation_id=event.correlation_id,
        tenant_id=tenant_id,
        user_id=user_id,
    )
    
    print()


if __name__ == "__main__":
    print("👷 Task Worker - REQUEST/RESPONSE Pattern")
    print("=" * 50)
    print("This worker executes tasks in request/response pattern:")
    print()
    print("1. Receives task.assigned REQUEST from planner")
    print("2. Executes task")
    print("3. Sends task.completed RESPONSE back to planner")
    print()
    print("Listening for task.assigned events...")
    print("\nEnsure planner is running:")
    print("  python planner.py")
    print()
    
    worker.run()
