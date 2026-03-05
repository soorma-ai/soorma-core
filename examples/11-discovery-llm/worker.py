"""
Research Worker — Example 11: LLM-Based Dynamic Discovery.

Demonstrates the key pattern: inline JSON Schema declared on AgentCapability so
the SDK auto-registers it with the Registry at startup.  The worker never calls
ctx.registry.register_schema() explicitly — that is the SDK's responsibility
(implemented in agents/base._auto_register_inline_schemas, T0 Phase 5).

Key SDK usage:
  - AgentCapability with payload_schema_name + payload_schema (inline body)
  - Worker.on_task() handler — receives TaskContext and PlatformContext
  - ctx.bus.complete() to publish the response back to the planner
"""

import asyncio
import logging
import os
from typing import Any, Dict, List

from dotenv import load_dotenv

from soorma import Worker
from soorma.context import PlatformContext
from soorma.task_context import TaskContext
from soorma_common import AgentCapability, EventDefinition

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Event definitions
# ---------------------------------------------------------------------------

RESEARCH_REQUESTED_EVENT = EventDefinition(
    event_name="research.requested",
    topic="action-requests",
    description="Request structured web research on a topic",
    # payload_schema_name identifies the schema in the Registry.
    # payload_schema (inline body) triggers auto-registration via the SDK —
    # no separate schema_registration.py script is needed.
    payload_schema_name="research_request_v1",
    payload_schema={
        "type": "object",
        "properties": {
            "topic": {
                "type": "string",
                "description": "Research topic or question",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return",
                "default": 5,
            },
            "depth": {
                "type": "string",
                "enum": ["shallow", "standard", "deep"],
                "description": "Research depth",
                "default": "standard",
            },
        },
        "required": ["topic"],
    },
)

RESEARCH_COMPLETED_EVENT = EventDefinition(
    event_name="research.completed",
    topic="action-responses",
    description="Research results produced by research-worker",
)

# ---------------------------------------------------------------------------
# Worker declaration
# ---------------------------------------------------------------------------

worker = Worker(
    name="research-worker",
    description="Performs structured web research and returns summarised results",
    capabilities=[
        AgentCapability(
            task_name="web_research",
            description=(
                "Performs structured web research on a given topic and returns "
                "a list of summarised findings with sources"
            ),
            consumed_event=RESEARCH_REQUESTED_EVENT,
            produced_events=[RESEARCH_COMPLETED_EVENT],
        )
    ],
)


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------

@worker.on_task("research.requested")
async def handle_research(task: TaskContext, context: PlatformContext) -> None:
    """Handle an incoming research request.

    Args:
        task: TaskContext containing the research payload.
        context: PlatformContext for service access.
    """
    raise NotImplementedError(
        "Implement handle_research: extract topic from task.data, simulate "
        "or perform web research, call ctx.bus.complete() with findings"
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    worker.run()
