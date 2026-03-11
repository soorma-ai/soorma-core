"""
Research Planner — Example 11: LLM-Based Dynamic Discovery.

Demonstrates symmetric schema-driven dispatch where the CLIENT owns the
response schema, not the planner:

  CLIENT → research.goal  (envelope: response_schema_name="research_result_v1")
    └─ PLANNER on_goal:
         SDK auto-saves {response_schema_name, response_event, …} to working memory
         discover worker → get worker schema → generate_payload() → dispatch
         PLANNER → research.requested
           └─ WORKER: task.complete() → research.worker.completed
             └─ PLANNER on_event:
                  read response_schema_name from goal metadata (working memory)
                  registry.get_schema(name) → generate_payload() → respond
                  PLANNER → research.completed → CLIENT

The planner is completely schema-agnostic on the outbound side:
  - It does not declare any response schema of its own
  - It reads the client’s requested schema name from goal metadata
  - It adapts its output to whatever schema the current client registered

This makes the planner reusable across clients with different response shapes
without any planner code changes.

SDK patterns shown:
  - ctx.registry.discover(requirements=...) — capability-based lookup
  - ctx.registry.get_event(name) → payload_schema_name
  - ctx.registry.get_schema(name) → PayloadSchema
  - planner.generate_payload(schema, context) — LLM payload generation (both directions)
  - ctx.memory.get_goal_metadata(correlation_id, ...) — retrieve client routing metadata
  - @planner.on_event(event, topic=ACTION_RESULTS) — receive worker result
  - ctx.bus.respond(...) — reply to client
"""

import json
import logging
import os
from typing import Any, Dict

from dotenv import load_dotenv

from soorma.ai.choreography import ChoreographyPlanner
from soorma.agents.planner import GoalContext
from soorma.context import PlatformContext
from soorma_common.events import EventEnvelope, EventTopic

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Planner declaration
# ---------------------------------------------------------------------------

planner = ChoreographyPlanner(
    name="research-planner",
    reasoning_model=os.environ.get("LLM_MODEL", "gpt-4o-mini"),
    # No events_produced — the client owns the response schema contract.
    # The planner reads response_schema_name from goal metadata at runtime.
    system_instructions=(
        "You are a research orchestrator. Your goal is to dispatch a research "
        "request to the most appropriate worker discovered from the Registry.\n\n"
        "WORKFLOW:\n"
        "1. DISCOVERY: Find agents capable of 'web_research'\n"
        "2. SCHEMA: Retrieve the consumed event schema for the chosen agent\n"
        "3. PAYLOAD: Use the schema to generate a well-formed research request\n"
        "4. DISPATCH: Publish the request and await the response\n\n"
        "Choose agents based on capability descriptions, not hardcoded names."
    ),
)


# ---------------------------------------------------------------------------
# Inbound: client → planner
# ---------------------------------------------------------------------------

