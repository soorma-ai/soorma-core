"""
Tests for Tracker Service response DTOs.

These are responses from Tracker Service query APIs,
distinct from progress tracking events in test_tracking.py.
"""
import pytest
from datetime import datetime, UTC
from soorma_common.tracker import (
    PlanProgress,
    TaskExecution,
    EventTimelineEntry,
    EventTimeline,
    AgentMetrics,
    PlanExecution,
    DelegationGroup,
)
from soorma_common.tracking import TaskState


class TestPlanProgress:
    """Tests for PlanProgress response model."""
    
    def test_plan_progress_minimal(self):
        """Test PlanProgress with minimal required fields."""
        progress = PlanProgress(
            plan_id="plan-123",
            status="running",
            started_at=datetime.now(UTC),
            task_count=5,
            completed_tasks=2,
            failed_tasks=0,
        )
        assert progress.plan_id == "plan-123"
        assert progress.status == "running"
        assert progress.task_count == 5
        assert progress.completed_tasks == 2
        assert progress.failed_tasks == 0
        assert progress.completed_at is None
        assert progress.current_state is None
    
    def test_plan_progress_complete(self):
        """Test completed plan progress."""
        completed_at = datetime.now(UTC)
        progress = PlanProgress(
            plan_id="plan-456",
            status="completed",
            started_at=datetime.now(UTC),
            completed_at=completed_at,
            task_count=10,
            completed_tasks=10,
            failed_tasks=0,
            current_state="finished",
        )
        assert progress.status == "completed"
        assert progress.completed_at == completed_at
        assert progress.current_state == "finished"


class TestTaskExecution:
    """Tests for TaskExecution response model."""
    
    def test_task_execution_running(self):
        """Test task in running state."""
        task = TaskExecution(
            task_id="task-123",
            event_type="search.requested",
            state=TaskState.RUNNING,
            started_at=datetime.now(UTC),
            completed_at=None,
            duration_seconds=None,
            progress=0.5,
        )
        assert task.task_id == "task-123"
        assert task.state == TaskState.RUNNING
        assert task.progress == 0.5
        assert task.completed_at is None
    
    def test_task_execution_completed(self):
        """Test completed task with duration."""
        started = datetime.now(UTC)
        completed = datetime.now(UTC)
        task = TaskExecution(
            task_id="task-456",
            event_type="analysis.completed",
            state=TaskState.COMPLETED,
            started_at=started,
            completed_at=completed,
            duration_seconds=12.5,
            progress=1.0,
        )
        assert task.state == TaskState.COMPLETED
        assert task.duration_seconds == 12.5
        assert task.progress == 1.0


class TestEventTimeline:
    """Tests for EventTimeline and EventTimelineEntry models."""
    
    def test_event_timeline_entry(self):
        """Test single timeline entry."""
        entry = EventTimelineEntry(
            event_id="event-123",
            event_type="search.requested",
            timestamp=datetime.now(UTC),
            parent_event_id=None,
        )
        assert entry.event_id == "event-123"
        assert entry.event_type == "search.requested"
        assert entry.parent_event_id is None
    
    def test_event_timeline_with_hierarchy(self):
        """Test timeline with parent-child events."""
        timestamp = datetime.now(UTC)
        entries = [
            EventTimelineEntry(
                event_id="event-1",
                event_type="goal.requested",
                timestamp=timestamp,
                parent_event_id=None,
            ),
            EventTimelineEntry(
                event_id="event-2",
                event_type="search.requested",
                timestamp=timestamp,
                parent_event_id="event-1",
            ),
        ]
        timeline = EventTimeline(
            trace_id="trace-abc",
            events=entries,
        )
        assert timeline.trace_id == "trace-abc"
        assert len(timeline.events) == 2
        assert timeline.events[1].parent_event_id == "event-1"


class TestAgentMetrics:
    """Tests for AgentMetrics response model."""
    
    def test_agent_metrics_basic(self):
        """Test agent metrics calculation."""
        metrics = AgentMetrics(
            agent_id="worker-search",
            period="7d",
            total_tasks=100,
            completed_tasks=85,
            failed_tasks=10,
            avg_duration_seconds=2.5,
            success_rate=0.85,
        )
        assert metrics.agent_id == "worker-search"
        assert metrics.period == "7d"
        assert metrics.total_tasks == 100
        assert metrics.success_rate == 0.85
        assert metrics.avg_duration_seconds == 2.5


class TestPlanExecution:
    """Tests for PlanExecution model (plan hierarchy tracking)."""
    
    def test_plan_execution_root_plan(self):
        """Test root plan (no parent)."""
        plan = PlanExecution(
            plan_id="plan-root",
            parent_plan_id=None,
            session_id="session-123",
            goal_event="research.goal",
            status="running",
            current_state="reasoning",
            trace_id="trace-abc",
            started_at=datetime.now(UTC),
            completed_at=None,
        )
        assert plan.plan_id == "plan-root"
        assert plan.parent_plan_id is None
        assert plan.session_id == "session-123"
        assert plan.status == "running"
    
    def test_plan_execution_nested_plan(self):
        """Test nested plan (has parent)."""
        plan = PlanExecution(
            plan_id="plan-child",
            parent_plan_id="plan-root",
            session_id="session-123",
            goal_event="sub_research.goal",
            status="completed",
            current_state="finished",
            trace_id="trace-abc",
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        assert plan.parent_plan_id == "plan-root"
        assert plan.status == "completed"


class TestDelegationGroup:
    """Tests for DelegationGroup model (parallel task tracking)."""
    
    def test_delegation_group_in_progress(self):
        """Test delegation group with partial completion."""
        group = DelegationGroup(
            group_id="group-parallel-123",
            parent_task_id="task-fanout",
            plan_id="plan-456",
            total_tasks=5,
            completed_tasks=2,
            created_at=datetime.now(UTC),
        )
        assert group.group_id == "group-parallel-123"
        assert group.total_tasks == 5
        assert group.completed_tasks == 2
    
    def test_delegation_group_complete(self):
        """Test fully completed delegation group."""
        group = DelegationGroup(
            group_id="group-parallel-456",
            parent_task_id="task-fanout",
            plan_id="plan-789",
            total_tasks=3,
            completed_tasks=3,
            created_at=datetime.now(UTC),
        )
        assert group.completed_tasks == group.total_tasks
