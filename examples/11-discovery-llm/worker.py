"""
Research Worker — Example 11: LLM-Based Dynamic Discovery.

Demonstrates the key pattern: inline JSON Schema declared on AgentCapability so
the SDK auto-registers it with the Registry at startup.  The worker never calls
ctx.registry.register_schema() explicitly — that is the SDK's responsibility
(implemented in agents/base._auto_register_inline_schemas, T0 Phase 5).

Key SDK usage:
  - AgentCapability with payload_schema_name + payload_schema (inline body)
  - Worker.on_task() handler — receives TaskContext and PlatformContext
  - task.complete() to publish the response (auto-propagates all metadata)
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

    Extracts the topic from the validated payload, simulates web research,
    Extracts the topic from the validated payload, simulates web research,
    and publishes findings back via task.complete() — which auto-propagates
    tenant_id, user_id, plan_id, correlation_id and cleans up any persisted state.

    Args:
        task: TaskContext containing the research payload
              (validated against research_request_v1 schema).
        context: PlatformContext for service access (unused directly;
                 task.complete() uses it internally).
    """
    topic: str = task.data.get("topic", "")
    max_results: int = int(task.data.get("max_results", 5))
    depth: str = task.data.get("depth", "standard")

    print(f"\n[worker]  ▶ Received: research.requested")
    print(f"[worker]  Task ID: {task.task_id}")
    print(f"[worker]  Topic: {topic!r}  depth={depth}  max_results={max_results}")

    # Simulate research — replace with real retrieval/search logic as needed
    findings: List[Dict[str, Any]] = _simulate_research(topic, max_results)

    print(f"[worker]  ✓ Research complete — {len(findings)} finding(s)")

    # task.complete() auto-propagates tenant_id, user_id, plan_id, correlation_id
    # and cleans up any persisted TaskContext from memory.
    await task.complete({
        "topic": topic,
        "findings": findings,
        "result_count": len(findings),
    })


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _simulate_research(topic: str, max_results: int) -> List[Dict[str, Any]]:
    """Return mock research findings for demonstration purposes.

    In a real implementation this would call a search API, web scraper,
    or knowledge base.  The return structure is intentionally simple so
    the planner can summarise it without additional context.

    Args:
        topic: Research topic.
        max_results: Maximum number of findings to return.

    Returns:
        List of finding dicts with 'title', 'summary', and 'source' keys.
    """
    templates = [
        "Overview of {topic}: key concepts and recent developments",
        "Expert analysis: {topic} in 2025",
        "{topic} — practical applications and case studies",
        "Challenges and opportunities in {topic}",
        "Future directions for {topic}: what researchers are saying",
        "Comparison of approaches to {topic}",
        "Industry impact of {topic}",
    ]
    return [
        {
            "title": templates[i % len(templates)].format(topic=topic),
            "summary": (
                f"Simulated finding {i + 1} about {topic!r}. "
                "Replace with real search results."
            ),
            "source": f"https://example.com/research/{i + 1}",
        }
        for i in range(min(max_results, len(templates)))
    ]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    worker.run()
