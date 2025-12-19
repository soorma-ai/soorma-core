#!/usr/bin/env python3
"""
Hello World Worker Agent

Demonstrates the Worker pattern using the Soorma SDK.
The Worker receives tasks and executes them, optionally invoking Tools.
"""

from soorma import Worker
from soorma.agents.worker import TaskContext


# Create a Worker instance using the SDK
worker = Worker(
    name="hello-worker",
    description="Executes greeting tasks",
    capabilities=["greet", "greeting"],
)


@worker.on_task("greet")
async def handle_greet(task: TaskContext, context) -> dict:
    """
    Handle a greet task.
    
    This is the SDK pattern: use @worker.on_task() decorator to register
    a handler for a specific task name.
    
    Args:
        task: TaskContext with task_id, task_name, data, and helper methods
        context: PlatformContext with registry, memory, bus, tracker clients
    
    Returns:
        Result dictionary
    """
    print(f"\n⚙️  Worker received task: {task.task_name}")
    print(f"   Task ID: {task.task_id}")
    print(f"   Data: {task.data}")
    
    # Report progress using TaskContext helper
    await task.report_progress(0.3, "Preparing greeting...")
    
    name = task.data.get("name", "World")
    
    # Option 1: Invoke tool via bus (for async tool invocation)
    # tool_result = await context.bus.request("tool.greeting-tool", {"operation": "greet", "name": name})
    
    # Option 2: For this simple example, generate greeting directly
    await task.report_progress(0.6, "Generating greeting...")
    
    greeting = f"Hello, {name}! 👋"
    print(f"\n   💬 {greeting}")
    
    await task.report_progress(1.0, "Completed!")
    
    return {
        "greeting": greeting,
        "name": name,
        "status": "completed",
    }


@worker.on_startup
async def startup():
    """Called when the worker starts."""
    print("\n🚀 Hello Worker started!")
    print(f"   Name: {worker.name}")
    print(f"   Capabilities: {worker.capabilities}")
    print("   Listening for 'greet' tasks...")
    print("   Press Ctrl+C to stop\n")


@worker.on_shutdown
async def shutdown():
    """Called when the worker stops."""
    print("\n👋 Hello Worker shutting down")


if __name__ == "__main__":
    worker.run()
