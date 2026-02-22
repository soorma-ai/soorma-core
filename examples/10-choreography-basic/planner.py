"""
Choreography Planner Example - Feedback Analysis.

Demonstrates Stage 4 Phase 2 ChoreographyPlanner pattern with
autonomous event-driven orchestration.

Key Pattern: The SDK's execute_decision() automatically handles metadata propagation.
When PublishAction includes response_event and correlation_id, the SDK routes through
bus.request() for request/response choreography. No manual intervention needed.
"""

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
        "You are a feedback analysis planner. Orchestrate this pipeline:\n"
        "1) Publish data.fetch.requested with response_event='data.fetched'\n"
        "2) Publish analysis.requested with response_event='analysis.completed'\n"
        "3) Publish report.requested with response_event='report.ready'\n"
        "4) Complete with the final report data.\n"
        "For each publish, use correlation_id to track the task. "
        "Only publish events that exist in the registry."
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

    plan = await PlanContext.create_from_goal(
        goal=goal,
        context=context,
        state_machine={},
        current_state="reasoning",
        status="running",
    )

    decision = await planner.reason_next_action(
        trigger=f"New goal: {goal.data.get('objective', 'feedback analysis')}",
        context=context,
        plan_id=plan.plan_id,
        custom_context={"goal": goal.data},
    )
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

    decision = await planner.reason_next_action(
        trigger=f"Event: {event.type}",
        context=context,
        plan_id=plan.plan_id,
        custom_context={"last_event": event.type, "event_data": event.data or {}},
    )
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
    planner.run()
