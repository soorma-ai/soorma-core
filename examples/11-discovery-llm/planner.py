"""
Research Planner — Example 11: LLM-Based Dynamic Discovery.

Demonstrates the full LLM-driven dynamic discovery loop:
  1. ctx.registry.discover()        — find agents with matching capabilities
  2. ctx.registry.get_schema()      — fetch the consumed schema from Registry
  3. ctx.ai.generate_payload()      — LLM generates a conforming JSON payload
                                       (SDK builds the prompt — planner never
                                       hand-crafts prompt strings)
  4. ctx.bus.request()              — publish with explicit response_event
                                       (Event Choreography §3 pattern)

Key SDK usage:
  - ChoreographyPlanner with on_goal() handler
  - ctx.registry.discover(requirements=..., include_schemas=True)
  - ctx.registry.get_schema(schema_name)
  - ctx.ai.generate_payload(schema=..., context=...)
  - ctx.bus.request(event_type=..., payload=..., response_event=...)
"""

import logging
import os

from dotenv import load_dotenv

from soorma.ai.choreography import ChoreographyPlanner
from soorma.agents.planner import GoalContext
from soorma.context import PlatformContext

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
# Goal handler
# ---------------------------------------------------------------------------

@planner.on_goal("research.goal")
async def handle_research_goal(goal: GoalContext, context: PlatformContext) -> None:
    """Discover a research worker and dispatch a research request.

    Full discovery loop:
      1. Discover agents capable of 'web_research'.
      2. Fetch the consumed event schema from the Registry.
      3. Use the LLM to generate a conforming payload from the goal description.
      4. Publish the request with an explicit response_event.

    Args:
        goal: GoalContext containing the research objective.
        context: PlatformContext for Registry, AI, and bus access.
    """
    description: str = goal.data.get("description", "")
    print(f"\n[planner] Goal received: research.goal")
    print(f"[planner] Description: {description!r}")

    # Step 1 — Dynamic discovery: find agents by capability, not by name.
    # The Registry returns agents whose AgentCapability.task_name matches any
    # entry in requirements.  include_schemas=True attaches schema payloads to
    # avoid a separate round-trip in most cases.
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

    # Pick the first matching agent (production code would apply ranking logic)
    agent = agents[0]

    # Step 2 — Look up the consumed event definition from the event registry.
    # The events table is the authoritative source for event_name → payload_schema_name.
    # The SDK auto-registers these EventDefinitions at worker startup, so the
    # planner never needs to know about schema names in advance.
    consumed_event_name = agent.capabilities[0].consumed_event.event_name
    event_def = await context.registry.get_event(consumed_event_name)
    if not event_def or not event_def.payload_schema_name:
        raise RuntimeError(
            f"Event '{consumed_event_name}' has no schema registered. "
            "Check that the worker declared payload_schema_name on its capability."
        )
    schema = await context.registry.get_schema(event_def.payload_schema_name)
    print(f"[planner] Schema fetched: {schema.schema_name}")

    # Step 3 — Ask the LLM to generate a payload that conforms to the schema.
    # The SDK builds the prompt internally from schema.json_schema and context;
    # the planner never hand-crafts prompt strings.
    payload = await context.ai.generate_payload(
        schema=schema,
        context=description,
    )
    print(f"[planner] LLM generated payload: {payload}")

    # Step 4 — Publish the research request with an explicit response_event.
    # Using an explicit response_event is mandatory per §3 Event Choreography.
    consumed_event_name = agent.capabilities[0].consumed_event.event_name
    response_event = f"research.completed.{goal.correlation_id}"
    print(f"[planner] Publishing: {consumed_event_name} → awaiting {response_event}")

    response = await context.bus.request(
        event_type=consumed_event_name,
        payload=payload,
        response_event=response_event,
        timeout=30.0,
    )
    print(f"[planner] ✓ Response received on {response_event}")
    print(f"[planner] Findings: {response.data.get('result_count', '?')} result(s)")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    planner.run()
