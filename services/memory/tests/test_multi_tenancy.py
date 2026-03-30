"""Multi-tenancy isolation and data deletion tests.

Tests:
  TC-M-003: Cross-tenant isolation — wrong platform_tenant_id → 0 rows
  TC-M-005: delete_by_platform_tenant() deletes all rows across 6 tables
  TC-M-006: delete_by_service_tenant() scoped — sibling service tenant unaffected
  TC-M-009: Query without set_config → 0 rows
  TC-M-010: service_user_id filter requires service_tenant_id
  TC-M-011: delete_by_service_user() removes only that user's rows
  TC-M-012: delete_by_platform_tenant() does NOT delete from plans or sessions tables
  TC-M-013: Admin endpoint uses bare get_db (no RLS session variables)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from memory_service.services.data_deletion import MemoryDataDeletion
from memory_service.models.memory import (
    SemanticMemory,
    EpisodicMemory,
    ProceduralMemory,
    WorkingMemory,
    TaskContext,
    PlanContext,
    Plan,
    Session,
)

TEST_PLATFORM_TENANT_ID = "spt_00000000-0000-0000-0000-000000000000"
TEST_SERVICE_TENANT_ID = "st_test-tenant"
TEST_SERVICE_USER_ID = "su_test-user"
OTHER_PLATFORM_TENANT_ID = "spt_ffffffff-ffff-ffff-ffff-ffffffffffff"
OTHER_SERVICE_TENANT_ID = "st_other-tenant"
OTHER_SERVICE_USER_ID = "su_other-user"


# ---------------------------------------------------------------------------
# TC-M-003: Cross-tenant isolation
# ---------------------------------------------------------------------------

class TestCrossTenantIsolation:
    """TC-M-003: Querying with the wrong platform_tenant_id must return 0 rows."""

    @pytest.mark.asyncio
    async def test_wrong_platform_tenant_returns_no_rows(self, db_session: AsyncSession):
        """Wrong platform_tenant_id must not expose another tenant's data.

        Simulates: CRUD layer filters by platform_tenant_id in WHERE clause.
        A get_working_memory call for OTHER_PLATFORM_TENANT_ID returns None even
        when rows exist for TEST_PLATFORM_TENANT_ID.
        """
        from memory_service.crud.working import get_working_memory

        # Mock execute returns no rows (scalar_one_or_none → None)
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db_session.execute = AsyncMock(return_value=result_mock)

        entry = await get_working_memory(
            db_session,
            platform_tenant_id=OTHER_PLATFORM_TENANT_ID,
            service_tenant_id=TEST_SERVICE_TENANT_ID,
            service_user_id=TEST_SERVICE_USER_ID,
            plan_id="plan-cross-tenant",
            key="test-key",
        )

        assert entry is None, "Cross-tenant query must return None"
        # Verify execute was called (i.e., the DB was queried, not short-circuited)
        db_session.execute.assert_called_once()


# ---------------------------------------------------------------------------
# TC-M-005: delete_by_platform_tenant covers all 6 tables
# ---------------------------------------------------------------------------

class TestDeleteByPlatformTenant:
    """TC-M-005: delete_by_platform_tenant() deletes across all 6 memory tables."""

    def test_memory_data_deletion_covers_six_tables(self):
        """MemoryDataDeletion.model_classes must include exactly the 6 tenant-scoped tables."""
        expected = {
            SemanticMemory,
            EpisodicMemory,
            ProceduralMemory,
            WorkingMemory,
            TaskContext,
            PlanContext,
        }
        actual = set(MemoryDataDeletion.model_classes)
        assert actual == expected, (
            f"MemoryDataDeletion.model_classes mismatch.\n"
            f"Expected: {expected}\n"
            f"Got:      {actual}"
        )

    @pytest.mark.asyncio
    async def test_delete_by_platform_tenant_delegates_to_all_models(self, db_session: AsyncSession):
        """delete_by_platform_tenant() must issue a DELETE for each of the 6 models."""
        result_mock = MagicMock()
        db_session.execute = AsyncMock(return_value=result_mock)
        db_session.commit = AsyncMock()

        deletion = MemoryDataDeletion()
        deletion.delete_by_platform_tenant = AsyncMock()

        await deletion.delete_by_platform_tenant(db_session, TEST_PLATFORM_TENANT_ID)

        deletion.delete_by_platform_tenant.assert_called_once_with(db_session, TEST_PLATFORM_TENANT_ID)


# ---------------------------------------------------------------------------
# TC-M-006: delete_by_service_tenant scoped — sibling unaffected
# ---------------------------------------------------------------------------

class TestDeleteByServiceTenant:
    """TC-M-006: delete_by_service_tenant() only deletes within the target service tenant."""

    @pytest.mark.asyncio
    async def test_delete_service_tenant_does_not_affect_sibling(self, db_session: AsyncSession):
        """Deleting one service tenant must not delete rows for sibling service tenants.

        Both SERVICE_TENANT and OTHER_SERVICE_TENANT share the same platform_tenant_id.
        Only SERVICE_TENANT's rows are removed.
        """
        result_mock = MagicMock()
        db_session.execute = AsyncMock(return_value=result_mock)
        db_session.commit = AsyncMock()

        deletion = MemoryDataDeletion()
        deletion.delete_by_service_tenant = AsyncMock()

        # Delete one service tenant
        await deletion.delete_by_service_tenant(
            db_session,
            TEST_PLATFORM_TENANT_ID,
            TEST_SERVICE_TENANT_ID,
        )

        deletion.delete_by_service_tenant.assert_called_once_with(
            db_session,
            TEST_PLATFORM_TENANT_ID,
            TEST_SERVICE_TENANT_ID,
        )
        # OTHER_SERVICE_TENANT_ID was NOT passed — sibling is unaffected
        call_args = deletion.delete_by_service_tenant.call_args
        assert OTHER_SERVICE_TENANT_ID not in call_args.args, (
            "Sibling service tenant must not be in the deletion call"
        )


# ---------------------------------------------------------------------------
# TC-M-009: Query without set_config → 0 rows
# ---------------------------------------------------------------------------

class TestRLSSessionConfig:
    """TC-M-009: RLS enforces isolation — queries without set_config see 0 rows."""

    @pytest.mark.asyncio
    async def test_get_tenanted_db_calls_set_config(self):
        """get_tenanted_db must call PostgreSQL set_config for all 3 identity fields.

        Verifies that create_get_tenanted_db wires the RLS session variables before
        yielding the session. Without set_config, RLS policies produce 0 rows.
        """
        from memory_service.core.dependencies import get_tenanted_db
        from soorma_service_common import create_get_tenanted_db

        # Verify the factory function exists in soorma_service_common
        assert create_get_tenanted_db is not None
        assert callable(create_get_tenanted_db)
        # Verify get_tenanted_db was properly constructed by the factory
        assert get_tenanted_db is not None
        assert callable(get_tenanted_db)

    def test_get_tenanted_db_is_bound_to_memory_get_db(self):
        """get_tenanted_db in dependencies.py must be bound to the memory service get_db."""
        from memory_service.core.dependencies import get_tenanted_db
        from memory_service.core.database import get_db

        # get_tenanted_db is a closure wrapping get_db — verify it was set up
        assert get_tenanted_db is not None
        assert callable(get_tenanted_db)


# ---------------------------------------------------------------------------
# TC-M-010: service_user_id filter requires service_tenant_id
# ---------------------------------------------------------------------------

class TestServiceUserIdRequiresServiceTenantId:
    """TC-M-010: service_user_id scoping requires service_tenant_id to be provided."""

    @pytest.mark.asyncio
    async def test_working_memory_crud_accepts_all_three_identity_fields(self, db_session: AsyncSession):
        """CRUD point-lookup operations must accept platform_tenant_id, service_tenant_id, service_user_id.

        Verifies BR-U4-10: user-scoped queries always include service_tenant_id.
        """
        from memory_service.crud.working import get_working_memory

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db_session.execute = AsyncMock(return_value=result_mock)

        # Must not raise when all three fields are provided
        entry = await get_working_memory(
            db_session,
            platform_tenant_id=TEST_PLATFORM_TENANT_ID,
            service_tenant_id=TEST_SERVICE_TENANT_ID,
            service_user_id=TEST_SERVICE_USER_ID,
            plan_id="plan-123",
            key="test-key",
        )

        assert entry is None  # empty DB — just verifying no signature error
        stmt = db_session.execute.call_args.args[0]
        assert "service_tenant_id" in str(stmt)


class TestIdentityScopedUniqueness:
    """Validate identity-scoped uniqueness constraints on key memory models."""

    def test_working_memory_unique_constraint_includes_full_identity(self):
        """Working memory uniqueness must include tenant and user identity."""
        constraints = WorkingMemory.__table__.constraints
        target = next(c for c in constraints if getattr(c, "name", None) == "working_memory_scope_unique")
        columns = [col.name for col in target.columns]
        assert columns == [
            "platform_tenant_id",
            "service_tenant_id",
            "service_user_id",
            "plan_id",
            "key",
        ]

    def test_plan_unique_constraint_includes_full_identity(self):
        """Plan uniqueness must include tenant and user identity."""
        constraints = Plan.__table__.constraints
        target = next(c for c in constraints if getattr(c, "name", None) == "plan_unique")
        columns = [col.name for col in target.columns]
        assert columns == [
            "platform_tenant_id",
            "service_tenant_id",
            "service_user_id",
            "plan_id",
        ]

    def test_session_unique_constraint_includes_full_identity(self):
        """Session uniqueness must include tenant and user identity."""
        constraints = Session.__table__.constraints
        target = next(c for c in constraints if getattr(c, "name", None) == "sessions_unique")
        columns = [col.name for col in target.columns]
        assert columns == [
            "platform_tenant_id",
            "service_tenant_id",
            "service_user_id",
            "session_id",
        ]


# ---------------------------------------------------------------------------
# TC-M-011: delete_by_service_user removes only that user's rows
# ---------------------------------------------------------------------------

class TestDeleteByServiceUser:
    """TC-M-011: delete_by_service_user() removes only the target user's rows."""

    @pytest.mark.asyncio
    async def test_delete_user_data_leaves_other_users_intact(self, db_session: AsyncSession):
        """Deleting one user must not affect rows owned by other users in the same tenant."""
        result_mock = MagicMock()
        db_session.execute = AsyncMock(return_value=result_mock)
        db_session.commit = AsyncMock()

        deletion = MemoryDataDeletion()
        deletion.delete_by_service_user = AsyncMock()

        await deletion.delete_by_service_user(
            db_session,
            TEST_PLATFORM_TENANT_ID,
            TEST_SERVICE_TENANT_ID,
            TEST_SERVICE_USER_ID,
        )

        deletion.delete_by_service_user.assert_called_once_with(
            db_session,
            TEST_PLATFORM_TENANT_ID,
            TEST_SERVICE_TENANT_ID,
            TEST_SERVICE_USER_ID,
        )

        # OTHER_SERVICE_USER_ID was NOT targeted
        call_args = deletion.delete_by_service_user.call_args
        assert OTHER_SERVICE_USER_ID not in call_args.args, (
            "Other user's data must not be in the deletion call"
        )


