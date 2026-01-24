"""
Progress tracking and task state DTOs.

Used by Workers/Planners to publish progress events
and by Tracker Service to subscribe to progress events.
"""
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class TaskState(str, Enum):
    """Standard task states."""
    
    PENDING = "pending"
    RUNNING = "running"
    DELEGATED = "delegated"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskProgressEvent(BaseModel):
    """Progress update event payload."""
    
    task_id: str
    plan_id: Optional[str] = None
    state: TaskState
    progress: Optional[float] = Field(None, ge=0.0, le=1.0, description="0.0 to 1.0")
    message: Optional[str] = None


class TaskStateChanged(BaseModel):
    """State transition event payload."""
    
    task_id: str
    plan_id: Optional[str] = None
    previous_state: TaskState
    new_state: TaskState
    reason: Optional[str] = None
