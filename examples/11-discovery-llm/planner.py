"""
Research Planner — Example 11: LLM-Based Dynamic Discovery.

Demonstrates the full LLM-driven dynamic discovery loop with correct
request/response ownership:

  CLIENT → research.goal (response_event="research.completed")
    └─ PLANNER on_goal: discover worker, generate payload, dispatch
       PLANNER → research.requested (response_event="research.worker.completed")
         └─ WORKER: process, task.complete() → research.worker.completed
           └─ PLANNER on_event: normalize result, respond to client
              PLANNER → research.completed → CLIENT

Key design principles:
  - 1:1 request/response ownership: the planner responds to the client;
    the worker NEVER has a direct path back to the client.
  - The planner translates the worker's internal result into the client
    contract schema — critical for dynamic discovery where the client has
    no knowledge of the worker's schema.
  - correlation_id threads through the entire chain so all parties can
    correlate request → result without embedding IDs in event names.

SDK patterns shown:
  - ctx.registry.discover(requirements=...) — capability-based lookup
  - ctx.registry.get_event(name) → payload_schema_name
  - ctx.registry.get_schema(name) → PayloadSchema
  - planner.generate_payload(schema, context) — LLM payload generation
  - ctx.bus.request(event_type, data, response_event, correlation_id)
  - @planner.on_event(event, topic=ACTION_RESULTS) — receive worker result
  - ctx.bus.respond(event_type, data, correlation_id) — reply to client
"""

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

    The planner owns the client contract.  It translates the client's
    high-level goal into a worker-specific payload determined at runtime via
    Registry discovery and LLM-driven schema population.

    This handler does NOT respond to the client — that is the responsibility
    of handle_research_worker_result() once the worker's result arrives.

    Args:
        goal: GoalContext containing the research objective and client metadata
              (correlation_id, response_event, tenant_id, user_id).
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
    """Receive the worker's result, normalize it, and deliver to the client.

    The planner translates the worker's internal task.complete() envelope
    into the canonical research.completed schema that the client expects.
    This decouples the client from any knowledge of the worker or its schema.

    Args:
        event: EventEnvelope from the worker (via task.complete()).
              Contains correlation_id matching the original client goal.
        context: PlatformContext for bus access.
    """
    data = event.data or {}
    # task.complete() wraps the result dict under the "result" key
    result: Dict[str, Any] = data.get("result", {})

    topic = result.get("topic", "")
    findings = result.get("findings", [])
    result_count = result.get("result_count", len(findings))

    print(f"\n[planner] Worker result received: {result_count} finding(s) on {topic!r}")

    # Respond to the client using the canonical event name and the same
    # correlation_id that arrived from the client (threaded by bus.request).
    await context.bus.respond(
        event_type="research.completed",
        data={
            "topic": topic,
            "findings": findings,
            "result_count": result_count,
        },
        correlation_id=event.correlation_id,
        tenant_id=event.tenant_id,
        user_id=event.user_id,
    )
    print(f"[planner] ✓ research.completed sent to client (correlation: {event.correlation_id})")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    planner.run()
