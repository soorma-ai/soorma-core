"""
Tests for Schema Registry DTOs in soorma-common (v0.8.1+).

RED Phase: Tests assert REAL expected behavior.
- PayloadSchema tests should PASS (Pydantic validation works)
- DiscoveredAgent helper method tests should FAIL with NotImplementedError
"""
import pytest
from datetime import datetime, timezone

from soorma_common.models import (
    PayloadSchema,
    PayloadSchemaRegistration,
    PayloadSchemaResponse,
    EventDefinition,
    AgentCapability,
    DiscoveredAgent,
)


class TestPayloadSchema:
    """Tests for PayloadSchema model."""
    
    def test_payload_schema_valid(self):
        """Valid schema passes validation."""
        schema = PayloadSchema(
            schema_name="research_request_v1",
            version="1.0.0",
            json_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                }
            }
        )
        assert schema.schema_name == "research_request_v1"
        assert schema.version == "1.0.0"
        assert schema.json_schema["type"] == "object"
    
    def test_payload_schema_with_description(self):
        """Schema with description."""
        schema = PayloadSchema(
            schema_name="test_v1",
            version="1.0.0",
            json_schema={},
            description="Test schema description"
        )
        assert schema.description == "Test schema description"
    
    def test_payload_schema_with_owner(self):
        """Schema with owner_agent_id."""
        schema = PayloadSchema(
            schema_name="test_v1",
            version="1.0.0",
            json_schema={},
            owner_agent_id="agent-123"
        )
        assert schema.owner_agent_id == "agent-123"
    
    def test_payload_schema_camel_case_serialization(self):
        """DTO serializes to camelCase."""
        schema = PayloadSchema(
            schema_name="test_v1",
            version="1.0.0",
            json_schema={}
        )
        json_data = schema.model_dump(by_alias=True)
        assert "schemaName" in json_data
        assert "jsonSchema" in json_data
    
    def test_payload_schema_invalid_missing_name(self):
        """Schema name is required."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            PayloadSchema(
                version="1.0.0",
                json_schema={}
            )
    
    def test_payload_schema_invalid_missing_version(self):
        """Version is required."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            PayloadSchema(
                schema_name="test",
                json_schema={}
            )


class TestPayloadSchemaRegistration:
    """Tests for PayloadSchemaRegistration model."""
    
    def test_registration_valid(self):
        """Valid registration request."""
        reg = PayloadSchemaRegistration(
            schema_name="research_request_v1",
            version="1.0.0",
            json_schema={"type": "object"}
        )
        assert reg.schema_name == "research_request_v1"
        assert reg.version == "1.0.0"
    
    def test_registration_with_description(self):
        """Registration with description."""
        reg = PayloadSchemaRegistration(
            schema_name="test", 
            version="1.0.0",
            json_schema={},
            description="Test description"
        )
        assert reg.description == "Test description"


class TestPayloadSchemaResponse:
    """Tests for PayloadSchemaResponse model."""
    
    def test_response_success(self):
        """Success response."""
        resp = PayloadSchemaResponse(
            schema_name="test_v1",
            version="1.0.0",
            success=True,
            message="Schema registered successfully"
        )
        assert resp.success is True
        assert resp.message == "Schema registered successfully"
    
    def test_response_failure(self):
        """Failure response."""
        resp = PayloadSchemaResponse(
            schema_name="test_v1",
            version="1.0.0",
            success=False,
            message="Schema already exists"
        )
        assert resp.success is False


