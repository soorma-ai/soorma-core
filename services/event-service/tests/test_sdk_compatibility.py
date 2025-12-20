import pytest
from datetime import datetime, timezone
from src.models.schemas import PublishRequest, EventPayload

def test_event_envelope_serialization():
    """Test that EventEnvelope serializes correctly for SDK compatibility."""
    
    # Simulate SDK payload
    sdk_event = {
        "id": "123",
        "source": "test-agent",
        "specversion": "1.0",
        "type": "test.event",
        "topic": "business-facts",
        "time": datetime.now(timezone.utc).isoformat(),
        "data": {"key": "value"},
        "correlation_id": "trace-123",
        "tenant_id": "tenant-1",
    }
    
    # Parse into PublishRequest (validates using EventEnvelope)
    request = PublishRequest(event=sdk_event)
    event = request.event
    
    # Check to_cloudevents_dict output
    ce_dict = event.to_cloudevents_dict()
    print(f"\nCloudEvents Dict: {ce_dict.keys()}")
    
    # Check model_dump output
    dump_dict = event.model_dump(mode='json', exclude_none=True)
    print(f"\nModel Dump: {dump_dict.keys()}")
    
    # SDK expects 'correlation_id', not 'correlationid'
    assert "correlation_id" in dump_dict
    assert "correlationid" not in dump_dict
    
    # CloudEvents dict has 'correlationid'
    assert "correlationid" in ce_dict
    assert "correlation_id" not in ce_dict
    
    # SDK expects 'tenant_id', not 'tenantid'
    assert "tenant_id" in dump_dict
    
    # Verify topic is string
    assert isinstance(dump_dict["topic"], str)
    assert dump_dict["topic"] == "business-facts"
