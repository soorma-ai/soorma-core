"""
Tests for agent registry DTOs.
"""
import pytest
from soorma_common import AgentDefinition, AgentCapability, AgentRegistrationRequest


def test_agent_capability_creation():
    """Test creating an AgentCapability."""
    capability = AgentCapability(
        task_name="perform_task",
        description="Performs a task",
        consumed_event="event.request",
        produced_events=["event.response", "event.failed"]
    )
    
    assert capability.task_name == "perform_task"
    assert capability.description == "Performs a task"
    assert capability.consumed_event == "event.request"
    assert len(capability.produced_events) == 2


def test_agent_definition_creation():
    """Test creating an AgentDefinition."""
    capability = AgentCapability(
        task_name="perform_task",
        description="Performs a task",
        consumed_event="event.request",
        produced_events=["event.response"]
    )
    
    agent = AgentDefinition(
        agent_id="test-agent-v1",
        name="Test Agent",
        description="Test agent description",
        capabilities=[capability]
        # consumed_events and produced_events will be derived from capabilities
    )
    
    assert agent.agent_id == "test-agent-v1"
    # Name now includes default version suffix
    assert agent.name == "Test Agent:1.0.0"
    assert len(agent.capabilities) == 1


def test_agent_definition_camel_case_serialization():
    """Test that AgentDefinition serializes to camelCase."""
    capability = AgentCapability(
        task_name="perform_task",
        description="Performs a task",
        consumed_event="event.request",
        produced_events=["event.response"]
    )
    
    agent = AgentDefinition(
        agent_id="test-agent-v1",
        name="Test Agent",
        description="Test agent description",
        capabilities=[capability],
        consumed_events=["event.request"],
        produced_events=["event.response"]
    )
    
    json_data = agent.model_dump(by_alias=True)
    
    # Should use camelCase
    assert "agentId" in json_data
    assert "consumedEvents" in json_data
    assert "producedEvents" in json_data
    
    # Should not use snake_case
    assert "agent_id" not in json_data
    assert "consumed_events" not in json_data
    assert "produced_events" not in json_data


def test_agent_registration_request():
    """Test creating an AgentRegistrationRequest."""
    capability = AgentCapability(
        task_name="perform_task",
        description="Performs a task",
        consumed_event="event.request",
        produced_events=["event.response"]
    )
    
    agent = AgentDefinition(
        agent_id="test-agent-v1",
        name="Test Agent",
        description="Test agent description",
        capabilities=[capability]
    )
    
    request = AgentRegistrationRequest(agent=agent)
    
    assert request.agent.agent_id == "test-agent-v1"

def test_agent_definition_version_appended_to_name():
    """Test that version is appended to agent name."""
    capability = AgentCapability(
        task_name="perform_task",
        description="Performs a task",
        consumed_event="event.request",
        produced_events=["event.response"]
    )
    
    # Create with explicit version
    agent = AgentDefinition(
        agent_id="test-agent-v1",
        name="Test Agent",
        description="Test agent description",
        capabilities=[capability],
        version="2.0.0"
    )
    
    # Name should have version appended
    assert agent.name == "Test Agent:2.0.0"


def test_agent_definition_default_version():
    """Test that default version (1.0.0) is appended to name."""
    capability = AgentCapability(
        task_name="perform_task",
        description="Performs a task",
        consumed_event="event.request",
        produced_events=["event.response"]
    )
    
    # Create without explicit version (uses default "1.0.0")
    agent = AgentDefinition(
        agent_id="test-agent-v1",
        name="Test Agent",
        description="Test agent description",
        capabilities=[capability]
    )
    
    # Name should have default version appended
    assert agent.name == "Test Agent:1.0.0"


def test_agent_definition_no_double_versioning():
    """Test that version is not appended twice if name already contains colon."""
    capability = AgentCapability(
        task_name="perform_task",
        description="Performs a task",
        consumed_event="event.request",
        produced_events=["event.response"]
    )
    
    # Simulate deserialization from registry (name already has version)
    agent = AgentDefinition(
        agent_id="test-agent-v1",
        name="Test Agent:2.0.0",
        description="Test agent description",
        capabilities=[capability],
        version="1.0.0"  # This should be ignored since name already has version
    )
    
    # Name should NOT have double versioning
    assert agent.name == "Test Agent:2.0.0"
    assert agent.name.count(":") == 1