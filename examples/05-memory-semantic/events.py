"""
Event definitions for knowledge management system.

These events define the API between the router, knowledge store, and answer agent.
"""

from pydantic import BaseModel, Field
from soorma_common import EventDefinition, EventTopic


# ============================================================================
# Input Event - User Request
# ============================================================================

class UserRequestPayload(BaseModel):
    """User's natural language request."""
    request: str = Field(..., description="User's request in natural language")


USER_REQUEST_EVENT = EventDefinition(
    event_name="user.request",
    topic=EventTopic.ACTION_REQUESTS,
    description="User request that needs to be routed to either knowledge storage or question answering",
    payload_schema=UserRequestPayload.model_json_schema(),
)


# ============================================================================
# Action Events - What the router can choose
# ============================================================================

class StoreKnowledgePayload(BaseModel):
    """Request to store knowledge in semantic memory."""
    content: str = Field(..., description="Knowledge content to store")
    metadata: dict = Field(default_factory=dict, description="Optional metadata (source, category, etc.)")


STORE_KNOWLEDGE_EVENT = EventDefinition(
    event_name="knowledge.store",
    topic=EventTopic.ACTION_REQUESTS,
    description="Store factual knowledge or information in semantic memory for later retrieval. Use when user wants to teach the system something, add facts, or store reference information.",
    payload_schema=StoreKnowledgePayload.model_json_schema(),
)


class AnswerQuestionPayload(BaseModel):
    """Request to answer a question using stored knowledge."""
    question: str = Field(..., description="Question to answer")


ANSWER_QUESTION_EVENT = EventDefinition(
    event_name="question.ask",
    topic=EventTopic.ACTION_REQUESTS,
    description="Answer a question using knowledge from semantic memory. Use when user asks a question that requires factual information or wants to retrieve stored knowledge.",
    payload_schema=AnswerQuestionPayload.model_json_schema(),
)


# ============================================================================
# Result Events - Responses
# ============================================================================

class KnowledgeStoredPayload(BaseModel):
    """Confirmation that knowledge was stored."""
    content: str = Field(..., description="Content that was stored")
    success: bool = Field(..., description="Whether storage succeeded")
    message: str = Field(..., description="Status message")


KNOWLEDGE_STORED_EVENT = EventDefinition(
    event_name="knowledge.stored",
    topic=EventTopic.ACTION_RESULTS,
    description="Knowledge has been successfully stored in semantic memory",
    payload_schema=KnowledgeStoredPayload.model_json_schema(),
)


class QuestionAnsweredPayload(BaseModel):
    """Answer to a question."""
    question: str = Field(..., description="The original question")
    answer: str = Field(..., description="The generated answer")
    knowledge_used: list = Field(default_factory=list, description="Knowledge fragments used")
    has_knowledge: bool = Field(..., description="Whether relevant knowledge was found")


QUESTION_ANSWERED_EVENT = EventDefinition(
    event_name="question.answered",
    topic=EventTopic.ACTION_RESULTS,
    description="Question has been answered using semantic memory",
    payload_schema=QuestionAnsweredPayload.model_json_schema(),
)
