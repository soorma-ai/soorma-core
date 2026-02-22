"""
Client for Choreography Example - Sends feedback analysis goal.

Demonstrates sending a request with response_event and waiting for the
orchestrated response from the planner.
"""

import asyncio
from uuid import uuid4

from soorma import EventClient
from soorma_common.events import EventEnvelope, EventTopic


TENANT_ID = "00000000-0000-0000-0000-000000000000"
USER_ID = "00000000-0000-0000-0000-000000000001"


async def main() -> None:
    """Send feedback analysis goal and wait for result."""
    client = EventClient(agent_id="feedback-client", source="feedback-client")
    
    response_event = asyncio.Event()
    response_payload = {}
    correlation_id = str(uuid4())

    @client.on_event("feedback.report.ready", topic=EventTopic.ACTION_RESULTS)
    async def handle_response(event: EventEnvelope) -> None:
        """Receive orchestrated report."""
        if event.correlation_id != correlation_id:
            return
        response_payload.update(event.data or {})
        response_event.set()

    await client.connect(topics=[EventTopic.ACTION_RESULTS])

    print("\n[client] Sending feedback analysis goal...")
    print(f"[client] Correlation ID: {correlation_id}")
    
    await client.publish(
        event_type="analyze.feedback",
        topic=EventTopic.ACTION_REQUESTS,
        response_event="feedback.report.ready",
        response_topic="action-results",
        correlation_id=correlation_id,
        data={"product": "Soorma Hub", "sample_size": 3},
        tenant_id=TENANT_ID,
        user_id=USER_ID,
    )

    print("[client] Waiting for response (timeout: 30s)...")
    await asyncio.wait_for(response_event.wait(), timeout=30.0)
    
    print("\n[client] Received report:")
    print(response_payload.get("result", response_payload))
    
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
