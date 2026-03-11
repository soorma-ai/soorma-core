"""
Research Planner — Example 11: LLM-Based Dynamic Discovery.

Demonstrates fully symmetric schema-driven dispatch:

  CLIENT → research.goal
    └─ PLANNER on_goal:
         discover worker → get worker schema → generate_payload() → dispatch
         PLANNER → research.requested
           └─ WORKER: task.complete() → research.worker.completed
             └─ PLANNER on_event:
                  look up research.completed schema → generate_payload() → respond
                  PLANNER → research.completed → CLIENT

Both directions use the same dynamic pattern:
  - Outbound to worker:  discover schema at runtime → LLM generates conforming payload
  - Outbound to client:  look up declared response schema → LLM normalizes worker result

The planner owns the client contract by declaring RESEARCH_COMPLETED_EVENT
(with inline schema) in events_produced.  The SDK auto-registers it at startup
— exactly as the worker auto-registers its consumed event schema.

SDK patterns shown:
  - ctx.registry.discover(requirements=...) — capability-based lookup
  - ctx.registry.get_event(name) → payload_schema_name
  - ctx.registry.get_schema(name) → PayloadSchema
  - planner.generate_payload(schema, context) — LLM payload generation (both directions)
  - events_produced=[EventDefinition(...)] — planner declares + auto-registers response schema
  - @planner.on_event(event, topic=ACTION_RESULTS) — receive worker result
  - ctx.bus.respond(...) — reply to client
"""

import logging
import os
from typing import Any, Dict

from dotenv import load_dotenv

from soorma.ai.choreography import ChoreographyPlanner
from soorma.agents.planner import GoalContext
from soorma.context import PlatformContext
from soorma_common import EventDefinition
from soorma_common.events import EventEnvelope, EventTopic

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Event definitions
# ---------------------------------------------------------------------------

# Planner owns the client contract: it declares and registers the response
# schema for research.completed.  The client can discover this schema from
# the Registry just as the planner discovers the worker's schema.
RESEARCH_COMPLETED_EVENT = EventDefinition(
    event_name="research.completed",
    topic="action-results",
    description="Normalized research results returned to the client by the planner",
    payload_schema_name="research_result_v1",
    payload_schema={
        "type": "object",
        "properties": {
            "topic": {
                "type": "string",
                "description": "The research topic that was investigated",
            },
            "summary": {
                "type": "string",
                "description": "A brief summary of the key findings",
            },
            "findings": {
                "type": "array",
                "description": "List of individual research findings",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "summary": {"type": "string"},
                        "source": {"type": "string"},
                    },
                    "required": ["title", "summary", "source"],
                },
            },
            "result_count": {
                "type": "integer",
                "description": "Total number of findings returned",
            },
        },
        "required": ["topic", "findings", "result_count"],
    },
)

# ---------------------------------------------------------------------------
# Planner declaration
# ---------------------------------------------------------------------------

planner = ChoreographyPlanner(
    name="research-planner",
    reasoning_model=os.environ.get("LLM_MODEL", "gpt-4o-mini"),
    # Declaring RESEARCH_COMPLETED_EVENT here causes the SDK to auto-register
    # both the event definition and its inline schema at startup — the same
    # mechanism used by the worker for its consumed event.
    events_produced=[RESEARCH_COMPLETED_EVENT],
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
    """Receive the worker's result, normalize it via schema + LLM, and deliver to the client.

    Mirrors the inbound path exactly:
      - Inbound  (goal → worker):    discover worker schema → generate_payload() → dispatch
      - Outbound (worker → client):  look up client response schema → generate_payload() → respond

    This ensures the planner never hardcodes the client response shape.  Any
    change to research_result_v1 schema is automatically picked up here
    without touching this handler.

    Args:
        event: EventEnvelope from the worker (via task.complete()).
               data["result"] contains the raw findings.
        context: PlatformContext for registry and bus access.
    """
    data = event.data or {}
    # task.complete() wraps the caller's dict under "result"
    raw_result: Dict[str, Any] = data.get("result", {})
    result_count = raw_result.get("result_count", len(raw_result.get("findings", [])))
    print(f"\n[planner] Worker result received: {result_count} finding(s)")

    # Look up the schema the client expects for research.completed.
    # The planner registered this schema at startup (events_produced above),
    # so it is always available in the Registry.
    event_def = await context.registry.get_event(RESEARCH_COMPLETED_EVENT.event_name)
    if event_def and event_def.payload_schema_name:
        schema = await context.registry.get_schema(event_def.payload_schema_name)
        # Use LLM to produce a response that conforms to research_result_v1.
        # Pass the raw worker result as context so the LLM can extract and
        # reformat it — adding a summary field, normalizing finding structure, etc.
        import json
        context_str = (
            f"Raw research result from worker (reformat this into the required schema):\n"
            f"{json.dumps(raw_result, indent=2)}"
        )
        response_payload = await planner.generate_payload(schema=schema, context=context_str)
        print(f"[planner] LLM normalized response to schema: {event_def.payload_schema_name}")
    else:
        # Schema not available — pass through raw result as fallback
        logger.warning("research.completed schema not found in registry; using raw worker result")
        response_payload = raw_result

    await context.bus.respond(
        event_type=RESEARCH_COMPLETED_EVENT.event_name,
        data=response_payload,
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
