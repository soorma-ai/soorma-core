"""
Tests for the full RegistryClient (soorma.registry.client).
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from soorma.registry.client import RegistryClient
from soorma_common import EventDefinition

@pytest.mark.asyncio
async def test_register_event_structured():
    """
    Test registering an event with structured definition.
    """
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    # Mock response for EventRegistrationResponse
    mock_response.json.return_value = {
        "eventName": "test.event",
        "success": True,
        "message": "Registered successfully"
    }
    mock_client.post.return_value = mock_response

    client = RegistryClient(base_url="http://test-registry")
    client._client = mock_client

    # Create structured event definition
    event_def = EventDefinition(
        event_name="test.event",
        topic="action-requests",
        description="A test event",
        payload_schema={
            "type": "object",
            "properties": {
                "field1": {"type": "string"}
            },
            "required": ["field1"]
        },
        response_schema={
            "type": "object",
            "properties": {
                "result": {"type": "boolean"}
            }
        }
    )

    # Register event
    response = await client.register_event(event_def)

    assert response.success is True
    assert response.event_name == "test.event"

    # Verify payload
    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    url = call_args[0][0]
    kwargs = call_args[1]
    payload = kwargs["json"]

    assert url == "http://test-registry/api/v1/events"
    assert "event" in payload
    event_payload = payload["event"]
    
    assert event_payload["eventName"] == "test.event"
    assert event_payload["topic"] == "action-requests"
    assert event_payload["payloadSchema"]["type"] == "object"
    assert event_payload["responseSchema"]["type"] == "object"
