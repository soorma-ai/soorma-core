"""
Client — Example 11: LLM-Based Dynamic Discovery.

Sends a research goal to the planner and waits for the response.
The CLIENT owns the response schema contract:
  - declares RESEARCH_COMPLETED_EVENT with research_result_v1 inline schema
  - registers the schema with the Registry on connect (via events_consumed)
  - passes response_schema_name="research_result_v1" in the goal envelope

The planner reads response_schema_name from the goal metadata (auto-saved by
the SDK's on_goal decorator), looks up the schema, and calls generate_payload()
to produce a conforming response — without hardcoding any schema of its own.

The client has no knowledge of the worker, its schema, or the internal
research.worker.completed event.  It only speaks the planner's API.

The response schema is discoverable from the Registry:
  ctx.registry.get_event("research.completed") → payload_schema_name
  ctx.registry.get_schema("research_result_v1") → JSON Schema

Usage:
    python client.py "Latest advances in quantum computing"
    python client.py  # uses default topic
"""

import asyncio
import sys
from pathlib import Path
from uuid import uuid4

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from soorma import EventClient
from soorma_common import EventDefinition
from soorma_common.events import EventEnvelope, EventTopic

from examples.shared.auth import build_example_token_provider

EXAMPLE_NAME = "11-discovery-llm"

DEFAULT_TOPIC = "Latest advances in quantum computing, 2025"
TIMEOUT_SECONDS = 30.0

# ---------------------------------------------------------------------------
# Client-owned response schema
# ---------------------------------------------------------------------------
# The client declares the shape it expects for research.completed responses.
# Passing this in events_consumed causes EventClient.connect() to auto-register
# both the event definition and the inline schema with the Registry — the same
# mechanism workers use for their consumed events.

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


async def send_research_goal(description: str) -> None:
    """Send a research goal event and wait for the planner's response.

    Args:
        description: Natural-language research objective sent to the planner.
    """
    token_provider = build_example_token_provider(EXAMPLE_NAME, __file__)
    await token_provider.get_token()
    tenant_id = await token_provider.get_platform_tenant_id()
    user_id = await token_provider.get_bootstrap_admin_principal_id()
    client = EventClient(
        agent_id="discovery-llm-client",
        source="discovery-llm-client",
        # Register our response schema with the Registry on connect so the
        # planner can look it up when generating its response payload.
        events_consumed=[RESEARCH_COMPLETED_EVENT],
        auth_token_provider=token_provider,
    )

    print("=" * 60)
    print("  Example 11 — LLM-Based Dynamic Discovery Client")
    print("=" * 60)
    print()

    correlation_id = str(uuid4())

    response_received = asyncio.Event()
    response_data: dict = {}

    @client.on_event(RESEARCH_COMPLETED_EVENT.event_name, topic=EventTopic.ACTION_RESULTS)
    async def on_response(event: EventEnvelope) -> None:
        """Receive the normalized research result from the planner.

        Args:
            event: EventEnvelope published by the planner after it receives
                   and normalizes the worker's internal result.
        """
        # Filter by correlation_id — canonical event name shared by all responses
        if event.correlation_id != correlation_id:
            return
        response_data.update(event.data or {})
        response_received.set()

    await client.connect(topics=[EventTopic.ACTION_RESULTS])

    print(f"🎯 Research goal: {description!r}")
    print(f"   Correlation ID: {correlation_id}")
    print()

    # Publish the goal — planner discovers the worker and dispatches dynamically.
    # response_schema_name tells the planner which schema to use when generating
    # its response payload — it reads this from goal metadata, not from its own
    # events_produced declaration.
    await client.publish(
        event_type="research.goal",
        topic=EventTopic.ACTION_REQUESTS,
        data={"description": description},
        correlation_id=correlation_id,
        response_event=RESEARCH_COMPLETED_EVENT.event_name,
        response_topic=EventTopic.ACTION_RESULTS,
        response_schema_name=RESEARCH_COMPLETED_EVENT.payload_schema_name,
        tenant_id=tenant_id,
        user_id=user_id,
    )

    print(f"[client] Goal published — waiting for response (timeout: {TIMEOUT_SECONDS}s)...")

    try:
        await asyncio.wait_for(response_received.wait(), timeout=TIMEOUT_SECONDS)

        print("\n[client] ✅ Research complete!")
        topic_out = response_data.get("topic", "")
        findings = response_data.get("findings", [])
        print(f"[client] Topic:    {topic_out}")
        print(f"[client] Findings: {len(findings)} result(s)")
        for i, finding in enumerate(findings, 1):
            print(f"  {i}. {finding.get('title', '—')}")
            print(f"     {finding.get('source', '')}")

    except asyncio.TimeoutError:
        print(f"\n⚠️  Timeout after {TIMEOUT_SECONDS}s — no response received.")
        print("   Make sure worker.py and planner.py are running (./start.sh).")

    finally:
        await client.disconnect()


if __name__ == "__main__":
    topic = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TOPIC
    try:
        asyncio.run(send_research_goal(topic))
    except KeyboardInterrupt:
        print("\n🛑 Interrupted")
