"""
Tests for event registry DTOs.
"""
import pytest
from soorma_common import EventDefinition, EventRegistrationRequest


def test_event_definition_creation():
    """Test creating an EventDefinition."""
    event = EventDefinition(
        event_name="test.event",
        topic="action-requests",
        description="Test event",
        payload_schema={"type": "object"},
        response_schema={"type": "object"}
    )
    
    assert event.event_name == "test.event"
    assert event.topic == "action-requests"
    assert event.description == "Test event"


def test_event_definition_camel_case_serialization():
    """Test that EventDefinition serializes to camelCase."""
    event = EventDefinition(
        event_name="test.event",
        topic="action-requests",
        description="Test event",
        payload_schema={"type": "object"}
    )
    
    json_data = event.model_dump(by_alias=True)
    
    # Should use camelCase
    assert "eventName" in json_data
    assert "payloadSchema" in json_data
    assert "responseSchema" in json_data
    
    # Should not use snake_case
    assert "event_name" not in json_data
    assert "payload_schema" not in json_data


def test_event_registration_request():
    """Test creating an EventRegistrationRequest."""
    event = EventDefinition(
        event_name="test.event",
        topic="action-requests",
        description="Test event",
        payload_schema={"type": "object"}
    )
    
    request = EventRegistrationRequest(event=event)
    
    assert request.event.event_name == "test.event"
