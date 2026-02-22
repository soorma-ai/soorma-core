"""
Tests for TrackerServiceClient (Layer 1 - Low-level HTTP client).

These tests verify the service client methods with mocked HTTP responses.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, UTC

from soorma.tracker.client import TrackerServiceClient
from soorma_common.tracker import (
    PlanProgress,
    TaskExecution,
    EventTimeline,
    EventTimelineEntry,
    AgentMetrics,
    PlanExecution,
    DelegationGroup,
)
from soorma_common.tracking import TaskState


@pytest.fixture
def tracker_client():
    """Create TrackerServiceClient instance."""
    return TrackerServiceClient(base_url="http://localhost:8084")


@pytest.fixture
def mock_auth():
    """Mock authentication headers."""
    return {
        "tenant_id": "tenant-123",
        "user_id": "user-456",
    }


class TestGetPlanProgress:
    """Tests for get_plan_progress method."""
    
    @pytest.mark.asyncio
    async def test_get_plan_progress_success(self, tracker_client, mock_auth):
        """Test successful plan progress retrieval."""
        plan_id = "plan-abc"
        now = datetime.now(UTC).isoformat()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "plan_id": plan_id,
            "status": "running",
            "started_at": now,
            "completed_at": None,
            "task_count": 5,
            "completed_tasks": 2,
            "failed_tasks": 0,
            "current_state": "reasoning",
        }
        mock_response.raise_for_status = MagicMock()
        
        tracker_client._client = AsyncMock()
        tracker_client._client.get = AsyncMock(return_value=mock_response)
        
        result = await tracker_client.get_plan_progress(
            plan_id=plan_id,
            tenant_id=mock_auth["tenant_id"],
            user_id=mock_auth["user_id"],
        )
        
        assert isinstance(result, PlanProgress)
        assert result.plan_id == plan_id
        assert result.status == "running"
        assert result.task_count == 5
        assert result.completed_tasks == 2
        
        # Verify headers were sent
        tracker_client._client.get.assert_called_once()
        call_args = tracker_client._client.get.call_args
        assert call_args.kwargs["headers"]["X-Tenant-ID"] == mock_auth["tenant_id"]
        assert call_args.kwargs["headers"]["X-User-ID"] == mock_auth["user_id"]
    
    @pytest.mark.asyncio
    async def test_get_plan_progress_not_found(self, tracker_client, mock_auth):
        """Test plan not found returns None."""
        import httpx
        
        plan_id = "plan-nonexistent"
        
        mock_response = MagicMock()
        mock_response.status_code = 404
        
        # Create proper HTTPStatusError
        error = httpx.HTTPStatusError(
            "404 Not Found",
            request=MagicMock(),
            response=mock_response,
        )
        mock_response.raise_for_status = MagicMock(side_effect=error)
        
        tracker_client._client = AsyncMock()
        tracker_client._client.get = AsyncMock(return_value=mock_response)
        
        result = await tracker_client.get_plan_progress(
            plan_id=plan_id,
            tenant_id=mock_auth["tenant_id"],
            user_id=mock_auth["user_id"],
        )
        
        assert result is None


class TestGetPlanTasks:
    """Tests for get_plan_tasks method."""
    
    @pytest.mark.asyncio
    async def test_get_plan_tasks_success(self, tracker_client, mock_auth):
        """Test successful task list retrieval."""
        plan_id = "plan-abc"
        now = datetime.now(UTC).isoformat()
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "task_id": "task-1",
                "event_type": "search.requested",
                "state": "completed",
                "started_at": now,
                "completed_at": now,
                "duration_seconds": 2.5,
                "progress": 1.0,
            },
            {
                "task_id": "task-2",
                "event_type": "analyze.requested",
                "state": "running",
                "started_at": now,
                "completed_at": None,
                "duration_seconds": None,
                "progress": 0.3,
            },
        ]
        mock_response.raise_for_status = MagicMock()
        
        tracker_client._client = AsyncMock()
        tracker_client._client.get = AsyncMock(return_value=mock_response)
        
        result = await tracker_client.get_plan_tasks(
            plan_id=plan_id,
            tenant_id=mock_auth["tenant_id"],
            user_id=mock_auth["user_id"],
        )
        
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(task, TaskExecution) for task in result)
        assert result[0].task_id == "task-1"
        assert result[0].state == TaskState.COMPLETED
        assert result[1].state == TaskState.RUNNING


class TestGetPlanTimeline:
    """Tests for get_plan_timeline method."""
    
    @pytest.mark.asyncio
    async def test_get_plan_timeline_success(self, tracker_client, mock_auth):
        """Test successful timeline retrieval."""
        plan_id = "plan-abc"
        now = datetime.now(UTC).isoformat()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "trace_id": "trace-xyz",
            "events": [
                {
                    "event_id": "event-1",
                    "event_type": "goal.requested",
                    "timestamp": now,
                    "parent_event_id": None,
                },
                {
                    "event_id": "event-2",
                    "event_type": "search.requested",
                    "timestamp": now,
                    "parent_event_id": "event-1",
                },
            ],
        }
        mock_response.raise_for_status = MagicMock()
        
        tracker_client._client = AsyncMock()
        tracker_client._client.get = AsyncMock(return_value=mock_response)
        
        result = await tracker_client.get_plan_timeline(
            plan_id=plan_id,
            tenant_id=mock_auth["tenant_id"],
            user_id=mock_auth["user_id"],
        )
        
        assert isinstance(result, EventTimeline)
        assert result.trace_id == "trace-xyz"
        assert len(result.events) == 2
        assert result.events[1].parent_event_id == "event-1"


class TestQueryAgentMetrics:
    """Tests for query_agent_metrics method."""
    
    @pytest.mark.asyncio
    async def test_query_agent_metrics_success(self, tracker_client, mock_auth):
        """Test successful metrics query."""
        agent_id = "worker-search"
        period = "7d"
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "agent_id": agent_id,
            "period": period,
            "total_tasks": 100,
            "completed_tasks": 85,
            "failed_tasks": 10,
            "avg_duration_seconds": 2.5,
            "success_rate": 0.85,
        }
        mock_response.raise_for_status = MagicMock()
        
        tracker_client._client = AsyncMock()
        tracker_client._client.get = AsyncMock(return_value=mock_response)
        
        result = await tracker_client.query_agent_metrics(
            agent_id=agent_id,
            period=period,
            tenant_id=mock_auth["tenant_id"],
            user_id=mock_auth["user_id"],
        )
        
        assert isinstance(result, AgentMetrics)
        assert result.agent_id == agent_id
        assert result.total_tasks == 100
        assert result.success_rate == 0.85


class TestHierarchyMethods:
    """Tests for plan hierarchy and delegation methods."""
    
    @pytest.mark.asyncio
    async def test_get_sub_plans(self, tracker_client, mock_auth):
        """Test get_sub_plans retrieves child plans."""
        plan_id = "plan-parent"
        now = datetime.now(UTC).isoformat()
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "plan_id": "plan-child-1",
                "parent_plan_id": plan_id,
                "session_id": "session-123",
                "goal_event": "sub_goal.1",
                "status": "completed",
                "current_state": "finished",
                "trace_id": "trace-abc",
                "started_at": now,
                "completed_at": now,
            },
        ]
        mock_response.raise_for_status = MagicMock()
        
        tracker_client._client = AsyncMock()
        tracker_client._client.get = AsyncMock(return_value=mock_response)
        
        result = await tracker_client.get_sub_plans(
            plan_id=plan_id,
            tenant_id=mock_auth["tenant_id"],
            user_id=mock_auth["user_id"],
        )
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].parent_plan_id == plan_id
    
    @pytest.mark.asyncio
    async def test_get_session_plans(self, tracker_client, mock_auth):
        """Test get_session_plans retrieves all plans in session."""
        session_id = "session-123"
        now = datetime.now(UTC).isoformat()
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "plan_id": "plan-1",
                "parent_plan_id": None,
                "session_id": session_id,
                "goal_event": "research.goal",
                "status": "completed",
                "current_state": None,
                "trace_id": "trace-1",
                "started_at": now,
                "completed_at": now,
            },
        ]
        mock_response.raise_for_status = MagicMock()
        
        tracker_client._client = AsyncMock()
        tracker_client._client.get = AsyncMock(return_value=mock_response)
        
        result = await tracker_client.get_session_plans(
            session_id=session_id,
            tenant_id=mock_auth["tenant_id"],
            user_id=mock_auth["user_id"],
        )
        
        assert isinstance(result, list)
        assert result[0].session_id == session_id
    
    @pytest.mark.asyncio
    async def test_get_delegation_group(self, tracker_client, mock_auth):
        """Test get_delegation_group retrieves parallel task group."""
        group_id = "group-parallel-123"
        now = datetime.now(UTC).isoformat()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "group_id": group_id,
            "parent_task_id": "task-fanout",
            "plan_id": "plan-456",
            "total_tasks": 5,
            "completed_tasks": 3,
            "created_at": now,
        }
        mock_response.raise_for_status = MagicMock()
        
        tracker_client._client = AsyncMock()
        tracker_client._client.get = AsyncMock(return_value=mock_response)
        
        result = await tracker_client.get_delegation_group(
            group_id=group_id,
            tenant_id=mock_auth["tenant_id"],
            user_id=mock_auth["user_id"],
        )
        
        assert isinstance(result, DelegationGroup)
        assert result.group_id == group_id
        assert result.total_tasks == 5
        assert result.completed_tasks == 3


class TestClientLifecycle:
    """Tests for client lifecycle methods."""
    
    @pytest.mark.asyncio
    async def test_client_context_manager(self):
        """Test client can be used as async context manager."""
        async with TrackerServiceClient() as client:
            assert client is not None
            assert client._client is not None
    
    @pytest.mark.asyncio
    async def test_client_close(self):
        """Test client close method."""
        client = TrackerServiceClient()
        await client.close()
        # If no exception, test passes

