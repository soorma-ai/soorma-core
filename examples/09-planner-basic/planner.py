"""
Basic Planner Example - State Machine Orchestration

Demonstrates Stage 4 Phase 1 Planner patterns:
- @on_goal() decorator for goal handling
- PlanContext for state machine management
- @on_transition() decorator for event routing
- GoalContext wrapper for clean goal access
"""

from soorma.agents.planner import Planner, GoalContext
from soorma.plan_context import PlanContext
from soorma.context import PlatformContext
from soorma_common.events import EventEnvelope, EventTopic
from soorma_common.state import StateConfig, StateAction, StateTransition


# Create Planner agent
planner = Planner(
    name="basic-planner",
    description="Basic planner demonstrating state machine orchestration",
    capabilities=["planning", "research_orchestration"],
)


@planner.on_startup
async def startup():
    """Initialize planner on startup."""
    print("\n🚀 Basic Planner Started")
    print("   Listening for: research.goal")
    print("   State machine: start → research → complete")
    print("   Subscribed topics: action-requests, action-results (for transitions)")
    print()


@planner.on_shutdown
async def shutdown():
    """Cleanup on shutdown."""
    print("\n🛑 Basic Planner Shutting Down")


@planner.on_goal("research.goal")
async def handle_research_goal(goal: GoalContext, context: PlatformContext):
    """
    Handle research goals by creating a state machine plan.
    
    Flow:
    1. Create PlanContext with state machine
    2. Save plan to Memory Service
    3. Execute initial state (start → research)
    
    The state machine will:
    - Start in 'start' state
    - Auto-transition to 'research' state
    - Publish research.task with goal data
    - Wait for research.complete event
    - Transition to 'complete' state
    - Publish final result
    """
    print(f"\n📋 Received goal: {goal.event_type}")
    print(f"   Topic: {goal.data.get('topic', 'N/A')}")
    print(f"   Correlation: {goal.correlation_id}")
    print(f"   Response Event: {goal.response_event}")
    
    # Define state machine
    states = {
        "start": StateConfig(
            state_name="start",
            description="Initial state",
            default_next="research",  # Auto-transition to research
        ),
        "research": StateConfig(
            state_name="research",
            description="Research phase - publish task and wait for result",
            action=StateAction(
                event_type="research.task",
                response_event="research.complete",
                data={
                    "query": "{{goal_data.topic}}",  # Template interpolation
                    "max_results": 3
                }
            ),
            transitions=[
                StateTransition(
                    on_event="research.complete",
                    to_state="complete"
                )
            ],
        ),
        "complete": StateConfig(
            state_name="complete",
            description="Terminal state",
            is_terminal=True,
        )
    }
    
    # Create and persist plan context
    plan = await PlanContext.create_from_goal(
        goal=goal,
        context=context,
        state_machine=states,
        current_state="start",
        status="pending",
    )
    
    print(f"📝 Creating plan with {len(states)} states")
    print(f"   Plan ID: {plan.plan_id}")
    
    print(f"📋 Created plan record: {plan.plan_id}")
    print(f"💾 Saved plan context: {plan.plan_id}")
    
    # Execute initial state (start → research)
    await plan.execute_next()
    print(f"▶️  Executing state: {plan.current_state}")


# Handle transitions for all plan-related events
@planner.on_transition()
async def handle_transition(
    event: EventEnvelope,
    context: PlatformContext,
    plan: PlanContext,
    next_state: str,
) -> None:
    """Handle research completion and transition plan state."""
    print(f"\n📥 Transition: {event.type}")
    print(f"   Correlation: {event.correlation_id}")
    
    print(f"   Plan ID: {plan.plan_id}")
    print(f"   Current state: {plan.current_state}")
    
    # Update state
    plan.current_state = next_state
    print(f"🔄 State transition: {plan.current_state}")
    
    # Store event data for next state
    plan.results[event.type] = event.data
    
    # Check if complete
    if plan.is_complete():
        print(f"✅ Plan complete: {plan.plan_id}")
        
        # Extract final result
        research_data = event.data or {}
        result = {
            "summary": research_data.get("summary", "Research complete"),
            "papers_found": research_data.get("papers_found", 0),
            "papers": research_data.get("papers", []),
            "topic": plan.goal_data.get("topic", "unknown")
        }
        
        # Publish final result
        print(f"📤 Publishing final result")
        print(f"   Response Event: {plan.response_event}")
        print(f"   Original Correlation: {plan.correlation_id}")
        await plan.finalize(result=result)
    else:
        # Execute next state
        print(f"▶️  Executing next state: {plan.current_state}")
        await plan.execute_next(event)


if __name__ == "__main__":
    # Run the planner
    planner.run()
