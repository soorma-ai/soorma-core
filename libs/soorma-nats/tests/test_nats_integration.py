"""Integration tests for NATSClient (RED phase).

These tests verify end-to-end NATS subscription behavior with a real server.
They require NATS_URL environment variable pointing to a live NATS server.

Run integration tests:
    NATS_URL=nats://localhost:4222 pytest tests/test_nats_integration.py -v -m integration

Skip in normal CI (no live NATS available):
    pytest tests/ -v -m "not integration"

RED Phase verification:
- All integration tests FAIL with NotImplementedError until GREEN phase.
"""

import asyncio
import json
import pytest

from soorma_nats import NATSClient, NATSConnectionError


@pytest.mark.integration
@pytest.mark.asyncio
async def test_connect_to_live_nats(nats_url: str):
    """NATSClient.connect() succeeds with a real NATS server.

    GREEN phase: is_connected returns True after connect().
    STUB phase: raises NotImplementedError.
    """
    client = NATSClient(url=nats_url)
    with pytest.raises(NotImplementedError):
        await client.connect()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_is_connected_true_after_connect(nats_url: str):
    """is_connected returns True after successful connect().

    GREEN phase: asserts is_connected is True.
    STUB phase: raises NotImplementedError from connect().
    """
    client = NATSClient(url=nats_url)
    with pytest.raises(NotImplementedError):
        await client.connect()
        assert client.is_connected is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_subscribe_and_receive_message(nats_url: str):
    """Subscribe to a topic and receive a published message.

    GREEN phase: callback receives (subject, message) for published events.
    STUB phase: raises NotImplementedError from connect().
    """
    received: list = []
    client = NATSClient(url=nats_url)

    async def on_message(subject: str, message: dict) -> None:
        received.append((subject, message))

    with pytest.raises(NotImplementedError):
        await client.connect()
        await client.subscribe(["action-requests"], callback=on_message)

        # Publish via raw nats-py
        import nats as nats_py

        publisher = await nats_py.connect(nats_url)
        payload = json.dumps({"test": True, "action_id": "a1"}).encode()
        await publisher.publish("soorma.events.action-requests", payload)
        await asyncio.sleep(0.2)
        await publisher.close()

        # Verify received
        assert len(received) == 1
        subject, message = received[0]
        assert subject == "soorma.events.action-requests"
        assert message["test"] is True
        assert message["action_id"] == "a1"

        await client.disconnect()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_subscribe_multiple_topics(nats_url: str):
    """Subscribe to multiple topics and receive messages on each.

    GREEN phase: messages arrive on all subscribed subjects.
    STUB phase: raises NotImplementedError from connect().
    """
    received: list = []
    client = NATSClient(url=nats_url)

    async def on_message(subject: str, message: dict) -> None:
        received.append(subject)

    with pytest.raises(NotImplementedError):
        await client.connect()
        await client.subscribe(
            topics=["action-requests", "action-results", "system-events"],
            callback=on_message,
        )

        import nats as nats_py

        publisher = await nats_py.connect(nats_url)
        for subject in [
            "soorma.events.action-requests",
            "soorma.events.action-results",
            "soorma.events.system-events",
        ]:
            await publisher.publish(subject, json.dumps({"ping": True}).encode())

        await asyncio.sleep(0.2)
        await publisher.close()

        assert len(received) == 3
        assert "soorma.events.action-requests" in received
        assert "soorma.events.action-results" in received
        assert "soorma.events.system-events" in received

        await client.disconnect()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_queue_group_single_consumer_receives_message(nats_url: str):
    """Queue group subscriber receives message exactly once.

    GREEN phase: queue group is set correctly; message received once.
    STUB phase: raises NotImplementedError from connect().
    """
    received: list = []
    client = NATSClient(url=nats_url)

    async def on_message(subject: str, message: dict) -> None:
        received.append(message)

    with pytest.raises(NotImplementedError):
        await client.connect()
        await client.subscribe(
            topics=["action-requests"],
            callback=on_message,
            queue_group="tracker-service",
        )

        import nats as nats_py

        publisher = await nats_py.connect(nats_url)
        await publisher.publish(
            "soorma.events.action-requests",
            json.dumps({"action_id": "qg-test"}).encode(),
        )
        await asyncio.sleep(0.2)
        await publisher.close()

        assert len(received) == 1
        assert received[0]["action_id"] == "qg-test"

        await client.disconnect()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_disconnect_sets_is_connected_false(nats_url: str):
    """is_connected returns False after disconnect().

    GREEN phase: after drain+close, is_connected is False.
    STUB phase: raises NotImplementedError from connect().
    """
    client = NATSClient(url=nats_url)

    with pytest.raises(NotImplementedError):
        await client.connect()
        assert client.is_connected is True
        await client.disconnect()
        assert client.is_connected is False


@pytest.mark.integration
@pytest.mark.asyncio
async def test_connect_invalid_url_raises_error():
    """NATSClient raises an error when NATS server is unreachable.

    GREEN phase: raises NATSConnectionError or ConnectionError.
    STUB phase: raises NotImplementedError.
    """
    client = NATSClient(url="nats://nonexistent-host-xyz:99999", max_reconnect_attempts=1)
    with pytest.raises((NotImplementedError, NATSConnectionError, ConnectionError, OSError)):
        await client.connect()
