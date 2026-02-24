"""
Tracker Service response DTOs.

These models represent responses from Tracker Service query APIs,
used for observability and debugging of plan/task execution.

Distinct from tracking.py (progress events) - these are read responses.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from soorma_common.tracking import TaskState


class PlanProgress(BaseModel):
    """Plan execution progress summary."""
    
    plan_id: str
    status: str  # running, completed, failed, paused
    started_at: datetime
    completed_at: Optional[datetime] = None
    task_count: int
    completed_tasks: int
    failed_tasks: int
    current_state: Optional[str] = None


class TaskExecution(BaseModel):
    """Task execution record."""
    
    task_id: str
    event_type: str
    state: TaskState
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    progress: Optional[float] = Field(None, ge=0.0, le=1.0)


class EventTimelineEntry(BaseModel):
    """Event timeline entry."""
    
    event_id: str
    event_type: str
    timestamp: datetime
    parent_event_id: Optional[str] = None


class EventTimeline(BaseModel):
    """Event execution timeline."""
    
    trace_id: str
    events: List[EventTimelineEntry]


class AgentMetrics(BaseModel):
    """Agent performance metrics."""
    
    agent_id: str
    period: str  # e.g., "7d", "30d", "1h"
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    avg_duration_seconds: float
    success_rate: float = Field(ge=0.0, le=1.0)


class PlanExecution(BaseModel):
    """Plan execution record with hierarchy."""
    
    plan_id: str
    parent_plan_id: Optional[str] = None  # For nested plans
    session_id: Optional[str] = None       # For conversation tracking
    goal_event: str
    status: str  # pending|running|completed|failed|paused
    current_state: Optional[str] = None    # State machine current state
    trace_id: str                          # Root workflow trace
    started_at: datetime
    completed_at: Optional[datetime] = None


class DelegationGroup(BaseModel):
    """Parallel delegation group tracking."""
    
    group_id: str
    parent_task_id: str
    plan_id: Optional[str] = None
    total_tasks: int
    completed_tasks: int
    created_at: datetime
