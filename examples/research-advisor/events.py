from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from soorma_common import EventDefinition, EventTopic

# =============================================================================
# 1. General Research
# =============================================================================

class ResearchRequestPayload(BaseModel):
    query: str = Field(..., description="The topic or question to research")
    context: Optional[str] = Field(None, description="Additional context or constraints")

class ResearchResultPayload(BaseModel):
    summary: str = Field(..., description="Summary of the research findings")
    source_url: str = Field(..., description="URL or citation for the source")
    original_request_id: Optional[str] = Field(None, description="ID of the request this answers")

RESEARCH_REQUEST_EVENT = EventDefinition(
    event_name="agent.research.requested",
    topic=EventTopic.ACTION_REQUESTS,
    description="Request to perform web research on a topic.",
    payload_schema=ResearchRequestPayload.model_json_schema(),
    response_schema=ResearchResultPayload.model_json_schema()
)

RESEARCH_RESULT_EVENT = EventDefinition(
    event_name="agent.research.completed",
    topic=EventTopic.ACTION_RESULTS,
    description="Results of the research.",
    payload_schema=ResearchResultPayload.model_json_schema()
)

# =============================================================================
# 2. Advice/Content Drafting
# =============================================================================

class DraftRequestPayload(BaseModel):
    user_request: str = Field(..., description="The user's original request")
    research_context: str = Field(..., description="Relevant information found by research")
    critique: Optional[str] = Field(None, description="Feedback from validator if draft was previously rejected. Include this when requesting a revised draft so the drafter knows what to fix.")

class DraftResultPayload(BaseModel):
    draft_text: str = Field(..., description="The proposed response or advice")
    original_request_id: Optional[str] = Field(None, description="ID of the request this answers")

ADVICE_REQUEST_EVENT = EventDefinition(
    event_name="agent.draft.requested",
    topic=EventTopic.ACTION_REQUESTS,
    description="Request to draft a response based on research. If revising a rejected draft, include validation critique in the payload.",
    payload_schema=DraftRequestPayload.model_json_schema(),
    response_schema=DraftResultPayload.model_json_schema()
)

ADVICE_RESULT_EVENT = EventDefinition(
    event_name="agent.draft.completed",
    topic=EventTopic.ACTION_RESULTS,
    description="Drafted response.",
    payload_schema=DraftResultPayload.model_json_schema()
)

# =============================================================================
# 3. Validation/Fact Checking
# =============================================================================

class ValidationRequestPayload(BaseModel):
    draft_text: str = Field(..., description="The text to be validated")
    source_text: str = Field(..., description="The original source material to check against")

class ValidationResultPayload(BaseModel):
    is_valid: bool = Field(..., description="Whether the draft is accurate based on the source")
    critique: str = Field(..., description="Explanation of why it is valid or invalid")
    original_request_id: Optional[str] = Field(None, description="ID of the request this answers")

VALIDATION_REQUEST_EVENT = EventDefinition(
    event_name="agent.validation.requested",
    topic=EventTopic.ACTION_REQUESTS,
    description="Request to validate a draft against source material.",
    payload_schema=ValidationRequestPayload.model_json_schema(),
    response_schema=ValidationResultPayload.model_json_schema()
)

VALIDATION_RESULT_EVENT = EventDefinition(
    event_name="agent.validation.completed",
    topic=EventTopic.ACTION_RESULTS,
    description="Result of the validation check.",
    payload_schema=ValidationResultPayload.model_json_schema()
)

# =============================================================================
# 4. Overall Workflow Events
# =============================================================================

class GoalPayload(BaseModel):
    goal: str = Field(..., description="The user's high-level goal or question")
    plan_id: str = Field(..., description="Unique identifier for this conversation/plan. Client generates at startup for multi-turn interactions.")

class FulfilledPayload(BaseModel):
    result: str = Field(..., description="The final answer or result")
    source: str = Field(..., description="Source of the information")
    plan_id: str = Field(..., description="The plan_id from the original goal")

GOAL_EVENT = EventDefinition(
    event_name="agent.goal.submitted",
    topic=EventTopic.BUSINESS_FACTS,
    description="A new user goal to be achieved.",
    payload_schema=GoalPayload.model_json_schema()
)

FULFILLED_EVENT = EventDefinition(
    event_name="agent.goal.fulfilled",
    topic=EventTopic.BUSINESS_FACTS,
    description="The user's goal has been successfully fulfilled.",
    payload_schema=FulfilledPayload.model_json_schema()
)
