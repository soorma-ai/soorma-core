"""Tests for plan context functionality.

Following TDD pattern to verify plan_id direct-string behavior (Migration 008).

Key Requirement (post-008 migration):
- plan_context.plan_id is now a VARCHAR(100) direct string — NO UUID FK to plans.id
- Service layer passes string plan_id directly to CRUD (no UUID lookup indirection)
- Identity: platform_tenant_id (str), NOT tenant_id (UUID)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from memory_service.services.plan_context_service import plan_context_service
from soorma_common.models import PlanContextCreate, PlanContextUpdate

TEST_PLATFORM_TENANT_ID = "spt_test-00000"
TEST_SERVICE_TENANT_ID = "st_test-tenant"
TEST_PLAN_ID = "test-plan-123"
TEST_SESSION_ID = "test-session-456"


class TestPlanContextService:
    """Test plan context service layer (direct string plan_id)."""

    @pytest.fixture
    def test_ids(self):
        """Generate test IDs."""
        return {
            "platform_tenant_id": TEST_PLATFORM_TENANT_ID,
            "service_tenant_id": TEST_SERVICE_TENANT_ID,
            "plan_id": TEST_PLAN_ID,
            "session_id": TEST_SESSION_ID,
        }

    async def test_upsert_plan_context_with_string_plan_id(
        self, db_session: AsyncSession, test_ids
    ):
        """Test creating plan context with string plan_id (direct, no lookup)."""
        # GIVEN: PlanContextCreate uses a string plan_id
        plan_context_data = PlanContextCreate(
            plan_id=test_ids["plan_id"],
            session_id=test_ids["session_id"],
            goal_event="research.goal",
            goal_data={"topic": "AI"},
            response_event="research.completed",
            state={"status": "running", "current_state": "start"},
            current_state="start",
            correlation_ids=["corr-123"],
        )

        # WHEN: Upserting plan context via service
        result = await plan_context_service.upsert(
            db=db_session,
            platform_tenant_id=test_ids["platform_tenant_id"],
            data=plan_context_data,
        )

        # THEN: Plan context should be created with the string plan_id directly
        assert result is not None
        assert result.plan_id == test_ids["plan_id"]
        assert result.goal_event == "research.goal"
        assert result.current_state == "start"

    async def test_get_plan_context(
        self, db_session: AsyncSession, test_ids
    ):
        """Test retrieving plan context by string plan_id."""
        plan_context_data = PlanContextCreate(
            plan_id=test_ids["plan_id"],
            session_id=test_ids["session_id"],
            goal_event="research.goal",
            goal_data={"topic": "AI"},
            response_event="research.completed",
            state={"status": "running"},
            current_state="start",
            correlation_ids=["corr-123"],
        )
        await plan_context_service.upsert(
            db=db_session,
            platform_tenant_id=test_ids["platform_tenant_id"],
            data=plan_context_data,
        )

        result = await plan_context_service.get(
            db=db_session,
            platform_tenant_id=test_ids["platform_tenant_id"],
            plan_id=test_ids["plan_id"],
        )

        assert result is not None
        assert result.goal_event == "research.goal"
        assert result.current_state == "start"

    async def test_get_plan_context_not_found(
        self, db_session: AsyncSession, test_ids
    ):
        """Test retrieving nonexistent plan context returns None."""
        result = await plan_context_service.get(
            db=db_session,
            platform_tenant_id=test_ids["platform_tenant_id"],
            plan_id="nonexistent-plan",
        )
        assert result is None

    async def test_update_plan_context(
        self, db_session: AsyncSession, test_ids
    ):
        """Test updating plan context state."""
        plan_context_data = PlanContextCreate(
            plan_id=test_ids["plan_id"],
            session_id=test_ids["session_id"],
            goal_event="research.goal",
            goal_data={"topic": "AI"},
            response_event="research.completed",
            state={"status": "running"},
            current_state="start",
            correlation_ids=["corr-123"],
        )
        await plan_context_service.upsert(
            db=db_session,
            platform_tenant_id=test_ids["platform_tenant_id"],
            data=plan_context_data,
        )

        update_data = PlanContextUpdate(
            state={"status": "running", "progress": 0.5},
            current_state="research",
            correlation_ids=["corr-123", "corr-456"],
        )
        result = await plan_context_service.update(
            db=db_session,
            platform_tenant_id=test_ids["platform_tenant_id"],
            plan_id=test_ids["plan_id"],
            data=update_data,
        )

        assert result is not None
        assert result.current_state == "research"
        assert result.state["progress"] == 0.5
        assert len(result.correlation_ids) == 2

    async def test_delete_plan_context(
        self, db_session: AsyncSession, test_ids
    ):
        """Test deleting plan context."""
        plan_context_data = PlanContextCreate(
            plan_id=test_ids["plan_id"],
            session_id=test_ids["session_id"],
            goal_event="research.goal",
            goal_data={"topic": "AI"},
            response_event="research.completed",
            state={"status": "running"},
            current_state="start",
            correlation_ids=[],
        )
        await plan_context_service.upsert(
            db=db_session,
            platform_tenant_id=test_ids["platform_tenant_id"],
            data=plan_context_data,
        )

        deleted = await plan_context_service.delete(
            db=db_session,
            platform_tenant_id=test_ids["platform_tenant_id"],
            plan_id=test_ids["plan_id"],
        )
        assert deleted is True

        result = await plan_context_service.get(
            db=db_session,
            platform_tenant_id=test_ids["platform_tenant_id"],
            plan_id=test_ids["plan_id"],
        )
        assert result is None
