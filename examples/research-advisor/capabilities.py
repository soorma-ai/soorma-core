from soorma_common import AgentCapability
from events import (
    RESEARCH_REQUEST_EVENT, RESEARCH_RESULT_EVENT,
    ADVICE_REQUEST_EVENT, ADVICE_RESULT_EVENT,
    VALIDATION_REQUEST_EVENT, VALIDATION_RESULT_EVENT
)

RESEARCH_CAPABILITY = AgentCapability(
    task_name="perform_web_research",
    description="Performs web research on a given topic",
    consumed_event=RESEARCH_REQUEST_EVENT.event_name,
    produced_events=[RESEARCH_RESULT_EVENT.event_name]
)

ADVICE_CAPABILITY = AgentCapability(
    task_name="draft_response",
    description="Drafts a response or advice based on research context",
    consumed_event=ADVICE_REQUEST_EVENT.event_name,
    produced_events=[ADVICE_RESULT_EVENT.event_name]
)

VALIDATION_CAPABILITY = AgentCapability(
    task_name="validate_content",
    description="Validates content accuracy against source material",
    consumed_event=VALIDATION_REQUEST_EVENT.event_name,
    produced_events=[VALIDATION_RESULT_EVENT.event_name]
)
