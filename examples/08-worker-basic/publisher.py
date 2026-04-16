#!/usr/bin/env python3
"""
Event Publisher (action request).

Sends an action request and waits for the worker's async completion.
"""

import asyncio
import sys
from pathlib import Path
from typing import Any, Dict

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from soorma import EventClient
from soorma_common.events import EventTopic, EventEnvelope

from examples.shared.auth import build_example_token_provider


EXAMPLE_NAME = "08-worker-basic"


async def publish_order_request() -> None:
    token_provider = build_example_token_provider(EXAMPLE_NAME, __file__)
    await token_provider.get_token()
    tenant_id = await token_provider.get_platform_tenant_id()
    user_id = await token_provider.get_bootstrap_admin_principal_id()
    client = EventClient(
        agent_id="order-service",
        source="order-service",
        auth_token_provider=token_provider,
    )

    print("=" * 60)
    print("  Event Publisher - Order Request")
    print("=" * 60)
    print()

    response_event = asyncio.Event()
    response_payload: Dict[str, Any] = {}

    @client.on_event("order.process.completed")
    async def handle_response(event: EventEnvelope) -> None:
        response_payload.update(event.data or {})
        response_event.set()

    await client.connect(topics=[EventTopic.ACTION_RESULTS])

    print("📨 Sending order.process.requested...")
    await client.publish(
        event_type="order.process.requested",
        topic=EventTopic.ACTION_REQUESTS,
        response_event="order.process.completed",
        data={
            "order_id": "ORD-001",
            "customer": "Alice",
            "items": ["laptop", "mouse"],
            "total": 1500.00,
        },
        tenant_id=tenant_id,
        user_id=user_id,
    )

    try:
        await asyncio.wait_for(response_event.wait(), timeout=10)
        print("\n✅ Order completed:")
        print(response_payload)
    except asyncio.TimeoutError:
        print("\n⏳ Timed out waiting for order completion.")
    finally:
        await client.disconnect()


async def main() -> None:
    await publish_order_request()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Interrupted\n")
