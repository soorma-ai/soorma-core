"""
Event Definitions for Feedback Analysis Choreography.

Defines the event schemas that workers consume and produce.
These are registered with the Registry service so the ChoreographyPlanner
can discover them and make intelligent routing decisions.
"""

from typing import Dict, List, Any
from pydantic import BaseModel, Field
from soorma_common import EventDefinition, EventTopic


# =============================================================================
# Payload Schemas
# =============================================================================

class DataFetchRequestPayload(BaseModel):
    """Request to fetch customer feedback data."""
    product: str = Field(..., description="Product name to fetch feedback for")
    sample_size: int = Field(default=3, description="Number of feedback entries to fetch")


class DataFetchedPayload(BaseModel):
    """Feedback data fetched from datastore."""
    product: str = Field(..., description="Product name")
    feedback: List[Dict[str, Any]] = Field(..., description="List of feedback entries")


class AnalysisRequestPayload(BaseModel):
    """Request to analyze feedback sentiment."""
    product: str = Field(..., description="Product being analyzed")
    feedback: List[Dict[str, Any]] = Field(..., description="Feedback entries to analyze")


class AnalysisCompletedPayload(BaseModel):
    """Analysis results."""
    product: str = Field(..., description="Product analyzed")
    summary: str = Field(..., description="Analysis summary")
    positive_count: int = Field(..., description="Number of positive feedback")
    negative_count: int = Field(..., description="Number of negative feedback")


class ReportRequestPayload(BaseModel):
    """Request to generate feedback report."""
    product: str = Field(..., description="Product name")
    summary: str = Field(..., description="Analysis summary")
    positive_count: int = Field(..., description="Positive feedback count")
    negative_count: int = Field(..., description="Negative feedback count")


class ReportReadyPayload(BaseModel):
    """Final feedback report."""
    product: str = Field(..., description="Product name")
    report: str = Field(..., description="Formatted report text")
    timestamp: str = Field(..., description="Report generation timestamp")


# =============================================================================
# Event Definitions
# =============================================================================

DATA_FETCH_REQUESTED_EVENT = EventDefinition(
    event_name="data.fetch.requested",
    topic=EventTopic.ACTION_REQUESTS,
    description="Request to fetch customer feedback data",
    payload_schema=DataFetchRequestPayload.model_json_schema(),
    response_schema=DataFetchedPayload.model_json_schema()
)

DATA_FETCHED_EVENT = EventDefinition(
    event_name="data.fetched",
    topic=EventTopic.ACTION_RESULTS,
    description="Customer feedback data fetched successfully",
    payload_schema=DataFetchedPayload.model_json_schema()
)

ANALYSIS_REQUESTED_EVENT = EventDefinition(
    event_name="analysis.requested",
    topic=EventTopic.ACTION_REQUESTS,
    description="Request to analyze feedback sentiment",
    payload_schema=AnalysisRequestPayload.model_json_schema(),
    response_schema=AnalysisCompletedPayload.model_json_schema()
)

ANALYSIS_COMPLETED_EVENT = EventDefinition(
    event_name="analysis.completed",
    topic=EventTopic.ACTION_RESULTS,
    description="Feedback analysis completed",
    payload_schema=AnalysisCompletedPayload.model_json_schema()
)

REPORT_REQUESTED_EVENT = EventDefinition(
    event_name="report.requested",
    topic=EventTopic.ACTION_REQUESTS,
    description="Request to generate feedback report",
    payload_schema=ReportRequestPayload.model_json_schema(),
    response_schema=ReportReadyPayload.model_json_schema()
)

REPORT_READY_EVENT = EventDefinition(
    event_name="report.ready",
    topic=EventTopic.ACTION_RESULTS,
    description="Feedback report generated and ready",
    payload_schema=ReportReadyPayload.model_json_schema()
)