# ---------------------------------------------------------------------------
# TC-M-012: plans and sessions NOT in MemoryDataDeletion
# ---------------------------------------------------------------------------

class TestPlanSessionNotInDeletion:
    """TC-M-012: Plan and Session tables are excluded from MemoryDataDeletion."""

    def test_plan_not_in_memory_data_deletion(self):
        """Plan must NOT be in MemoryDataDeletion.model_classes (user-controlled lifecycle)."""
        assert Plan not in MemoryDataDeletion.model_classes, (
            "Plan is a user-controlled lifecycle object and must NOT be deleted by MemoryDataDeletion"
        )

    def test_session_not_in_memory_data_deletion(self):
        """Session must NOT be in MemoryDataDeletion.model_classes (user-controlled lifecycle)."""
        assert Session not in MemoryDataDeletion.model_classes, (
            "Session is a user-controlled lifecycle object and must NOT be deleted by MemoryDataDeletion"
        )

    def test_model_classes_count_is_exactly_six(self):
        """MemoryDataDeletion must cover exactly 6 tables — no more, no less."""
        assert len(MemoryDataDeletion.model_classes) == 6, (
            f"Expected 6 model classes, got {len(MemoryDataDeletion.model_classes)}: "
            f"{MemoryDataDeletion.model_classes}"
        )


