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

    Args:
        goal: GoalContext containing the research objective.
        context: PlatformContext for Registry, AI, and bus access.
    """
    raise NotImplementedError(
        "Implement handle_research_goal:\n"
        "  1. agents = await context.registry.discover(requirements=['web_research'], include_schemas=True)\n"
        "  2. schema  = await context.registry.get_schema(agents[0].get_consumed_schemas()[0])\n"
        "  3. payload = await context.ai.generate_payload(schema=schema, context=goal.description)\n"
        "  4. await context.bus.request(\n"
        "         event_type=agents[0].capabilities[0].consumed_event.event_name,\n"
        "         payload=payload,\n"
        "         response_event=f'research.completed.{goal.correlation_id}',\n"
        "     )\n"
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    planner.run()