class TestEnhancedEventDefinition:
    """Tests for enhanced EventDefinition with schema references."""
    
    def test_event_definition_with_schema_name_reference(self):
        """EventDefinition with schema_name reference (v0.8.1 pattern)."""
        event = EventDefinition(
            event_name="research.requested",
            topic="action-requests",
            description="Research request event",
            payload_schema_name="research_request_v1"
        )
        assert event.payload_schema_name == "research_request_v1"
        assert event.payload_schema is None  # Deprecated field not set
    
    def test_event_definition_with_response_schema_name(self):
        """EventDefinition with response_schema_name."""
        event = EventDefinition(
            event_name="research.requested",
            topic="action-requests",
            description="Research request event",
            payload_schema_name="research_request_v1",
            response_schema_name="research_response_v1"
        )
        assert event.response_schema_name == "research_response_v1"
    
    def test_event_definition_backward_compat_embedded_schema(self):
        """EventDefinition accepts embedded schema (deprecated but supported)."""
        event = EventDefinition(
            event_name="research.requested",
            topic="action-requests",
            description="Research request event",
            payload_schema={"type": "object"}
        )
        assert event.payload_schema is not None
        assert event.payload_schema_name is None
    
    def test_event_definition_both_schema_formats(self):
        """EventDefinition can have both old and new format (transition period)."""
        event = EventDefinition(
            event_name="research.requested",
            topic="action-requests",
            description="Research request event",
            payload_schema_name="research_request_v1",
            payload_schema={"type": "object"}  # Deprecated but still supported
        )
        assert event.payload_schema_name == "research_request_v1"
        assert event.payload_schema == {"type": "object"}


class TestEnhancedAgentCapability:
    """Tests for enhanced AgentCapability with EventDefinition objects."""
    
    def test_agent_capability_with_event_definition(self):
        """AgentCapability with EventDefinition objects (v0.8.1 pattern)."""
        capability = AgentCapability(
            task_name="web_research",
            description="Performs web research",
            consumed_event=EventDefinition(
                event_name="research.requested",
                topic="action-requests",
                description="Research request",
                payload_schema_name="research_request_v1"
            ),
            produced_events=[
                EventDefinition(
                    event_name="research.completed",
                    topic="action-results",
                    description="Research result",
                    payload_schema_name="research_result_v1"
                )
            ]
        )
        assert isinstance(capability.consumed_event, EventDefinition)
        assert len(capability.produced_events) == 1
        assert isinstance(capability.produced_events[0], EventDefinition)
        assert capability.consumed_event.event_name == "research.requested"
        assert capability.produced_events[0].event_name == "research.completed"
    
    def test_agent_capability_rejects_string_consumed_event(self):
        """AgentCapability rejects string for consumed_event (breaking change v0.8.1)."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            AgentCapability(
                task_name="web_research",
                description="Performs web research",
                consumed_event="research.requested",  # String not allowed
                produced_events=[]
            )
    
    def test_agent_capability_rejects_string_produced_events(self):
        """AgentCapability rejects strings in produced_events (breaking change v0.8.1)."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            AgentCapability(
                task_name="web_research",
                description="Performs web research",
                consumed_event=EventDefinition(
                    event_name="research.requested",
                    topic="action-requests",
                    description="Research request"
                ),
                produced_events=["research.completed"]  # String not allowed
            )


