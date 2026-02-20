"""Tests for plan context functionality.

Following TDD pattern to verify plan_id lookup behavior (Migration 007).

Key Requirement:
- plan_context.plan_id is a UUID FK to plans.id (not plans.plan_id string)
- Service layer MUST look up Plan by string plan_id to get UUID id
"""

import pytest
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from memory_service.crud.plans import create_plan
from memory_service.services.plan_context_service import plan_context_service
from soorma_common.models import PlanContextCreate, PlanContextUpdate


class TestPlanContextService:
    """Test plan context service layer with plan_id lookup."""

    @pytest.fixture
    def test_ids(self):
        """Generate test IDs."""
        return {
            "tenant_id": uuid4(),
            "user_id": uuid4(),
            "plan_id_string": "test-plan-123",  # User-facing string ID
            "session_id": "test-session-456",
        }

    @pytest.fixture
    async def created_plan(self, db_session: AsyncSession, test_ids):
        """Create a plan in the database to reference."""
        plan = await create_plan(
            db=db_session,
            tenant_id=test_ids["tenant_id"],
            user_id=test_ids["user_id"],
            plan_id=test_ids["plan_id_string"],
            session_id=test_ids["session_id"],
            goal_event="research.goal",
            goal_data={"topic": "AI"},
            parent_plan_id=None,
        )
        await db_session.commit()
        return plan

    async def test_create_plan_context_with_string_plan_id(
        self, db_session: AsyncSession, test_ids, created_plan
    ):
        """Test creating plan context with string plan_id (should lookup Plan UUID)."""
        # GIVEN: A plan exists with string plan_id "test-plan-123"
        # AND: PlanContextCreate uses the string plan_id
        plan_context_data = PlanContextCreate(
            plan_id=test_ids["plan_id_string"],  # String, not UUID
            session_id=test_ids["session_id"],
            goal_event="research.goal",
            goal_data={"topic": "AI"},
            response_event="research.completed",
            state={
                "status": "running",
                "current_state": "start",
            },
            current_state="start",
            correlation_ids=["corr-123"],
        )

        # WHEN: Upserting plan context via service
        result = await plan_context_service.upsert(
            db=db_session,
            tenant_id=test_ids["tenant_id"],
            data=plan_context_data,
        )

        # THEN: Plan context should be created successfully
        assert result is not None
        assert result.plan_id == str(created_plan.id)  # Should return UUID as string
        assert result.goal_event == "research.goal"
        assert result.current_state == "start"

    async def test_create_plan_context_plan_not_found(
        self, db_session: AsyncSession, test_ids
    ):
        """Test creating plan context fails when plan doesn't exist."""
        # GIVEN: No plan exists with this plan_id
        plan_context_data = PlanContextCreate(
            plan_id="nonexistent-plan",
            session_id=test_ids["session_id"],
            goal_event="research.goal",
            goal_data={"topic": "AI"},
            response_event="research.completed",
            state={},
            current_state="start",
            correlation_ids=[],
        )

        # WHEN/THEN: Upserting plan context should raise ValueError
        with pytest.raises(ValueError, match="Plan not found"):
            await plan_context_service.upsert(
                db=db_session,
                tenant_id=test_ids["tenant_id"],
                data=plan_context_data,
            )

    async def test_get_plan_context_with_string_plan_id(
        self, db_session: AsyncSession, test_ids, created_plan
    ):
        """Test retrieving plan context with string plan_id."""
        # GIVEN: A plan context exists
        plan_context_data = PlanContextCreate(
            plan_id=test_ids["plan_id_string"],
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
            tenant_id=test_ids["tenant_id"],
            data=plan_context_data,
        )

        # WHEN: Getting plan context by string plan_id
        result = await plan_context_service.get(
            db=db_session,
            tenant_id=test_ids["tenant_id"],
            plan_id=test_ids["plan_id_string"],  # String, not UUID
        )

        # THEN: Should return the plan context
        assert result is not None
        assert result.goal_event == "research.goal"
        assert result.current_state == "start"

    async def test_get_plan_context_not_found(
        self, db_session: AsyncSession, test_ids
    ):
        """Test retrieving nonexistent plan context returns None."""
        # WHEN: Getting plan context that doesn't exist
        result = await plan_context_service.get(
            db=db_session,
            tenant_id=test_ids["tenant_id"],
            plan_id="nonexistent-plan",
        )

        # THEN: Should return None
        assert result is None

    async def test_update_plan_context_with_string_plan_id(
        self, db_session: AsyncSession, test_ids, created_plan
    ):
        """Test updating plan context with string plan_id."""
        # GIVEN: A plan context exists
        plan_context_data = PlanContextCreate(
            plan_id=test_ids["plan_id_string"],
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
            tenant_id=test_ids["tenant_id"],
            data=plan_context_data,
        )

        # WHEN: Updating plan context
        update_data = PlanContextUpdate(
            state={"status": "running", "progress": 0.5},
            current_state="research",
            correlation_ids=["corr-123", "corr-456"],
        )
        result = await plan_context_service.update(
            db=db_session,
            tenant_id=test_ids["tenant_id"],
            plan_id=test_ids["plan_id_string"],  # String, not UUID
            data=update_data,
        )

        # THEN: Should update successfully
        assert result is not None
        assert result.current_state == "research"
        assert result.state["progress"] == 0.5
        assert len(result.correlation_ids) == 2

    async def test_delete_plan_context_with_string_plan_id(
        self, db_session: AsyncSession, test_ids, created_plan
    ):
        """Test deleting plan context with string plan_id."""
        # GIVEN: A plan context exists
        plan_context_data = PlanContextCreate(
            plan_id=test_ids["plan_id_string"],
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
            tenant_id=test_ids["tenant_id"],
            data=plan_context_data,
        )

        # WHEN: Deleting plan context
        deleted = await plan_context_service.delete(
            db=db_session,
            tenant_id=test_ids["tenant_id"],
            plan_id=test_ids["plan_id_string"],  # String, not UUID
        )

        # THEN: Should delete successfully
        assert deleted is True

        # AND: Plan context should no longer exist
        result = await plan_context_service.get(
            db=db_session,
            tenant_id=test_ids["tenant_id"],
            plan_id=test_ids["plan_id_string"],
        )
        assert result is None

    async def test_delete_plan_context_not_found(
        self, db_session: AsyncSession, test_ids
    ):
        """Test deleting nonexistent plan context returns False."""
        # WHEN: Deleting plan context that doesn't exist
        deleted = await plan_context_service.delete(
            db=db_session,
            tenant_id=test_ids["tenant_id"],
            plan_id="nonexistent-plan",
        )

        # THEN: Should return False
        assert deleted is False
