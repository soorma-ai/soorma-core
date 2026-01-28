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
    
    def __init__(self, version: str = "1.0.0", **data):
        """Initialize AgentDefinition with version appended to name.
        
        Args:
            version: Version string to append to name (default: "1.0.0")
            **data: Other fields including name, agent_id, description, etc.
        """
        # Append version to name only if name doesn't already have a version suffix
        if "name" in data and ":" not in data["name"]:
            data["name"] = f"{data['name']}:{version}"
        super().__init__(**data)


class AgentRegistrationRequest(BaseDTO):
    """Request to register a new agent (Full/Nested format)."""
    agent: AgentDefinition = Field(..., description="Agent definition to register.")


class AgentRegistrationRequestFlat(BaseDTO):
    """
    Request model matching the SDK's flat structure.
    Used by the Registry Service API for simplified registration.
    """
    agent_id: str = Field(..., description="Unique identifier for the agent.")
    name: str = Field(..., description="Human-readable name of the agent.")
    agent_type: str = Field(..., description="Type of the agent (e.g., 'planner', 'worker').")
    capabilities: List[str] = Field(..., description="List of capability names.")
    events_consumed: List[str] = Field(..., description="List of events consumed.")
    events_produced: List[str] = Field(..., description="List of events produced.")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata.")


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


# =============================================================================
# Memory Service DTOs
# =============================================================================


class SemanticMemoryCreate(BaseDTO):
    """Create semantic memory with upsert and privacy support.
    
    RF-ARCH-012: Upsert via external_id or content_hash
    RF-ARCH-014: User-scoped privacy (default private, optional public)
    
    Note: user_id is NOT included in this DTO - it comes from authentication context.
    Clients must authenticate, and the user_id is derived from their auth credentials.
    This prevents clients from claiming ownership of knowledge as another user.
    """
    content: str = Field(..., description="Knowledge content")
    external_id: Optional[str] = Field(None, description="User-provided ID for versioning/upsert")
    is_public: bool = Field(default=False, description="If True, visible to all users in tenant. Default False (private).")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    tags: Optional[List[str]] = Field(None, description="Optional tags for categorization")
    source: Optional[str] = Field(None, description="Optional source identifier")


class SemanticMemoryResponse(BaseDTO):
    """Semantic memory response with upsert and privacy fields.
    
    RF-ARCH-012: Includes external_id and content_hash info
    RF-ARCH-014: Includes user_id and is_public fields
    """
    id: str = Field(..., description="Memory ID")
    tenant_id: str = Field(..., description="Tenant ID")
    user_id: str = Field(..., description="User who owns this knowledge")
    content: str = Field(..., description="Knowledge content")
    external_id: Optional[str] = Field(None, description="User-provided ID")
    is_public: bool = Field(..., description="Whether knowledge is public or private")
    metadata: Dict[str, Any] = Field(..., description="Additional metadata")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    score: Optional[float] = Field(None, description="Similarity score (for search results)")