@planner.on_goal("research.goal")
async def handle_research_goal(goal: GoalContext, context: PlatformContext) -> None:
    """Receive client goal, discover a capable worker, and dispatch the request.

    The planner translates the client's high-level goal into a worker-specific
    payload determined at runtime via Registry discovery and LLM-driven schema
    population.  The SDK's on_goal hook auto-saves goal routing metadata
    (including response_schema_name) to working memory so the result handler
    can retrieve it without any manual plumbing here.

    This handler does NOT respond to the client — that is the responsibility
    of handle_research_worker_result() once the worker's result arrives.

    Args:
        goal: GoalContext containing the research objective and client metadata
              (correlation_id, response_event, response_schema_name, etc.).
        context: PlatformContext for Registry, bus, and AI access.
    """
    description: str = goal.data.get("description", "")
    print(f"\n[planner] Goal received: research.goal")
    print(f"[planner] Description: {description!r}")

    # Step 1 — Dynamic discovery: find agents by capability, not by name.
    agents = await context.registry.discover(
        requirements=["web_research"],
        include_schemas=True,
    )
    if not agents:
        raise RuntimeError(
            "No agents found with capability 'web_research'. "
            "Is the worker running and registered?"
        )
    print(f"[planner] Discovered {len(agents)} agent(s) with capability: web_research")

    agent = agents[0]

    # Step 2 — Resolve the consumed event's schema from the event registry.
    consumed_event_name = agent.capabilities[0].consumed_event.event_name
    event_def = await context.registry.get_event(consumed_event_name)
    if not event_def or not event_def.payload_schema_name:
        raise RuntimeError(
            f"Event '{consumed_event_name}' has no schema registered. "
            "Check that the worker declared payload_schema_name on its capability."
        )
    schema = await context.registry.get_schema(event_def.payload_schema_name)
    print(f"[planner] Schema fetched: {schema.schema_name}")

    # Step 3 — LLM generates a payload conforming to the worker's schema.
    payload = await planner.generate_payload(schema=schema, context=description)
    print(f"[planner] LLM generated payload: {payload}")

    # Step 4 — Dispatch to the worker using an INTERNAL response event.
    # "research.worker.completed" is the planner–worker contract; the client
    # never sees it.  The same correlation_id from the client is threaded
    # through so the result handler can correlate back to this goal.
    print(f"[planner] Dispatching → {consumed_event_name} (internal response: research.worker.completed)")
    await context.bus.request(
        event_type=consumed_event_name,
        data=payload,
        response_event="research.worker.completed",
        correlation_id=goal.correlation_id,
    )
    print(f"[planner] ✓ Worker request published; awaiting research.worker.completed")


# ---------------------------------------------------------------------------
# Inbound: worker → planner (internal)
# ---------------------------------------------------------------------------

@planner.on_event("research.worker.completed", topic=EventTopic.ACTION_RESULTS)
async def handle_research_worker_result(event: EventEnvelope, context: PlatformContext) -> None:
    """Receive the worker's result, normalize it via the client's schema, and respond.

    The planner is schema-agnostic on the outbound side:
      1. Reads response_schema_name from goal metadata (saved by on_goal SDK hook)
      2. Fetches the schema the CLIENT registered — planner owns nothing here
      3. Calls generate_payload() to conform the raw result to that schema
      4. Publishes to the canonical response_event so the client receives it

    This means the same planner code works for any client with any response
    schema — no planner changes needed when the schema evolves.

    Args:
        event: EventEnvelope from the worker (via task.complete()).
               data["result"] contains the raw findings.
        context: PlatformContext for registry, memory, and bus access.
    """
    data = event.data or {}
    # task.complete() wraps the caller's dict under "result"
    raw_result: Dict[str, Any] = data.get("result", {})
    result_count = raw_result.get("result_count", len(raw_result.get("findings", [])))
    print(f"\n[planner] Worker result received: {result_count} finding(s)")

    # Retrieve the client's requested response schema name from goal metadata.
    # The on_goal SDK hook auto-saved this when the goal arrived — no manual
    # store/retrieve boilerplate needed in goal handler or here.
    goal_meta = await context.memory.get_goal_metadata(
        correlation_id=event.correlation_id,
        tenant_id=event.tenant_id,
        user_id=event.user_id,
    )
    response_schema_name = (goal_meta or {}).get("response_schema_name")
    response_event = (goal_meta or {}).get("response_event", "research.completed")

    if response_schema_name:
        schema = await context.registry.get_schema(response_schema_name)
        if schema:
            # Use LLM to produce a payload conforming to the client's schema.
            # The raw worker result is passed as context so the LLM can extract
            # and reformat it (add summary field, normalize finding structure, etc.)
            context_str = (
                f"Raw research result from worker (reformat into the required schema):\n"
                f"{json.dumps(raw_result, indent=2)}"
            )
            response_payload = await planner.generate_payload(schema=schema, context=context_str)
            print(f"[planner] LLM normalized response to schema: {response_schema_name}")
        else:
            logger.warning(f"Schema '{response_schema_name}' not found; using raw result")
            response_payload = raw_result
    else:
        # No schema requested — pass through raw result
        response_payload = raw_result

    await context.bus.respond(
        event_type=response_event,
        data=response_payload,
        correlation_id=event.correlation_id,
        tenant_id=event.tenant_id,
        user_id=event.user_id,
    )
    print(f"[planner] ✓ {response_event} sent to client (correlation: {event.correlation_id})")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    planner.run()
