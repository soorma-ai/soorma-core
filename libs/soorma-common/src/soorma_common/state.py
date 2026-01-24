"""
State machine DTOs for Planner and State Tracker.
"""
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any


class StateAction(BaseModel):
    """Action to execute when entering a state."""
    
    event_type: str = Field(..., description="Event to publish")
    response_event: str = Field(..., description="Expected response event")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Event payload template")


class StateTransition(BaseModel):
    """A transition from one state to another."""
    
    on_event: str = Field(..., description="Event type that triggers this transition")
    to_state: str = Field(..., description="Target state name")
    condition: Optional[str] = Field(default=None, description="Optional condition expression")


class StateConfig(BaseModel):
    """Configuration for a state in the plan state machine."""
    
    state_name: str = Field(..., description="Unique state identifier")
    description: str = Field(..., description="Human-readable description")
    action: Optional[StateAction] = Field(default=None, description="Action on state entry")
    transitions: List[StateTransition] = Field(default_factory=list)
    default_next: Optional[str] = Field(default=None, description="For unconditional transitions")
    is_terminal: bool = Field(default=False, description="Whether this is a terminal state")


class PlanDefinition(BaseModel):
    """Definition of a plan's state machine - used for registration."""
    
    plan_type: str = Field(..., description="Type of plan (e.g., 'research.plan')")
    description: str = Field(..., description="Plan description")
    initial_state: str = Field(default="start", description="Starting state")
    states: Dict[str, StateConfig] = Field(..., description="State machine definition")


class PlanRegistrationRequest(BaseModel):
    """Request to register a plan type with State Tracker."""
    
    plan: PlanDefinition


class PlanInstanceRequest(BaseModel):
    """Request to create a new plan instance."""
    
    plan_type: str
    goal_data: Dict[str, Any]
    session_id: Optional[str] = None
    parent_plan_id: Optional[str] = None
