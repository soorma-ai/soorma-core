#!/usr/bin/env python3
"""
Hello World Planner Agent

Demonstrates the Planner pattern using the Soorma SDK.
The Planner receives goals and decomposes them into tasks for Workers.
"""

from soorma import Planner
from soorma.agents.planner import Goal, Plan, Task


# Create a Planner instance using the SDK
planner = Planner(
    name="hello-planner",
    description="Plans greeting workflows",
    capabilities=["greeting", "hello-world"],
)


@planner.on_goal("greeting.goal")
async def plan_greeting(goal: Goal, context) -> Plan:
    """
    Handle a greeting goal.
    
    This is the SDK pattern: use @planner.on_goal() decorator to register
    a handler that receives a Goal and returns a Plan.
    
    Args:
        goal: The Goal object with goal_type, data, goal_id, etc.
        context: PlatformContext with registry, memory, bus, tracker clients
    
    Returns:
        A Plan containing tasks to execute
    """
    print(f"\n📋 Planner received goal")
    print(f"   Goal ID: {goal.goal_id}")
    print(f"   Data: {goal.data}")
    
    # Extract the name to greet from goal data
    name = goal.data.get("name", "World")
    
    # Create a plan with a task assigned to hello-worker
    plan = Plan(
        goal=goal,
        tasks=[
            Task(
                name="greet",
                assigned_to="hello-worker",
                data={"name": name},
            )
        ],
    )
    
    print(f"\n📝 Created plan: {plan.plan_id}")
    print(f"   Tasks: {len(plan.tasks)}")
    for task in plan.tasks:
        print(f"   - {task.name} -> {task.assigned_to}")
    
    return plan


@planner.on_startup
async def startup():
    """Called when the planner starts."""
    print("\n🚀 Hello Planner started!")
    print(f"   Name: {planner.name}")
    print(f"   Capabilities: {planner.capabilities}")
    print("   Listening for 'greeting.goal' events...")
    print("   Press Ctrl+C to stop\n")


@planner.on_shutdown
async def shutdown():
    """Called when the planner stops."""
    print("\n👋 Hello Planner shutting down")


if __name__ == "__main__":
    planner.run()
