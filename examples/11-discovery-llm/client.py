"""
Client — Example 11: LLM-Based Dynamic Discovery.

Sends a research goal to the planner and waits for the response.
The planner owns both ends of the client contract:
  - receives research.goal from the client
  - discovers the worker, generates the payload, dispatches internally
  - normalizes the worker result and publishes research.completed back here

The client has no knowledge of the worker, its schema, or the internal
research.worker.completed event — it only speaks the planner's API.

Usage:
    python client.py "Latest advances in quantum computing"
    python client.py  # uses default topic
"""

import asyncio
import sys
from uuid import uuid4

from soorma import EventClient
from soorma_common.events import EventEnvelope, EventTopic


# Authentication context — in production this comes from user auth
TENANT_ID = "00000000-0000-0000-0000-000000000000"
USER_ID = "00000000-0000-0000-0000-000000000001"

DEFAULT_TOPIC = "Latest advances in quantum computing, 2025"
TIMEOUT_SECONDS = 30.0


async def send_research_goal(description: str) -> None:
    """Send a research goal event and wait for the planner's response.

    Args:
        description: Natural-language research objective sent to the planner.
    """
    client = EventClient(
        agent_id="discovery-llm-client",
        source="discovery-llm-client",
    )

    print("=" * 60)
    print("  Example 11 — LLM-Based Dynamic Discovery Client")
    print("=" * 60)
    print()

    correlation_id = str(uuid4())

    response_received = asyncio.Event()
    response_data: dict = {}

    @client.on_event("research.completed", topic=EventTopic.ACTION_RESULTS)
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

    # Publish the goal — planner discovers the worker and dispatches dynamically
    await client.publish(
        event_type="research.goal",
        topic=EventTopic.ACTION_REQUESTS,
        data={"description": description},
        correlation_id=correlation_id,
        response_event="research.completed",
        response_topic=EventTopic.ACTION_RESULTS,
        tenant_id=TENANT_ID,
        user_id=USER_ID,
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