class EpisodicMemoryCreate(BaseDTO):
    """Create episodic memory."""
    agent_id: str = Field(..., description="Agent identifier")
    role: str = Field(..., description="Role: user, assistant, system, tool")
    content: str = Field(..., description="Interaction content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class EpisodicMemoryResponse(BaseDTO):
    """Episodic memory response."""
    id: str = Field(..., description="Memory ID")
    tenant_id: str = Field(..., description="Tenant ID")
    user_id: str = Field(..., description="User ID")
    agent_id: str = Field(..., description="Agent identifier")
    role: str = Field(..., description="Role")
    content: str = Field(..., description="Interaction content")
    metadata: Dict[str, Any] = Field(..., description="Additional metadata")
    created_at: str = Field(..., description="Creation timestamp")
    score: Optional[float] = Field(None, description="Similarity score (for search results)")


class ProceduralMemoryResponse(BaseDTO):
    """Procedural memory response."""
    id: str = Field(..., description="Memory ID")
    tenant_id: str = Field(..., description="Tenant ID")
    user_id: str = Field(..., description="User ID")
    agent_id: str = Field(..., description="Agent identifier")
    trigger_condition: Optional[str] = Field(None, description="Trigger condition")
    procedure_type: str = Field(..., description="Procedure type: system_prompt or few_shot_example")
    content: str = Field(..., description="Procedure content")
    created_at: str = Field(..., description="Creation timestamp")
    score: Optional[float] = Field(None, description="Similarity score (for search results)")


class WorkingMemorySet(BaseDTO):
    """Set working memory value."""
    value: Any = Field(..., description="State value (JSON-serializable)")


class WorkingMemoryResponse(BaseDTO):
    """Working memory response."""
    id: str = Field(..., description="Memory ID")
    tenant_id: str = Field(..., description="Tenant ID")
    plan_id: str = Field(..., description="Plan ID")
    key: str = Field(..., description="State key")
    value: Any = Field(..., description="State value (JSON-serializable)")
    updated_at: str = Field(..., description="Last update timestamp")


# =============================================================================
# Task Context DTOs
# =============================================================================


class TaskContextCreate(BaseDTO):
    """Create task context."""
    task_id: str = Field(..., description="Task ID")
    plan_id: Optional[str] = Field(None, description="Plan ID")
    event_type: str = Field(..., description="Event type that triggered this task")
    response_event: Optional[str] = Field(None, description="Expected response event")
    response_topic: str = Field(default='action-results', description="Response topic")
    data: Dict[str, Any] = Field(default_factory=dict, description="Original request data")
    sub_tasks: List[str] = Field(default_factory=list, description="List of sub-task IDs")
    state: Dict[str, Any] = Field(default_factory=dict, description="Worker-specific state")


class TaskContextUpdate(BaseDTO):
    """Update task context."""
    sub_tasks: Optional[List[str]] = Field(None, description="Updated sub-task list")
    state: Optional[Dict[str, Any]] = Field(None, description="Updated state")


class TaskContextResponse(BaseDTO):
    """Task context response."""
    id: str = Field(..., description="Record ID")
    tenant_id: str = Field(..., description="Tenant ID")
    task_id: str = Field(..., description="Task ID")
    plan_id: Optional[str] = Field(None, description="Plan ID")
    event_type: str = Field(..., description="Event type")
    response_event: Optional[str] = Field(None, description="Response event")
    response_topic: str = Field(..., description="Response topic")
    data: Dict[str, Any] = Field(..., description="Request data")
    sub_tasks: List[str] = Field(..., description="Sub-task IDs")
    state: Dict[str, Any] = Field(..., description="Worker state")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")


# =============================================================================
# Plan Context DTOs
# =============================================================================


class PlanContextCreate(BaseDTO):
    """Create plan context."""
    plan_id: str = Field(..., description="Plan ID")
    session_id: Optional[str] = Field(None, description="Session ID")
    goal_event: str = Field(..., description="Goal event type")
    goal_data: Dict[str, Any] = Field(default_factory=dict, description="Goal data")
    response_event: Optional[str] = Field(None, description="Expected response event")
    state: Dict[str, Any] = Field(default_factory=dict, description="Plan state machine")
    current_state: Optional[str] = Field(None, description="Current state name")
    correlation_ids: List[str] = Field(default_factory=list, description="Correlation IDs")


class PlanContextUpdate(BaseDTO):
    """Update plan context."""
    state: Optional[Dict[str, Any]] = Field(None, description="Updated state")
    current_state: Optional[str] = Field(None, description="Updated current state")
    correlation_ids: Optional[List[str]] = Field(None, description="Updated correlation IDs")


class PlanContextResponse(BaseDTO):
    """Plan context response."""
    id: str = Field(..., description="Record ID")
    tenant_id: str = Field(..., description="Tenant ID")
    plan_id: str = Field(..., description="Plan ID")
    session_id: Optional[str] = Field(None, description="Session ID")
    goal_event: str = Field(..., description="Goal event type")
    goal_data: Dict[str, Any] = Field(..., description="Goal data")
    response_event: Optional[str] = Field(None, description="Response event")
    state: Dict[str, Any] = Field(..., description="Plan state")
    current_state: Optional[str] = Field(None, description="Current state")
    correlation_ids: List[str] = Field(..., description="Correlation IDs")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")


# =============================================================================
# Plan & Session DTOs
# =============================================================================


class PlanCreate(BaseDTO):
    """Create plan."""
    plan_id: str = Field(..., description="Plan ID")
    session_id: Optional[str] = Field(None, description="Session ID")
    goal_event: str = Field(..., description="Goal event type")
    goal_data: Dict[str, Any] = Field(default_factory=dict, description="Goal data")
    parent_plan_id: Optional[str] = Field(None, description="Parent plan ID")


class PlanUpdate(BaseDTO):
    """Update plan."""
    status: str = Field(..., description="Plan status: running, completed, failed, paused")


class PlanSummary(BaseDTO):
    """Plan summary response."""
    id: str = Field(..., description="Record ID")
    plan_id: str = Field(..., description="Plan ID")
    session_id: Optional[str] = Field(None, description="Session ID")
    goal_event: str = Field(..., description="Goal event type")
    goal_data: Dict[str, Any] = Field(..., description="Goal data")
    status: str = Field(..., description="Plan status")
    parent_plan_id: Optional[str] = Field(None, description="Parent plan ID")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")


class SessionCreate(BaseDTO):
    """Create session."""
    session_id: str = Field(..., description="Session ID")
    name: Optional[str] = Field(None, description="Session name")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Session metadata")


class SessionSummary(BaseDTO):
    """Session summary response."""
    id: str = Field(..., description="Record ID")
    session_id: str = Field(..., description="Session ID")
    name: Optional[str] = Field(None, description="Session name")
    metadata: Dict[str, Any] = Field(..., description="Session metadata")
    created_at: str = Field(..., description="Creation timestamp")
    last_interaction: str = Field(..., description="Last interaction timestamp")

