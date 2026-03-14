"""
Internal Research Agent — Example 13: A2A Gateway Interoperability.

A standard Soorma Worker that handles "research.requested" events routed
by the A2A gateway.  It does not know anything about the A2A protocol —
it simply processes Soorma events using the standard Worker + TaskContext
pattern.

SDK patterns shown:
  - Worker with AgentCapability and inline payload_schema
  - @worker.on_task() handler receiving TaskContext + PlatformContext
  - task.complete() — publishes result to task.response_event (set by gateway)
  - @worker.on_startup() — logs readiness message after Registry registration
"""

import asyncio
import logging
import os

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
    description="A research request from an external A2A client via the gateway",
    payload_schema_name="a2a_research_request_v1",
    # Inline JSON schema — SDK auto-registers this at startup via _register_with_registry()
    payload_schema={
        "type": "object",
        "properties": {
            "input": {
                "type": "string",
                "description": "The research topic or question from the A2A client",
            },
        },
        "required": ["input"],
    },
)

RESEARCH_COMPLETED_EVENT = EventDefinition(
    event_name="research.completed",
    topic="action-results",
    description="Research summary produced by the internal agent",
    payload_schema_name="a2a_research_result_v1",
    payload_schema={
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "Brief summary of the research findings",
            },
            "topic": {
                "type": "string",
                "description": "The original research topic",
            },
            "sources_consulted": {
                "type": "integer",
                "description": "Number of sources consulted (simulated)",
            },
        },
        "required": ["summary", "topic"],
    },
)

# ---------------------------------------------------------------------------
# Worker definition
# ---------------------------------------------------------------------------

worker = Worker(
    # Name must match what gateway_service.py queries: registry.query_agents(name="research-agent")
    name="research-agent",
    description=(
        "Performs structured research in response to queries forwarded by the A2A gateway. "
        "Accepts research topics and returns a summary with simulated findings."
    ),
    capabilities=[
        AgentCapability(
            task_name="web_research",
            description=(
                "Research a topic and return a concise summary. "
                "Accepts any research query as plain text."
            ),
            consumed_event=RESEARCH_REQUESTED_EVENT,
            produced_events=[RESEARCH_COMPLETED_EVENT],
        )
    ],
)

# ---------------------------------------------------------------------------
# Task handler
# ---------------------------------------------------------------------------


@worker.on_task("research.requested")
async def handle_research(task: TaskContext, context: PlatformContext) -> None:
    """Handle an incoming research request forwarded by the A2A gateway.

    Performs simulated research (no live web access in this example) and
    publishes the result back to the gateway via task.complete().  The SDK
    automatically routes the result to task.response_event which the gateway
    is listening on.

    Args:
        task: TaskContext carrying the research request payload.
        context: PlatformContext for service access (unused in this example).
    """
    _ = context  # Unused — no external service calls in this example

    research_topic: str = task.data.get("input", "")
    logger.info("[research-agent] ▶ Research requested: %r", research_topic)
    logger.info("[research-agent]   task_id=%s", task.task_id)
    logger.info("[research-agent]   correlation_id=%s", task.correlation_id)
    logger.info("[research-agent]   response_event=%s", task.response_event)

    if not research_topic:
        await task.complete(
            {"summary": "No research topic provided.", "topic": "", "sources_consulted": 0}
        )
        return

    # Simulate research work — replace with real LLM / web search in production
    await asyncio.sleep(0.5)
    summary = _simulate_research(research_topic)

    result = {
        "summary": summary,
        "topic": research_topic,
        "sources_consulted": 3,
    }

    logger.info("[research-agent] ✓ Research complete — publishing result")
    # task.complete() publishes to task.response_event on the action-results topic.
    # The gateway is waiting on that exact event (keyed by correlation_id = task.id).
    await task.complete(result)


def _simulate_research(topic: str) -> str:
    """Return a deterministic simulated research summary for the given topic.

    In a production implementation this would call an LLM or a web-search API.

    Args:
        topic: The research topic string from the A2A client.

    Returns:
        A brief plain-text summary.
    """
    topic_lower = topic.lower()
    if "quantum" in topic_lower:
        return (
            "Quantum computing leverages superposition and entanglement to perform "
            "computations exponentially faster than classical computers for certain "
            "problems, including cryptography and optimisation."
        )
    if "machine learning" in topic_lower or "ml" in topic_lower:
        return (
            "Machine learning is a subset of AI that enables systems to learn from "
            "data and improve performance without explicit programming. Core paradigms "
            "include supervised, unsupervised, and reinforcement learning."
        )
    if "blockchain" in topic_lower:
        return (
            "Blockchain is a distributed ledger technology that records transactions "
            "in an immutable, cryptographically linked chain. It underpins "
            "cryptocurrencies and has supply-chain and identity-management applications."
        )
    # Generic response for any other topic
    return (
        f"Research on '{topic}' indicates this is an active area of development "
        "with multiple competing approaches. Key findings depend on the specific "
        "application domain and available resources."
    )


# ---------------------------------------------------------------------------
# Startup hook
# ---------------------------------------------------------------------------


@worker.on_startup
async def on_startup() -> None:
    """Log agent readiness after Registry registration and NATS subscription.

    The SDK calls this hook after _register_with_registry() and event-bus
    subscription succeed — at this point it is safe to start receiving tasks.
    """
    logger.info("[research-agent] ✓ research-agent started")
    logger.info("[research-agent]   Listening for: research.requested")
    logger.info("[research-agent]   Publishes to:  research.completed (via task.complete)")
    logger.info("[research-agent]   Gateway can now start routing A2A tasks.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    worker.run()