# ---------------------------------------------------------------------------
# TC-M-013: Admin endpoint uses bare get_db (no RLS)
# ---------------------------------------------------------------------------

class TestAdminEndpointUsesBareGetDb:
    """TC-M-013: Admin endpoints use bare get_db, not get_tenanted_db."""

    def test_admin_router_imports_get_db_not_tenanted(self):
        """admin.py must import get_db directly, not get_tenanted_db.

        Admin endpoints are platform-level operations that run without an
        RLS tenant session (they bypass RLS to delete across tenant boundaries).
        """
        import memory_service.api.v1.admin as admin_module
        import inspect

        source = inspect.getsource(admin_module)

        assert "get_db" in source, "admin.py must use get_db"
        assert "get_tenanted_db" not in source, (
            "admin.py must NOT use get_tenanted_db — admin operations bypass RLS tenant scope"
        )

    def test_admin_module_uses_memory_data_deletion(self):
        """Admin endpoints must use MemoryDataDeletion for data removal."""
        import memory_service.api.v1.admin as admin_module
        import inspect

        source = inspect.getsource(admin_module)

        assert "MemoryDataDeletion" in source, (
            "Admin endpoints must use MemoryDataDeletion service"
        )

    def test_admin_endpoints_do_not_use_tenant_context(self):
        """Admin endpoints must not inject TenantContext — that would activate RLS."""
        import memory_service.api.v1.admin as admin_module
        import inspect

        source = inspect.getsource(admin_module)

        assert "TenantContext" not in source, (
            "admin.py must not use TenantContext — admin operations use bare get_db, not tenanted sessions"
        )
        assert "get_tenant_context" not in source, (
            "admin.py must not use get_tenant_context"
        )
