"""Tests for tracking DTOs."""

import pytest
from soorma_common.tracking import (
    TaskState,
    TaskProgressEvent,
    TaskStateChanged,
)


def test_task_state():
    """Test TaskState enum."""
    assert TaskState.PENDING == "pending"
    assert TaskState.RUNNING == "running"
    assert TaskState.DELEGATED == "delegated"
    assert TaskState.WAITING == "waiting"
    assert TaskState.COMPLETED == "completed"
    assert TaskState.FAILED == "failed"
    assert TaskState.CANCELLED == "cancelled"


def test_task_progress_event():
    """Test TaskProgressEvent validation."""
    event = TaskProgressEvent(
        task_id="task-123",
        plan_id="plan-456",
        state=TaskState.RUNNING,
        progress=0.5,
        message="Halfway done",
    )
    
    assert event.task_id == "task-123"
    assert event.plan_id == "plan-456"
    assert event.state == TaskState.RUNNING
    assert event.progress == 0.5
    assert event.message == "Halfway done"


def test_task_progress_event_without_plan():
    """Test TaskProgressEvent without plan_id."""
    event = TaskProgressEvent(
        task_id="task-123",
        state=TaskState.COMPLETED,
        progress=1.0,
    )
    
    assert event.task_id == "task-123"
    assert event.plan_id is None
    assert event.state == TaskState.COMPLETED
    assert event.progress == 1.0


def test_task_progress_event_progress_validation():
    """Test TaskProgressEvent progress validation."""
    # Valid progress
    event1 = TaskProgressEvent(
        task_id="task-123",
        state=TaskState.RUNNING,
        progress=0.0,
    )
    assert event1.progress == 0.0
    
    event2 = TaskProgressEvent(
        task_id="task-123",
        state=TaskState.RUNNING,
        progress=1.0,
    )
    assert event2.progress == 1.0
    
    # Invalid progress should raise validation error
    with pytest.raises(Exception):  # Pydantic ValidationError
        TaskProgressEvent(
            task_id="task-123",
            state=TaskState.RUNNING,
            progress=1.5,  # > 1.0
        )
    
    with pytest.raises(Exception):  # Pydantic ValidationError
        TaskProgressEvent(
            task_id="task-123",
            state=TaskState.RUNNING,
            progress=-0.1,  # < 0.0
        )


def test_task_state_changed():
    """Test TaskStateChanged validation."""
    event = TaskStateChanged(
        task_id="task-123",
        plan_id="plan-456",
        previous_state=TaskState.PENDING,
        new_state=TaskState.RUNNING,
        reason="Task started",
    )
    
    assert event.task_id == "task-123"
    assert event.plan_id == "plan-456"
    assert event.previous_state == TaskState.PENDING
    assert event.new_state == TaskState.RUNNING
    assert event.reason == "Task started"


def test_task_state_changed_without_reason():
    """Test TaskStateChanged without reason."""
    event = TaskStateChanged(
        task_id="task-123",
        previous_state=TaskState.RUNNING,
        new_state=TaskState.COMPLETED,
    )
    
    assert event.task_id == "task-123"
    assert event.reason is None
