"""
Tests for EventClient schema auto-registration and response_schema_name support.

Covers new behaviour added alongside the client-owned response schema pattern:
  - events_consumed param stores EventDefinitions for registration on connect()
  - _register_event_definitions() calls RegistryClient.register_event() and
    RegistryClient.register_schema() for each EventDefinition with inline schema
  - 409 responses are treated as non-fatal (already registered)
  - ImportError would have been caught by these tests (regression guard)
  - EventClient.publish() passes response_schema_name through to envelope
  - BusClient.publish() passes response_schema_name through to EventClient
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from soorma.events import EventClient
from soorma.context import BusClient
from soorma_common import EventDefinition
from soorma_common.events import EventTopic


SAMPLE_EVENT_DEF = EventDefinition(
    event_name="research.completed",
    topic="action-results",
    description="Research result schema",
    payload_schema_name="research_result_v1",
    payload_schema={
        "type": "object",
        "properties": {"topic": {"type": "string"}, "findings": {"type": "array"}},
        "required": ["topic", "findings"],
    },
)

SAMPLE_EVENT_DEF_NO_SCHEMA = EventDefinition(
    event_name="ping.completed",
    topic="action-results",
    description="Event with no inline schema",
)


class TestEventClientEventsConsumed:
    """EventClient stores EventDefinitions supplied via events_consumed."""

    def test_events_consumed_stores_definitions_with_event_name(self):
        """EventDefinitions passed to events_consumed are stored for registration."""
        client = EventClient(
            agent_id="test-client",
            events_consumed=[SAMPLE_EVENT_DEF],
        )
        assert len(client._pending_event_definitions) == 1
        assert client._pending_event_definitions[0].event_name == "research.completed"

    def test_events_consumed_empty_by_default(self):
        """No pending definitions when events_consumed is not supplied."""
        client = EventClient(agent_id="test-client")
        assert client._pending_event_definitions == []

    def test_events_consumed_multiple_definitions(self):
        """Multiple EventDefinitions are all stored."""
        client = EventClient(
            agent_id="test-client",
            events_consumed=[SAMPLE_EVENT_DEF, SAMPLE_EVENT_DEF_NO_SCHEMA],
        )
        assert len(client._pending_event_definitions) == 2

    def test_events_consumed_ignores_non_event_definition_objects(self):
        """Strings or objects without event_name are not stored."""
        client = EventClient(
            agent_id="test-client",
            events_consumed=["research.completed"],  # string, not EventDefinition
        )
        assert client._pending_event_definitions == []


class TestEventClientRegisterEventDefinitions:
    """_register_event_definitions() calls Registry for each pending definition."""

    @pytest.fixture
    def mock_registry_client(self):
        """Return a MagicMock that stands in for RegistryClient."""
        mock = MagicMock()
        mock.register_event = AsyncMock(return_value=MagicMock())
        mock.register_schema = AsyncMock(return_value=MagicMock())
        return mock

    @pytest.mark.asyncio
    async def test_register_event_called_for_each_definition(self, mock_registry_client):
        """register_event() is called once per EventDefinition."""
        client = EventClient(
            agent_id="test-client",
            events_consumed=[SAMPLE_EVENT_DEF, SAMPLE_EVENT_DEF_NO_SCHEMA],
        )
        with patch(
            "soorma.registry.client.RegistryClient",
            return_value=mock_registry_client,
        ):
            await client._register_event_definitions()

        assert mock_registry_client.register_event.call_count == 2

    @pytest.mark.asyncio
    async def test_register_schema_called_only_when_inline_body_present(
        self, mock_registry_client
    ):
        """register_schema() is only called for EventDefinitions with payload_schema."""
        client = EventClient(
            agent_id="test-client",
            events_consumed=[SAMPLE_EVENT_DEF, SAMPLE_EVENT_DEF_NO_SCHEMA],
        )
        with patch(
            "soorma.registry.client.RegistryClient",
            return_value=mock_registry_client,
        ):
            await client._register_event_definitions()

        # Only SAMPLE_EVENT_DEF has payload_schema — SAMPLE_EVENT_DEF_NO_SCHEMA does not
        assert mock_registry_client.register_schema.call_count == 1
        call_args = mock_registry_client.register_schema.call_args[0][0]
        assert call_args.schema_name == "research_result_v1"

    @pytest.mark.asyncio
    async def test_409_on_register_event_is_non_fatal(self, mock_registry_client):
        """A 409 response on register_event() is silently ignored (already registered)."""
        conflict = Exception("409 Conflict")
        conflict.response = MagicMock(status_code=409)
        mock_registry_client.register_event = AsyncMock(side_effect=conflict)

        client = EventClient(
            agent_id="test-client",
            events_consumed=[SAMPLE_EVENT_DEF],
        )
        with patch("soorma.registry.client.RegistryClient", return_value=mock_registry_client):
            # Must not raise
            await client._register_event_definitions()

    @pytest.mark.asyncio
    async def test_409_on_register_schema_is_non_fatal(self, mock_registry_client):
        """A 409 response on register_schema() is silently ignored."""
        conflict = Exception("409 Conflict")
        conflict.response = MagicMock(status_code=409)
        mock_registry_client.register_schema = AsyncMock(side_effect=conflict)

        client = EventClient(
            agent_id="test-client",
            events_consumed=[SAMPLE_EVENT_DEF],
        )
        with patch("soorma.registry.client.RegistryClient", return_value=mock_registry_client):
            await client._register_event_definitions()

    @pytest.mark.asyncio
    async def test_importerror_regression_registry_client_importable(self):
        """RegistryClient must be importable from soorma.events (regression guard).

        This test would have caught the RegistryServiceClient vs RegistryClient
        name mismatch that caused a runtime ImportError in the client example.
        """
        # If this import fails, the test fails — no need for further assertions
        import importlib
        mod = importlib.import_module("soorma.events")
        # Trigger the import path by calling the method with an empty list
        client = EventClient(agent_id="test-client")
        client._pending_event_definitions = []
        # Should complete without ImportError
        await client._register_event_definitions()

    @pytest.mark.asyncio
    async def test_noop_when_no_pending_definitions(self, mock_registry_client):
        """_register_event_definitions() is a no-op when list is empty."""
        client = EventClient(agent_id="test-client")
        with patch("soorma.registry.client.RegistryClient", return_value=mock_registry_client):
            await client._register_event_definitions()

        mock_registry_client.register_event.assert_not_called()
        mock_registry_client.register_schema.assert_not_called()


class TestConnectTriggersRegistration:
    """connect() invokes _register_event_definitions() when definitions are pending."""

    @pytest.mark.asyncio
    async def test_connect_calls_registration_when_definitions_pending(self):
        """connect() triggers schema registration before subscribing to topics."""
        client = EventClient(
            agent_id="test-client",
            events_consumed=[SAMPLE_EVENT_DEF],
        )
        with patch.object(
            client, "_register_event_definitions", new_callable=AsyncMock
        ) as mock_reg, patch.object(
            client, "_run_stream", new_callable=AsyncMock
        ):
            await client.connect(topics=[EventTopic.ACTION_RESULTS])

        mock_reg.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_skips_registration_when_no_definitions(self):
        """connect() does not call _register_event_definitions() when list is empty."""
        client = EventClient(agent_id="test-client")
        with patch.object(
            client, "_register_event_definitions", new_callable=AsyncMock
        ) as mock_reg, patch.object(
            client, "_run_stream", new_callable=AsyncMock
        ):
            await client.connect(topics=[EventTopic.ACTION_RESULTS])

        mock_reg.assert_not_called()


class TestEventClientPublishResponseSchemaName:
    """EventClient.publish() passes response_schema_name through to the envelope."""

    @pytest.mark.asyncio
    async def test_publish_includes_response_schema_name_when_provided(self):
        """response_schema_name appears in the published event dict."""
        client = EventClient(
            agent_id="test-client",
            events_consumed=[SAMPLE_EVENT_DEF],
        )
        # Intercept the HTTP call instead of the actual network
        with patch.object(client, "_ensure_http_client", new_callable=AsyncMock), patch.object(
            client, "_http_client", create=True
        ) as mock_http:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"id": "evt-123"}
            mock_http.post = AsyncMock(return_value=mock_response)

            await client.publish(
                event_type="research.goal",
                topic=EventTopic.ACTION_REQUESTS,
                data={"description": "test"},
                response_schema_name="research_result_v1",
            )

            call_json = mock_http.post.call_args[1]["json"]
            assert call_json["event"].get("response_schema_name") == "research_result_v1"

    @pytest.mark.asyncio
    async def test_publish_omits_response_schema_name_when_not_provided(self):
        """response_schema_name is absent from the envelope when not supplied."""
        client = EventClient(agent_id="test-client")
        with patch.object(client, "_ensure_http_client", new_callable=AsyncMock), patch.object(
            client, "_http_client", create=True
        ) as mock_http:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"id": "evt-123"}
            mock_http.post = AsyncMock(return_value=mock_response)

            await client.publish(
                event_type="research.goal",
                topic=EventTopic.ACTION_REQUESTS,
                data={"description": "test"},
            )

            call_json = mock_http.post.call_args[1]["json"]
            assert "response_schema_name" not in call_json["event"]

    @pytest.mark.asyncio
    async def test_publish_includes_authorization_header_when_auth_token_present(self):
        """EventClient should send bearer auth on publish when configured."""
        client = EventClient(agent_id="test-client", auth_token="jwt-token")
        with patch.object(client, "_ensure_http_client", new_callable=AsyncMock), patch.object(
            client, "_http_client", create=True
        ) as mock_http:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"id": "evt-123"}
            mock_http.post = AsyncMock(return_value=mock_response)

            await client.publish(
                event_type="research.goal",
                topic=EventTopic.ACTION_REQUESTS,
                data={"description": "test"},
            )

            headers = mock_http.post.call_args.kwargs["headers"]
            assert headers["Authorization"] == "Bearer jwt-token"
            assert "X-Tenant-ID" not in headers


class TestEventClientAuthHeaders:
    """Tests for event-service auth header construction."""

    @pytest.mark.asyncio
    async def test_build_auth_headers_without_token_uses_platform_tenant_only(self, monkeypatch):
        """Auth headers should be empty when no bearer token is configured."""
        monkeypatch.delenv("SOORMA_AUTH_TOKEN", raising=False)
        client = EventClient(agent_id="test-client", platform_tenant_id="tenant-platform")

        headers = await client._build_auth_headers()

        assert headers == {}

    @pytest.mark.asyncio
    async def test_build_auth_headers_with_token_includes_authorization(self):
        """Auth headers should include Authorization when auth_token is set."""
        client = EventClient(
            agent_id="test-client",
            platform_tenant_id="tenant-platform",
            auth_token="jwt-token",
        )

        headers = await client._build_auth_headers()

        assert "X-Tenant-ID" not in headers
        assert headers["Authorization"] == "Bearer jwt-token"


class TestBusClientResponseSchemaName:
    """BusClient.publish() passes response_schema_name through to EventClient."""

    @pytest.fixture
    def bus_client(self):
        client = BusClient()
        client.event_client = AsyncMock(spec=EventClient)
        client.event_client.publish = AsyncMock(return_value="event-123")
        return client

    @pytest.mark.asyncio
    async def test_publish_passes_response_schema_name(self, bus_client):
        """response_schema_name is forwarded from BusClient.publish to EventClient.publish."""
        await bus_client.publish(
            topic="action-requests",
            event_type="research.goal",
            data={"description": "test"},
            response_schema_name="research_result_v1",
        )

        call_kwargs = bus_client.event_client.publish.call_args[1]
        assert call_kwargs["response_schema_name"] == "research_result_v1"

    @pytest.mark.asyncio
    async def test_publish_response_schema_name_defaults_to_none(self, bus_client):
        """response_schema_name is None when not provided."""
        await bus_client.publish(
            topic="action-requests",
            event_type="research.goal",
            data={},
        )

        call_kwargs = bus_client.event_client.publish.call_args[1]
        assert call_kwargs.get("response_schema_name") is None
