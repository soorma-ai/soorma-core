"""
Choreography Planner Example - Feedback Analysis.

Demonstrates Stage 4 Phase 2 ChoreographyPlanner pattern with
autonomous event-driven orchestration.

Key Pattern: The SDK's execute_decision() automatically handles metadata propagation.
When PublishAction includes response_event and correlation_id, the SDK routes through
bus.request() for request/response choreography. No manual intervention needed.
"""

import logging
from typing import Optional
from uuid import uuid4

from soorma.ai.choreography import ChoreographyPlanner
from soorma.agents.planner import GoalContext
from soorma.context import PlatformContext
from soorma.plan_context import PlanContext
from soorma_common.decisions import PlanAction, PlannerDecision
from soorma_common.events import EventEnvelope


planner = ChoreographyPlanner(
    name="feedback-orchestrator",
    reasoning_model="gpt-4o",
    system_instructions=(
        "You are a feedback analysis orchestrator. Your goal is to produce a comprehensive feedback report.\n\n"
        "LOGICAL WORKFLOW (discover events from registry to fulfill each capability):\n"
        "1. DATA RETRIEVAL: First, you need raw feedback data from the datastore\n"
        "   - Look for events that retrieve/fetch/load customer feedback\n"
        "   - Ensure you get entries with ratings and comments\n"
        "2. ANALYSIS: Once you have raw data, extract insights\n"
        "   - Look for events that analyze/process sentiment or patterns\n"
        "   - You need sentiment breakdown (positive/negative counts) and summary\n"
        "3. REPORTING: Finally, format the insights into a presentable report\n"
        "   - Look for events that generate/create/format reports\n"
        "   - The output should be human-readable with timestamp\n"
        "4. COMPLETION: When you have the final report, complete the workflow\n\n"
        "IMPORTANT: \n"
        "- Choose events based on their CAPABILITY descriptions, not their names\n"
        "- Always set response_event to track request/response flow\n"
        "- Use correlation_id to maintain task tracking across the pipeline\n"
        "- Only use events that exist in the available events list"
    ),
)


@planner.on_goal("analyze.feedback")
async def handle_goal(goal: GoalContext, context: PlatformContext) -> None:
    """Handle incoming feedback analysis goals.

    Args:
        goal: GoalContext containing the analysis request.
        context: PlatformContext for service access.
    """
    print("\n[planner] Goal received: analyze.feedback")
    print(f"[planner] Correlation: {goal.correlation_id}")

    print("[planner] Creating plan context...")
    plan = await PlanContext.create_from_goal(
        goal=goal,
        context=context,
        state_machine={},
        current_state="reasoning",
        status="running",
    )
    print(f"[planner] Plan created: {plan.plan_id}")

    print("[planner] Calling ChoreographyPlanner.reason_next_action()...")
    try:
        decision = await planner.reason_next_action(
            trigger=f"New goal: {goal.data.get('objective', 'feedback analysis')}",
            context=context,
            plan_id=plan.plan_id,
            custom_context={"goal": goal.data},
        )
        print(f"[planner] Decision received: {decision.next_action.action}")
    except Exception as e:
        print(f"[planner] ERROR during reason_next_action: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    plan.current_state = decision.current_state
    await plan.save()

    await planner.execute_decision(
        decision,
        context,
        goal_event=goal,
        plan=plan,
    )


@planner.on_transition()
async def handle_transition(
    event: EventEnvelope,
    context: PlatformContext,
    plan: PlanContext,
    next_state: str,
) -> None:
    """Handle plan transitions for choreography.

    Args:
        event: Incoming event envelope triggering the transition.
        context: PlatformContext for service access.
        plan: Restored PlanContext instance.
        next_state: Proposed next state name (unused for choreography).
    """
    print(f"\n[planner] ▶ Transition triggered by: {event.type}")
    print(f"[planner] Correlation: {event.correlation_id}")
    print(f"[planner] Plan ID: {plan.plan_id}")
    
    _ = next_state
    plan.results[event.type] = event.data or {}

    if event.tenant_id and event.user_id:
        try:
            progress = await context.tracker.get_plan_progress(
                plan.plan_id,
                tenant_id=event.tenant_id,
                user_id=event.user_id,
            )
            if progress:
                print(
                    f"[planner] Tracker progress: {progress.completed_tasks}/"
                    f"{progress.task_count} tasks"
                )
        except Exception as exc:
            print(f"[planner] Tracker query failed: {exc}")

    print(f"[planner] Calling reason_next_action for event: {event.type}")
    decision = await planner.reason_next_action(
        trigger=f"Event: {event.type}",
        context=context,
        plan_id=plan.plan_id,
        custom_context={"last_event": event.type, "event_data": event.data or {}},
    )
    print(f"[planner] Decision: {decision.next_action.action}")
    
    plan.current_state = decision.current_state
    await plan.save()

    await planner.execute_decision(
        decision,
        context,
        goal_event=event,
        plan=plan,
    )


@planner.on_startup
async def startup() -> None:
    """Planner startup hook."""
    print("\n[planner] feedback-orchestrator started")
    print("[planner] Listening for analyze.feedback")


@planner.on_shutdown
async def shutdown() -> None:
    """Planner shutdown hook."""
    print("\n[planner] feedback-orchestrator shutting down")


if __name__ == "__main__":
    # Configure logging - show agent logic, suppress noisy SDK logs
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s:%(name)s:%(message)s",
    )
    # Suppress noisy SDK/infrastructure logs
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("soorma.registry.client").setLevel(logging.WARNING)
    logging.getLogger("soorma.agents.base").setLevel(logging.WARNING)
    logging.getLogger("soorma.events").setLevel(logging.WARNING)
    logging.getLogger("soorma.context").setLevel(logging.WARNING)
    logging.getLogger("soorma.task_context").setLevel(logging.WARNING)
    logging.getLogger("soorma.plan_context").setLevel(logging.WARNING)
    planner.run()
