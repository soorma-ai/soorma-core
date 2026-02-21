"""Decision types for LLM-based planning.

This module defines the decision types that LLM-based planners use to determine
the next action in a workflow. These types provide type-safe, structured outputs
from LLM reasoning that can be validated and executed safely.

The decision system prevents LLM hallucinations by validating that referenced
events exist in the Registry before execution.

Usage:
    from soorma_common.decisions import PlannerDecision, PlanAction
    
    decision = PlannerDecision(
        plan_id="plan-123",
        current_state="search",
        next_action=PublishAction(
            action=PlanAction.PUBLISH,
            event_type="search.requested",
            data={"query": "AI agents"},
            reasoning="Need to search for information",
        ),
        reasoning="Starting search based on goal requirements",
    )
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class PlanAction(str, Enum):
    """Actions a Planner can take in response to events.
    
    Attributes:
        PUBLISH: Publish a new event to trigger a worker
        COMPLETE: Mark plan as complete and send response_event
        WAIT: Wait for external input (e.g., human approval)
        DELEGATE: Delegate to another planner
    """
    
    PUBLISH = "publish"
    COMPLETE = "complete"
    WAIT = "wait"
    DELEGATE = "delegate"


class PublishAction(BaseModel):
    """Instruction to publish a new event.
    
    Used when the planner needs to trigger a worker or service by publishing
    an action request event.
    
    Attributes:
        action: Action type (PUBLISH)
        event_type: Event type to publish (must exist in Registry)
        topic: Topic for event (default: "action-requests")
        data: Event payload
        reasoning: Why this event should be published
    """
    
    action: PlanAction = Field(default=PlanAction.PUBLISH, description="Action type")
    event_type: str = Field(..., description="Event type to publish")
    topic: Optional[str] = Field(default="action-requests", description="Topic for event")
    data: Dict[str, Any] = Field(default_factory=dict, description="Event payload")
    reasoning: str = Field(..., description="Why this event should be published")


class CompleteAction(BaseModel):
    """Instruction to complete the plan.
    
    Used when the planner determines that the goal has been achieved and
    the plan should be finalized with a response.
    
    Attributes:
        action: Action type (COMPLETE)
        result: Final result to return
        reasoning: Why the plan is now complete
    """
    
    action: PlanAction = Field(default=PlanAction.COMPLETE, description="Action type")
    result: Dict[str, Any] = Field(..., description="Final result to return")
    reasoning: str = Field(..., description="Why the plan is now complete")


class WaitAction(BaseModel):
    """Instruction to pause and wait for external input.
    
    Used when the planner needs human approval, missing information, or
    must wait for an external dependency.
    
    Attributes:
        action: Action type (WAIT)
        reason: Why we're waiting
        expected_event: Event type that will resume the plan
        timeout_seconds: Timeout in seconds (default: 1 hour)
    """
    
    action: PlanAction = Field(default=PlanAction.WAIT, description="Action type")
    reason: str = Field(..., description="Why we're waiting")
    expected_event: str = Field(..., description="Event type that will resume the plan")
    timeout_seconds: Optional[int] = Field(
        default=3600,
        description="Timeout in seconds (default: 1 hour)"
    )


class DelegateAction(BaseModel):
    """Instruction to delegate to another planner.
    
    Used when the current planner determines that another specialized planner
    should handle a subtask.
    
    Attributes:
        action: Action type (DELEGATE)
        target_planner: Name of planner to delegate to
        goal_event: Goal event to send
        goal_data: Goal parameters
        reasoning: Why delegation is appropriate
    """
    
    action: PlanAction = Field(default=PlanAction.DELEGATE, description="Action type")
    target_planner: str = Field(..., description="Name of planner to delegate to")
    goal_event: str = Field(..., description="Goal event to send")
    goal_data: Dict[str, Any] = Field(..., description="Goal parameters")
    reasoning: str = Field(..., description="Why delegation is appropriate")


# Union of all action types for discriminated union
PlannerAction = Union[PublishAction, CompleteAction, WaitAction, DelegateAction]


class PlannerDecision(BaseModel):
    """LLM decision on what to do next in a plan.
    
    This is the output of ChoreographyPlanner.reason_next_action().
    The SDK validates that referenced events exist before execution.
    
    Attributes:
        plan_id: Plan being executed
        current_state: Current state in the plan
        next_action: Action to take (discriminated union)
        alternative_actions: Alternative actions the planner considered
        confidence: Confidence in this decision (0-1)
        reasoning: LLM's reasoning for this decision
    
    Example:
        ```python
        decision = PlannerDecision(
            plan_id="plan-123",
            current_state="search",
            next_action=PublishAction(
                event_type="search.requested",
                data={"query": "AI agents"},
                reasoning="Need to search",
            ),
            reasoning="Starting search phase",
        )
        ```
    """
    
    plan_id: str = Field(..., description="Plan being executed")
    current_state: str = Field(..., description="Current state in the plan")
    next_action: PlannerAction = Field(..., description="Action to take")
    alternative_actions: Optional[List[PlannerAction]] = Field(
        default=None,
        description="Alternative actions the planner considered"
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence in this decision (0-1)"
    )
    reasoning: str = Field(..., description="LLM's reasoning for this decision")
    
    # Model configuration for JSON schema generation
    model_config = {
        "json_schema_extra": {
            "title": "Planner Decision",
            "description": "Decision on next action in plan execution",
        }
    }
