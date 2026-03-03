"""Unit tests for NATSClient (RED phase).

These tests assert REAL expected behavior of NATSClient.
They MUST fail with NotImplementedError in STUB phase and PASS in GREEN phase.

Constitution rule: Do NOT test for the stub (no pytest.raises(NotImplementedError)).
Write tests asserting real behavior; let the stub raise NotImplementedError naturally.

RED Phase verification:
- Run: pytest tests/test_nats_client.py -v
- Expected:
  - Init / subject-mapping tests: PASS (no async calls)
  - Async behavior tests: FAIL with NotImplementedError from stub
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from soorma_nats import NATSClient, NATSConnectionError, NATSSubscriptionError


class TestNATSClientInit:
    """Test NATSClient construction.

    These tests assert real __init__ behavior — pass in both STUB and GREEN phases.
    """

    def test_default_url(self):
        """NATSClient defaults to localhost:4222."""
        client = NATSClient()
        assert client._url == "nats://localhost:4222"

    def test_custom_url(self):
        """NATSClient accepts custom URL."""
        client = NATSClient(url="nats://myserver:5222")
        assert client._url == "nats://myserver:5222"

    def test_is_connected_false_before_connect(self):
        """is_connected returns False before connect() is called."""
        client = NATSClient()
        assert client.is_connected is False

    def test_default_reconnect_settings(self):
        """Default reconnect settings are as specified."""
        client = NATSClient()
        assert client._reconnect_time_wait == 2
        assert client._max_reconnect_attempts == -1

    def test_custom_reconnect_settings(self):
        """Custom reconnect settings are stored."""
        client = NATSClient(reconnect_time_wait=5, max_reconnect_attempts=3)
        assert client._reconnect_time_wait == 5
        assert client._max_reconnect_attempts == 3


class TestSubjectMapping:
    """Test topic <-> subject conversion helpers.

    These test real helper behavior — pass in both STUB and GREEN phases.
    """

    def test_topic_to_subject_basic(self):
        """action-requests maps to soorma.events.action-requests."""
        client = NATSClient()
        assert client._topic_to_subject("action-requests") == "soorma.events.action-requests"

    def test_topic_to_subject_already_prefixed(self):
        """Already-prefixed subjects are returned as-is."""
        client = NATSClient()
        subject = "soorma.events.action-requests"
        assert client._topic_to_subject(subject) == subject

    def test_subject_to_topic_basic(self):
        """soorma.events.action-results maps back to action-results."""
        client = NATSClient()
        assert client._subject_to_topic("soorma.events.action-results") == "action-results"

    def test_subject_to_topic_round_trip(self):
        """topic -> subject -> topic round-trip is identity."""
        client = NATSClient()
        for topic in ["action-requests", "action-results", "system-events"]:
            subject = client._topic_to_subject(topic)
            assert client._subject_to_topic(subject) == topic


class TestNATSClientConnect:
    """Test connect() real behavior.

    RED: these tests call connect() directly and FAIL with NotImplementedError from stub.
    GREEN: these tests PASS because connect() calls nats.connect() successfully.
    """

    @pytest.mark.asyncio
    async def test_connect_with_mock_nats_sets_is_connected(self):
        """connect() uses nats.connect() and sets internal client; is_connected becomes True.

        GREEN phase: after connect(), is_connected is True.
        STUB phase: FAILS with NotImplementedError before nats.connect() is called.
        """
        mock_nc = MagicMock()
        mock_nc.is_connected = True
        mock_nc.connected_url = "nats://localhost:4222"

        client = NATSClient()
        with patch("soorma_nats.client.nats") as mock_nats_mod:
            mock_nats_mod.connect = AsyncMock(return_value=mock_nc)
            # GREEN: connects and sets is_connected True
            # STUB: raises NotImplementedError here
            await client.connect()

        assert client.is_connected is True

    @pytest.mark.asyncio
    async def test_connect_raises_connection_error_on_failure(self):
        """connect() raises NATSConnectionError when nats.connect() fails.

        GREEN phase: NATSConnectionError is raised wrapping nats exception.
        STUB phase: FAILS with NotImplementedError (not NATSConnectionError).
        """
        client = NATSClient(url="nats://bad-host:4222")
        with patch("soorma_nats.client.nats") as mock_nats_mod:
            mock_nats_mod.connect = AsyncMock(side_effect=Exception("connection refused"))
            with pytest.raises(NATSConnectionError):
                await client.connect()

    @pytest.mark.asyncio
    async def test_connect_idempotent_when_already_connected(self):
        """connect() does nothing if already connected (no-op guard).

        GREEN phase: second connect() does not call nats.connect() again.
        STUB phase: FAILS with NotImplementedError on first connect().
        """
        mock_nc = MagicMock()
        mock_nc.is_connected = True
        mock_nc.connected_url = "nats://localhost:4222"

        client = NATSClient()
        with patch("soorma_nats.client.nats") as mock_nats_mod:
            mock_nats_mod.connect = AsyncMock(return_value=mock_nc)
            await client.connect()
            await client.connect()  # second call should be no-op
            assert mock_nats_mod.connect.call_count == 1


class TestNATSClientSubscribe:
    """Test subscribe() real behavior.

    RED: tests FAIL with NotImplementedError from stub.
    GREEN: tests PASS because subscribe() calls nats client properly.
    """

    @pytest.mark.asyncio
    async def test_subscribe_before_connect_raises_connection_error(self):
        """subscribe() raises NATSConnectionError when not connected.

        GREEN phase: raises NATSConnectionError with "Not connected" message.
        STUB phase: FAILS with NotImplementedError (different exception — RED fail).
        """
        client = NATSClient()
        # is_connected is False (stub returns False)
        with pytest.raises(NATSConnectionError):
            await client.subscribe(["action-requests"], callback=AsyncMock())

    @pytest.mark.asyncio
    async def test_subscribe_returns_subscription_id_string(self):
        """subscribe() returns a non-empty string subscription ID.

        GREEN phase: returns UUID string.
        STUB phase: FAILS with NotImplementedError.
        """
        mock_nc = MagicMock()
        mock_nc.is_connected = True
        mock_nc.connected_url = "nats://localhost:4222"
        mock_nc.subscribe = AsyncMock(return_value=MagicMock())

        client = NATSClient()
        with patch("soorma_nats.client.nats") as mock_nats_mod:
            mock_nats_mod.connect = AsyncMock(return_value=mock_nc)
            await client.connect()
            sub_id = await client.subscribe(["action-requests"], callback=AsyncMock())

        assert isinstance(sub_id, str)
        assert len(sub_id) > 0

    @pytest.mark.asyncio
    async def test_subscribe_calls_nats_subscribe_for_each_topic(self):
        """subscribe() calls nats client.subscribe() once per topic.

        GREEN phase: nats subscribe called N times for N topics.
        STUB phase: FAILS with NotImplementedError.
        """
        mock_nc = MagicMock()
        mock_nc.is_connected = True
        mock_nc.connected_url = "nats://localhost:4222"
        mock_nc.subscribe = AsyncMock(return_value=MagicMock())

        topics = ["action-requests", "action-results", "system-events"]
        client = NATSClient()
        with patch("soorma_nats.client.nats") as mock_nats_mod:
            mock_nats_mod.connect = AsyncMock(return_value=mock_nc)
            await client.connect()
            await client.subscribe(topics, callback=AsyncMock())

        assert mock_nc.subscribe.call_count == len(topics)

    @pytest.mark.asyncio
    async def test_subscribe_uses_queue_group(self):
        """subscribe() passes queue_group to nats client.subscribe().

        GREEN phase: queue parameter is forwarded to nats-py.
        STUB phase: FAILS with NotImplementedError.
        """
        mock_nc = MagicMock()
        mock_nc.is_connected = True
        mock_nc.connected_url = "nats://localhost:4222"
        mock_nc.subscribe = AsyncMock(return_value=MagicMock())

        client = NATSClient()
        with patch("soorma_nats.client.nats") as mock_nats_mod:
            mock_nats_mod.connect = AsyncMock(return_value=mock_nc)
            await client.connect()
            await client.subscribe(
                ["action-requests"],
                callback=AsyncMock(),
                queue_group="tracker-service",
            )

        # Verify queue group was passed as 'queue' kwarg to nats subscribe
        call_kwargs = mock_nc.subscribe.call_args.kwargs
        assert call_kwargs.get("queue") == "tracker-service"

    @pytest.mark.asyncio
    async def test_subscribe_uses_soorma_events_prefix_in_subjects(self):
        """subscribe() subscribes to soorma.events.<topic> subjects.

        GREEN phase: nats client receives fully qualified subjects.
        STUB phase: FAILS with NotImplementedError.
        """
        mock_nc = MagicMock()
        mock_nc.is_connected = True
        mock_nc.connected_url = "nats://localhost:4222"
        mock_nc.subscribe = AsyncMock(return_value=MagicMock())

        client = NATSClient()
        with patch("soorma_nats.client.nats") as mock_nats_mod:
            mock_nats_mod.connect = AsyncMock(return_value=mock_nc)
            await client.connect()
            await client.subscribe(["action-requests"], callback=AsyncMock())

        subscribed_subject = mock_nc.subscribe.call_args.args[0]
        assert subscribed_subject == "soorma.events.action-requests"


class TestNATSClientDisconnect:
    """Test disconnect() real behavior."""

    @pytest.mark.asyncio
    async def test_disconnect_drains_and_clears_client(self):
        """disconnect() drains the nats connection and clears internal client.

        GREEN phase: client._client is None after disconnect(); is_connected is False.
        STUB phase: FAILS with NotImplementedError.
        """
        mock_nc = MagicMock()
        mock_nc.is_connected = True
        mock_nc.connected_url = "nats://localhost:4222"
        mock_nc.subscribe = AsyncMock(return_value=MagicMock())
        mock_nc.drain = AsyncMock()

        client = NATSClient()
        with patch("soorma_nats.client.nats") as mock_nats_mod:
            mock_nats_mod.connect = AsyncMock(return_value=mock_nc)
            await client.connect()
            await client.disconnect()

        mock_nc.drain.assert_awaited_once()
        assert client._client is None

    @pytest.mark.asyncio
    async def test_disconnect_safe_when_not_connected(self):
        """disconnect() does not raise when called before connect().

        GREEN phase: no-op, no exception raised.
        STUB phase: FAILS with NotImplementedError.
        """
        client = NATSClient()
        # Should complete without error in GREEN phase
        await client.disconnect()  # STUB: raises NotImplementedError