class TestDiscoveredAgent:
    """Tests for DiscoveredAgent with helper methods.
    
    RED Phase: These tests assert REAL expected behavior and will FAIL with NotImplementedError.
    """
    
    def test_discovered_agent_basic_creation(self):
        """Create DiscoveredAgent with capabilities."""
        agent = DiscoveredAgent(
            agent_id="worker-001",
            name="Research Worker:1.0.0",
            description="Performs research tasks",
            version="1.0.0",
            capabilities=[]
        )
        assert agent.agent_id == "worker-001"
        assert agent.name == "Research Worker:1.0.0"
        assert agent.version == "1.0.0"
    
    def test_discovered_agent_get_consumed_schemas(self):
        """DiscoveredAgent extracts consumed schema names.
        
        RED Phase: This test asserts REAL expected behavior.
        Will fail with NotImplementedError until GREEN phase.
        """
        agent = DiscoveredAgent(
            agent_id="worker-001",
            name="Research Worker:1.0.0",
            description="Performs research",
            version="1.0.0",
            capabilities=[
                AgentCapability(
                    task_name="research",
                    description="Research capability",
                    consumed_event=EventDefinition(
                        event_name="research.requested",
                        topic="action-requests",
                        description="Research request",
                        payload_schema_name="research_request_v1"
                    ),
                    produced_events=[]
                )
            ]
        )
        
        # Assert REAL expected behavior (will fail with NotImplementedError)
        consumed_schemas = agent.get_consumed_schemas()
        assert "research_request_v1" in consumed_schemas
        assert len(consumed_schemas) == 1
    
    def test_discovered_agent_get_produced_schemas(self):
        """DiscoveredAgent extracts produced schema names.
        
        RED Phase: This test asserts REAL expected behavior.
        Will fail with NotImplementedError until GREEN phase.
        """
        agent = DiscoveredAgent(
            agent_id="worker-001",
            name="Research Worker:1.0.0",
            description="Performs research",
            version="1.0.0",
            capabilities=[
                AgentCapability(
                    task_name="research",
                    description="Research capability",
                    consumed_event=EventDefinition(
                        event_name="research.requested",
                        topic="action-requests",
                        description="Research request"
                    ),
                    produced_events=[
                        EventDefinition(
                            event_name="research.completed",
                            topic="action-results",
                            description="Research completed",
                            payload_schema_name="research_result_v1"
                        ),
                        EventDefinition(
                            event_name="research.failed",
                            topic="action-results",
                            description="Research failed",
                            payload_schema_name="error_v1"
                        )
                    ]
                )
            ]
        )
        
        # Assert REAL expected behavior (will fail with NotImplementedError)
        produced_schemas = agent.get_produced_schemas()
        assert "research_result_v1" in produced_schemas
        assert "error_v1" in produced_schemas
        assert len(produced_schemas) == 2
    
    def test_discovered_agent_get_schemas_with_multiple_capabilities(self):
        """DiscoveredAgent extracts schemas from multiple capabilities.
        
        RED Phase: Tests deduplication logic (REAL expected behavior).
        """
        agent = DiscoveredAgent(
            agent_id="worker-001",
            name="Multi Worker:1.0.0",
            description="Multi-capability worker",
            version="1.0.0",
            capabilities=[
                AgentCapability(
                    task_name="research",
                    description="Research capability",
                    consumed_event=EventDefinition(
                        event_name="research.requested",
                        topic="action-requests",
                        description="Research request",
                        payload_schema_name="research_request_v1"
                    ),
                    produced_events=[
                        EventDefinition(
                            event_name="research.completed",
                            topic="action-results",
                            description="Research completed",
                            payload_schema_name="research_result_v1"
                        )
                    ]
                ),
                AgentCapability(
                    task_name="analysis",
                    description="Analysis capability",
                    consumed_event=EventDefinition(
                        event_name="analysis.requested",
                        topic="action-requests",
                        description="Analysis request",
                        payload_schema_name="analysis_request_v1"
                    ),
                    produced_events=[
                        EventDefinition(
                            event_name="analysis.completed",
                            topic="action-results",
                            description="Analysis completed",
                            payload_schema_name="research_result_v1"  # Same schema as research
                        )
                    ]
                )
            ]
        )
        
        # Assert REAL expected behavior with deduplication
        consumed_schemas = agent.get_consumed_schemas()
        assert "research_request_v1" in consumed_schemas
        assert "analysis_request_v1" in consumed_schemas
        assert len(consumed_schemas) == 2
        
        produced_schemas = agent.get_produced_schemas()
        assert "research_result_v1" in produced_schemas
        assert len(produced_schemas) == 1  # Deduplicated
    
    def test_discovered_agent_handles_none_schema_names(self):
        """DiscoveredAgent handles events without schema names.
        
        RED Phase: Tests filtering logic (REAL expected behavior).
        """
        agent = DiscoveredAgent(
            agent_id="worker-001",
            name="Worker:1.0.0",
            description="Worker",
            version="1.0.0",
            capabilities=[
                AgentCapability(
                    task_name="task",
                    description="Task",
                    consumed_event=EventDefinition(
                        event_name="task.requested",
                        topic="action-requests",
                        description="Task request",
                        payload_schema_name=None  # No schema name
                    ),
                    produced_events=[
                        EventDefinition(
                            event_name="task.completed",
                            topic="action-results",
                            description="Task completed",
                            payload_schema_name="task_result_v1"
                        )
                    ]
                )
            ]
        )
        
        # Should filter out None values
        consumed_schemas = agent.get_consumed_schemas()
        assert consumed_schemas == []  # No schema name in consumed event
        
        produced_schemas = agent.get_produced_schemas()
        assert produced_schemas == ["task_result_v1"]
