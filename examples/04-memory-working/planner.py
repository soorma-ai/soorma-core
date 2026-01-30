"""
Planner agent that orchestrates workflows with request/response pattern.

This demonstrates CORRECT request/response usage WITH working memory:
- Planner receives request from client
- Planner stores client request info (correlation_id, response_event) in WORKING MEMORY
- Planner requests workers to perform tasks
- Planner LISTENS for responses from workers
- When task completes, planner RETRIEVES client info from working memory
- Planner makes decisions and requests next task
- Planner responds back to client when workflow is complete

Key: The requester (planner) always listens for its response_event.
     Working memory stores the client request info for later retrieval.
     This enables fully distributed, asynchronous workflow orchestration.
No in-memory state - everything is in working memory!
"""

import asyncio
from typing import Any, Dict
import uuid
from soorma import Worker
from soorma.context import PlatformContext
from soorma.workflow import WorkflowState
from soorma_common.events import EventEnvelope, EventTopic


planner = Worker(
    name="workflow-planner",
    description="Orchestrates workflows with request/response pattern",
    capabilities=["planning", "orchestration"],
    events_consumed=["workflow.start", "task.completed"],
    events_produced=["task.assigned", "workflow.completed"],
)


@planner.on_event("workflow.start", topic=EventTopic.ACTION_REQUESTS)
async def handle_workflow_start(event: EventEnvelope, context: PlatformContext):
    """
    Start a workflow - client sends request expecting workflow.completed response.
    
    This demonstrates correct request/response:
    - We receive the request with response_event="workflow.completed"
    - We will listen for task.completed responses from workers
    - We respond back with "workflow.completed" when done
    """
    data = event.data or {}
    workflow_name = data.get("workflow_name", "demo-workflow")
    plan_id = str(uuid.uuid4())
    
    # Extract tenant_id and user_id from event envelope (infrastructure metadata)
    tenant_id = event.tenant_id or "00000000-0000-0000-0000-000000000000"
    user_id = event.user_id or "00000000-0000-0000-0000-000000000001"
    
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
    
    # Store client request info in working memory (for distributed access)
    # This is why we need working memory - when task.completed comes back,
    # we need to know how to respond to the original client
    await state.set("client_correlation_id", event.correlation_id)
    await state.set("client_response_event", event.response_event or "workflow.completed")
    await state.set("client_tenant_id", tenant_id)
    await state.set("client_user_id", user_id)
    
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
    
    # Request first task - we (planner) will listen for task.completed response
    await context.bus.request(
        event_type="task.assigned",
        response_event="task.completed",
        data={
            "plan_id": plan_id,
            "task": tasks[0],
            "task_index": 0
        },
        correlation_id=plan_id,  # Use plan_id for our request correlation
        tenant_id=tenant_id,
        user_id=user_id,
    )
    
    print("   ✓ Workflow initialized, waiting for responses\n")


async def request_next_task(
    context: PlatformContext,
    state: WorkflowState,
    plan_id: str,
    tasks: list,
    next_index: int,
    tenant_id: str,
    user_id: str,
):
    """Request the next task in the workflow."""
    if next_index >= len(tasks):
        return False  # No more tasks
    
    next_task = tasks[next_index]
    await state.set("current_task_index", next_index)
    
    print(f"   📋 Requesting next task: {next_task}")
    
    # Request next task - we (planner) will listen for task.completed response
    await context.bus.request(
        event_type="task.assigned",
        response_event="task.completed",
        data={
            "plan_id": plan_id,
            "task": next_task,
            "task_index": next_index
        },
        correlation_id=plan_id,  # Use plan_id for our request correlation
        tenant_id=tenant_id,
        user_id=user_id,
    )
    
    return True  # Task requested


@planner.on_event("task.completed", topic=EventTopic.ACTION_RESULTS)
async def handle_task_completed(event: EventEnvelope, context: PlatformContext):
    """
    Handle task completion response (REQUEST/RESPONSE pattern).
    
    This handler ONLY runs for responses to OUR requests (correlation_id = plan_id).
    We orchestrate the workflow progression here.
    """
    data = event.data or {}
    plan_id = data.get("plan_id")
    completed_task = data.get("task")
    task_index = data.get("task_index")
    
    # Extract tenant_id and user_id from event envelope
    tenant_id = event.tenant_id or "00000000-0000-0000-0000-000000000000"
    user_id = event.user_id or "00000000-0000-0000-0000-000000000001"
    
    print(f"\n✓ Task Completed: {completed_task}")
    print(f"   Plan ID: {plan_id}")
    
    # Access plan state
    state = WorkflowState(
        context.memory,
        plan_id,
        tenant_id=tenant_id,
        user_id=user_id
    )
    
    # Store task result
    result = data.get("result", {})
    await state.set(completed_task, result)
    
    tasks = await state.get("tasks", [])
    current_index = await state.get("current_task_index", 0)
    
    print(f"   Progress: {current_index + 1}/{len(tasks)} tasks")
    
    # Check if there are more tasks
    next_index = current_index + 1
    
    if next_index < len(tasks):
        # Request next task
        await request_next_task(context, state, plan_id, tasks, next_index, tenant_id, user_id)
    else:
        # All tasks completed - respond back to client
        print(f"   🎉 Workflow completed!")
        
        await state.set("status", "completed")
        await state.record_action("workflow.completed")
        
        # Get all results and history
        results = {}
        for task in tasks:
            result = await state.get(task)
            results[task] = result
        
        history = await state.get_action_history()
        
        print(f"   Action history: {history}")
        
        # Retrieve client request info from working memory
        client_correlation_id = await state.get("client_correlation_id")
        client_response_event = await state.get("client_response_event")
        client_tenant_id = await state.get("client_tenant_id")
        client_user_id = await state.get("client_user_id")
        
        # Respond back to CLIENT using their response_event
        await context.bus.respond(
            event_type=client_response_event,
            data={
                "plan_id": plan_id,
                "workflow_name": await state.get("workflow_name"),
                "results": results,
                "history": history
            },
            correlation_id=client_correlation_id,
            tenant_id=client_tenant_id,
            user_id=client_user_id,
        )
        
        print("   ✓ Response sent to client")
        
        # Clean up working memory after workflow completion
        # This removes all state for the plan, freeing up resources
        # Useful for long-running systems handling many workflows
        count = await state.cleanup()
        print(f"   ✓ Cleaned up {count} state entries from working memory\n")


if __name__ == "__main__":
    print("🎯 Workflow Planner - REQUEST/RESPONSE Pattern")
    print("=" * 60)
    print("This planner demonstrates CORRECT request/response usage:")
    print()
    print("1. Receives workflow.start REQUEST from client")
    print("2. Sends task.assigned REQUEST to worker")
    print("3. LISTENS for task.completed RESPONSE from worker")
    print("4. Orchestrates next task or completes workflow")
    print("5. Sends workflow.completed RESPONSE back to client")
    print()
    print("Key: Planner (requester) always listens for responses")
    print("     No chaining - only request/response pattern")
    print()
    print("Listening for workflow.start events...")
    print("\nStart the worker:")
    print("  python worker.py   (in another terminal)")
    print("\nThen start the workflow:")
    print("  python client.py")
    print()
    
    planner.run()
