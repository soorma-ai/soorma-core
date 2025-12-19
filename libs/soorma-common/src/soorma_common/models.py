"""
Common Pydantic DTOs for Soorma platform services.

These models are decoupled from database-specific ORM code and can be used
by services, SDKs, and clients across the platform.
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class BaseDTO(BaseModel):
    """
    Base configuration for all DTOs.
    
    - Aliases are generated in camelCase for JSON serialization.
    - Allows population by field name (snake_case) in Python code.
    """
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


# =============================================================================
# Agent Registry DTOs
# =============================================================================


class AgentCapability(BaseDTO):
    """Describes a single capability or task an agent can perform with its event contract."""
    task_name: str = Field(..., description="Name of the task the agent can handle.")
    description: str = Field(..., description="Detailed description of the task and its purpose.")
    consumed_event: str = Field(
        ..., 
        description="Event name (from EventRegistry) that triggers this capability."
    )
    produced_events: List[str] = Field(
        ..., 
        description="List of event names (from EventRegistry) that this capability can produce "
                    "(e.g., success, failure, or partial result events)."
    )


class AgentDefinition(BaseDTO):
    """Defines a single agent in the system."""
    agent_id: str = Field(..., description="Unique identifier for the agent.")
    name: str = Field(..., description="Human-readable name of the agent.")
    description: str = Field(..., description="Description of the agent's overall role and purpose.")
    capabilities: List[AgentCapability] = Field(
        ..., 
        description="List of capabilities/tasks the agent can handle, each with explicit event contracts."
    )
    consumed_events: Optional[List[str]] = Field(
        default=None, 
        description="[DERIVED] List of all event names this agent consumes (union of all capability consumed_events). "
                    "This field is automatically populated from capabilities if not provided."
    )
    produced_events: Optional[List[str]] = Field(
        default=None, 
        description="[DERIVED] List of all event names this agent produces (union of all capability produced_events). "
                    "This field is automatically populated from capabilities if not provided."
    )


class AgentRegistrationRequest(BaseDTO):
    """Request to register a new agent."""
    agent: AgentDefinition = Field(..., description="Agent definition to register.")


class AgentRegistrationResponse(BaseDTO):
    """Response after registering an agent."""
    agent_id: str = Field(..., description="ID of the registered agent.")
    success: bool = Field(..., description="Whether registration was successful.")
    message: str = Field(..., description="Success or error message.")


class AgentQueryRequest(BaseDTO):
    """Request to query agents."""
    agent_id: Optional[str] = Field(default=None, description="Specific agent ID to query.")
    name: Optional[str] = Field(default=None, description="Filter by agent name.")
    consumed_event: Optional[str] = Field(default=None, description="Filter by consumed event.")
    produced_event: Optional[str] = Field(default=None, description="Filter by produced event.")


class AgentQueryResponse(BaseDTO):
    """Response containing agent definitions."""
    agents: List[AgentDefinition] = Field(..., description="List of agent definitions.")
    count: int = Field(..., description="Number of agents returned.")


# =============================================================================
# Event Registry DTOs
# =============================================================================


class EventDefinition(BaseDTO):
    """Defines a single event in the system."""
    event_name: str = Field(..., description="Unique name of the event (e.g., 'user.created').")
    topic: str = Field(..., description="PubSub topic this event belongs to (from PubSubTopic enum).")
    description: str = Field(..., description="Description of what this event represents.")
    payload_schema: Dict[str, Any] = Field(..., description="JSON schema for the event payload.")
    response_schema: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="JSON schema for the response payload, required for action_request events."
    )


class EventRegistrationRequest(BaseDTO):
    """Request to register a new event."""
    event: EventDefinition = Field(..., description="Event definition to register.")


class EventRegistrationResponse(BaseDTO):
    """Response after registering an event."""
    event_name: str = Field(..., description="Name of the registered event.")
    success: bool = Field(..., description="Whether registration was successful.")
    message: str = Field(..., description="Success or error message.")


class EventQueryRequest(BaseDTO):
    """Request to query events."""
    event_name: Optional[str] = Field(default=None, description="Specific event name to query.")
    topic: Optional[str] = Field(default=None, description="Filter by topic.")


class EventQueryResponse(BaseDTO):
    """Response containing event definitions."""
    events: List[EventDefinition] = Field(..., description="List of event definitions.")
    count: int = Field(..., description="Number of events returned.")
