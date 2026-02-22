"""
Tests for TrackerClient wrapper (Layer 2 - High-level agent API).

These tests verify the wrapper methods delegate correctly to
TrackerServiceClient and handle tenant/user context properly.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, UTC

from soorma.context import TrackerClient
from soorma.tracker.client import TrackerServiceClient
from soorma_common.tracker import (
    PlanProgress,
    TaskExecution,
    EventTimeline,
    AgentMetrics,
    PlanExecution,
    DelegationGroup,
)
from soorma_common.tracking import TaskState


@pytest.fixture
def tracker_wrapper():
    """Create TrackerClient wrapper instance."""
    return TrackerClient(base_url="http://localhost:8084")


@pytest.fixture
def mock_service_client():
    """Create mocked TrackerServiceClient."""
    return AsyncMock(spec=TrackerServiceClient)


class TestTrackerClientWrapper:
    """Tests for TrackerClient high-level wrapper."""
    
    @pytest.mark.asyncio
    async def test_get_plan_progress_delegates_to_service_client(
        self, tracker_wrapper, mock_service_client
    ):
        """Test get_plan_progress delegates to service client."""
        plan_id = "plan-abc"
        tenant_id = "tenant-123"
        user_id = "user-456"
        
        # Mock service client response
        mock_progress = PlanProgress(
            plan_id=plan_id,
            status="running",
            started_at=datetime.now(UTC),
            task_count=5,
            completed_tasks=2,
            failed_tasks=0,
        )
        mock_service_client.get_plan_progress = AsyncMock(return_value=mock_progress)
        
        # Inject mocked service client
        tracker_wrapper._client = mock_service_client
        
        # Call wrapper method
        result = await tracker_wrapper.get_plan_progress(
            plan_id=plan_id,
            tenant_id=tenant_id,
            user_id=user_id,
        )
        
        # Verify delegation
        assert result == mock_progress
        mock_service_client.get_plan_progress.assert_called_once_with(
            plan_id, tenant_id, user_id
        )
    
    @pytest.mark.asyncio
    async def test_get_plan_tasks_delegates(
        self, tracker_wrapper, mock_service_client
    ):
        """Test get_plan_tasks delegates to service client."""
        plan_id = "plan-abc"
        tenant_id = "tenant-123"
        user_id = "user-456"
        
        mock_tasks = [
            TaskExecution(
                task_id="task-1",
                event_type="search.requested",
                state=TaskState.COMPLETED,
                started_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
                duration_seconds=2.5,
                progress=1.0,
            ),
        ]
        mock_service_client.get_plan_tasks = AsyncMock(return_value=mock_tasks)
        tracker_wrapper._client = mock_service_client
        
        result = await tracker_wrapper.get_plan_tasks(
            plan_id=plan_id,
            tenant_id=tenant_id,
            user_id=user_id,
        )
        
        assert result == mock_tasks
        mock_service_client.get_plan_tasks.assert_called_once_with(
            plan_id, tenant_id, user_id
        )
    
    @pytest.mark.asyncio
    async def test_get_plan_timeline_delegates(
        self, tracker_wrapper, mock_service_client
    ):
        """Test get_plan_timeline delegates to service client."""
        plan_id = "plan-abc"
        tenant_id = "tenant-123"
        user_id = "user-456"
        
        mock_timeline = EventTimeline(
            trace_id="trace-xyz",
            events=[],
        )
        mock_service_client.get_plan_timeline = AsyncMock(return_value=mock_timeline)
        tracker_wrapper._client = mock_service_client
        
        result = await tracker_wrapper.get_plan_timeline(
            plan_id=plan_id,
            tenant_id=tenant_id,
            user_id=user_id,
        )
        
        assert result == mock_timeline
        mock_service_client.get_plan_timeline.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_query_agent_metrics_delegates(
        self, tracker_wrapper, mock_service_client
    ):
        """Test query_agent_metrics delegates to service client."""
        agent_id = "worker-search"
        period = "7d"
        tenant_id = "tenant-123"
        user_id = "user-456"
        
        mock_metrics = AgentMetrics(
            agent_id=agent_id,
            period=period,
            total_tasks=100,
            completed_tasks=85,
            failed_tasks=10,
            avg_duration_seconds=2.5,
            success_rate=0.85,
        )
        mock_service_client.query_agent_metrics = AsyncMock(return_value=mock_metrics)
        tracker_wrapper._client = mock_service_client
        
        result = await tracker_wrapper.query_agent_metrics(
            agent_id=agent_id,
            period=period,
            tenant_id=tenant_id,
            user_id=user_id,
        )
        
        assert result == mock_metrics
        mock_service_client.query_agent_metrics.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_sub_plans_delegates(
        self, tracker_wrapper, mock_service_client
    ):
        """Test get_sub_plans delegates to service client."""
        plan_id = "plan-parent"
        tenant_id = "tenant-123"
        user_id = "user-456"
        
        mock_plans = [
            PlanExecution(
                plan_id="plan-child",
                parent_plan_id=plan_id,
                session_id="session-123",
                goal_event="sub_goal",
                status="completed",
                trace_id="trace-abc",
                started_at=datetime.now(UTC),
            ),
        ]
        mock_service_client.get_sub_plans = AsyncMock(return_value=mock_plans)
        tracker_wrapper._client = mock_service_client
        
        result = await tracker_wrapper.get_sub_plans(
            plan_id=plan_id,
            tenant_id=tenant_id,
            user_id=user_id,
        )
        
        assert result == mock_plans
    
    @pytest.mark.asyncio
    async def test_ensure_client_creates_service_client(self, tracker_wrapper):
        """Test _ensure_client creates TrackerServiceClient on first call."""
        assert tracker_wrapper._client is None
        
        client = await tracker_wrapper._ensure_client()
        
        assert client is not None
        assert isinstance(client, TrackerServiceClient)
        assert tracker_wrapper._client is client
        
        # Second call returns same instance
        client2 = await tracker_wrapper._ensure_client()
        assert client2 is client
