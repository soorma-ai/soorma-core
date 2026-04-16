"""Tests for Tracker Query API endpoints (RED phase).

These tests assert REAL expected behavior. Initially they will fail with
NotImplementedError from the stub implementation. After GREEN phase, they
should all pass.
"""

import pytest
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from tracker_service.main import app
from tracker_service.models.db import PlanProgress, ActionProgress, ActionStatus, PlanStatus
from .conftest import build_auth_headers


PLATFORM_TENANT = "spt_test-tenant"
SERVICE_TENANT = "st_tenant-1"
SERVICE_USER = "su_user-1"


class TestGetPlanProgress:
    """Tests for GET /v1/tracker/plans/{plan_id}."""

    @pytest.mark.asyncio
    async def test_get_plan_progress_returns_progress(
        self, db_session: AsyncSession, override_get_db
    ):
        """Test that get_plan_progress returns PlanProgress DTO for existing plan."""
        # Arrange: Insert plan_progress record
        plan_id = "plan-123"
        service_tenant_id = SERVICE_TENANT
        service_user_id = SERVICE_USER
        
        # Insert via SQLAlchemy to simulate existing data
        plan_progress = PlanProgress(
            plan_id=plan_id,
            platform_tenant_id=PLATFORM_TENANT,
            service_tenant_id=service_tenant_id,
            service_user_id=service_user_id,
            status=PlanStatus.IN_PROGRESS,
            total_actions=5,
            completed_actions=2,
            failed_actions=1,
            started_at=datetime.now(timezone.utc),
        )
        db_session.add(plan_progress)
        await db_session.commit()

        # Act: Call API endpoint
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                f"/v1/tracker/plans/{plan_id}",
                headers=build_auth_headers(PLATFORM_TENANT, service_tenant_id, service_user_id),
            )

        # Assert: Returns 200 with PlanProgress DTO
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Validate DTO fields
        assert data["plan_id"] == plan_id
        assert data["status"] == PlanStatus.IN_PROGRESS
        assert data["task_count"] == 5
        assert data["completed_tasks"] == 2
        assert data["failed_tasks"] == 1
        assert "started_at" in data

    @pytest.mark.asyncio
    async def test_get_plan_progress_404_not_found(
        self, db_session: AsyncSession, override_get_db
    ):
        """Test that get_plan_progress returns 404 when plan doesn't exist."""
        # Act: Call API with non-existent plan_id
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/v1/tracker/plans/nonexistent-plan",
                headers=build_auth_headers(PLATFORM_TENANT, SERVICE_TENANT, SERVICE_USER),
            )

        # Assert: Returns 404
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"

    @pytest.mark.asyncio
    async def test_get_plan_progress_filters_by_tenant(
        self, db_session: AsyncSession, override_get_db
    ):
        """Test that get_plan_progress filters by tenant_id (multi-tenancy)."""
        # Arrange: Insert plan_progress for tenant-1
        plan_id = "plan-456"
        
        plan_progress = PlanProgress(
            plan_id=plan_id,
            platform_tenant_id=PLATFORM_TENANT,
            service_tenant_id=SERVICE_TENANT,
            service_user_id=SERVICE_USER,
            status=PlanStatus.IN_PROGRESS,
            total_actions=3,
            completed_actions=0,
            failed_actions=0,
            started_at=datetime.now(timezone.utc),
        )
        db_session.add(plan_progress)
        await db_session.commit()

        # Act: Call API with a different service tenant header
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                f"/v1/tracker/plans/{plan_id}",
                headers=build_auth_headers(PLATFORM_TENANT, "st_other-tenant", SERVICE_USER),
            )

        # Assert: Returns 404 (plan exists but tenant filter blocks it)
        assert response.status_code == 404, f"Expected 404 due to tenant mismatch, got {response.status_code}"

    @pytest.mark.asyncio
    async def test_get_plan_progress_requires_service_tenant_header(
        self, db_session: AsyncSession, override_get_db
    ):
        """Test that get_plan_progress requires X-Service-Tenant-ID."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/v1/tracker/plans/plan-123",
                headers=build_auth_headers(
                    PLATFORM_TENANT,
                    SERVICE_TENANT,
                    SERVICE_USER,
                    include_service_tenant_header=False,
                ),
            )

        assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"


class TestGetPlanActions:
    """Tests for GET /v1/tracker/plans/{plan_id}/actions."""

    @pytest.mark.asyncio
    async def test_get_plan_actions_returns_list(
        self, db_session: AsyncSession, override_get_db
    ):
        """Test that get_plan_actions returns List[TaskExecution]."""
        # Arrange: Insert action_progress records
        plan_id = "plan-789"
        service_tenant_id = SERVICE_TENANT
        service_user_id = SERVICE_USER
        
        # Insert plan first
        plan_progress = PlanProgress(
            plan_id=plan_id,
            platform_tenant_id=PLATFORM_TENANT,
            service_tenant_id=service_tenant_id,
            service_user_id=service_user_id,
            status=PlanStatus.IN_PROGRESS,
            total_actions=2,
            completed_actions=1,
            failed_actions=0,
            started_at=datetime.now(timezone.utc),
        )
        db_session.add(plan_progress)
        
        # Insert action executions
        action1 = ActionProgress(
            action_id="action-1",
            plan_id=plan_id,
            platform_tenant_id=PLATFORM_TENANT,
            service_tenant_id=service_tenant_id,
            service_user_id=service_user_id,
            action_name="Research Task",
            action_type="research.requested",
            assigned_to="worker-1",
            status=ActionStatus.COMPLETED,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        action2 = ActionProgress(
            action_id="action-2",
            plan_id=plan_id,
            platform_tenant_id=PLATFORM_TENANT,
            service_tenant_id=service_tenant_id,
            service_user_id=service_user_id,
            action_name="Search Task",
            action_type="search.requested",
            assigned_to="worker-2",
            status=ActionStatus.PENDING,
            started_at=datetime.now(timezone.utc),
        )
        db_session.add(action1)
        db_session.add(action2)
        await db_session.commit()

        # Act: Call API endpoint
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                f"/v1/tracker/plans/{plan_id}/actions",
                headers=build_auth_headers(PLATFORM_TENANT, service_tenant_id, service_user_id),
            )

        # Assert: Returns 200 with List[TaskExecution]
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Validate list response
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        assert len(data) == 2, f"Expected 2 actions, got {len(data)}"
        
        # Validate TaskExecution DTOs (order may vary)
        task_ids = [item["task_id"] for item in data]  # TaskExecution uses task_id, not action_id
        assert "action-1" in task_ids
        assert "action-2" in task_ids

    @pytest.mark.asyncio
    async def test_get_plan_actions_empty_list(
        self, db_session: AsyncSession, override_get_db
    ):
        """Test that get_plan_actions returns empty list when no actions exist."""
        # Arrange: Insert plan without actions
        plan_id = "plan-empty"
        service_tenant_id = SERVICE_TENANT
        service_user_id = SERVICE_USER
        
        plan_progress = PlanProgress(
            plan_id=plan_id,
            platform_tenant_id=PLATFORM_TENANT,
            service_tenant_id=service_tenant_id,
            service_user_id=service_user_id,
            status=PlanStatus.PENDING,
            total_actions=0,
            completed_actions=0,
            failed_actions=0,
            started_at=datetime.now(timezone.utc),
        )
        db_session.add(plan_progress)
        await db_session.commit()

        # Act: Call API endpoint
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                f"/v1/tracker/plans/{plan_id}/actions",
                headers=build_auth_headers(PLATFORM_TENANT, service_tenant_id, service_user_id),
            )

        # Assert: Returns 200 with empty list
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        assert len(data) == 0, f"Expected empty list, got {len(data)} items"

    @pytest.mark.asyncio
    async def test_get_plan_actions_filters_by_tenant(
        self, db_session: AsyncSession, override_get_db
    ):
        """Test that get_plan_actions filters by tenant_id."""
        # Arrange: Insert actions for tenant-1
        plan_id = "plan-999"
        
        plan_progress = PlanProgress(
            plan_id=plan_id,
            platform_tenant_id=PLATFORM_TENANT,
            service_tenant_id=SERVICE_TENANT,
            service_user_id=SERVICE_USER,
            status=PlanStatus.IN_PROGRESS,
            total_actions=1,
            completed_actions=0,
            failed_actions=0,
            started_at=datetime.now(timezone.utc),
        )
        db_session.add(plan_progress)
        
        action = ActionProgress(
            action_id="action-secret",
            plan_id=plan_id,
            platform_tenant_id=PLATFORM_TENANT,
            service_tenant_id=SERVICE_TENANT,
            service_user_id=SERVICE_USER,
            action_name="Secret Task",
            action_type="research.requested",
            assigned_to="worker-1",
            status=ActionStatus.PENDING,
            started_at=datetime.now(timezone.utc),
        )
        db_session.add(action)
        await db_session.commit()

        # Act: Call API with tenant-2 header
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                f"/v1/tracker/plans/{plan_id}/actions",
                headers=build_auth_headers(PLATFORM_TENANT, "st_other-tenant", SERVICE_USER),
            )

        # Assert: Returns empty list (actions exist but tenant filter blocks)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert len(data) == 0, f"Expected empty list due to tenant mismatch, got {len(data)} items"
