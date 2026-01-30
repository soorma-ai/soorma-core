"""Tests for working memory deletion (RF-ARCH-013)."""

import pytest
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from memory_service.crud.working import (
    set_working_memory,
    get_working_memory,
    delete_working_memory_key,
    delete_working_memory_plan,
)
from soorma_common.models import WorkingMemorySet


class TestWorkingMemoryDeletion:
    """Test working memory deletion operations."""

    @pytest.fixture
    def test_ids(self):
        """Generate test IDs."""
        return {
            "tenant_id": uuid4(),
            "user_id": uuid4(),
            "plan_id": uuid4(),
            "other_tenant_id": uuid4(),
            "other_user_id": uuid4(),
            "other_plan_id": uuid4(),
        }

    async def test_delete_working_memory_key_success(
        self, db_session: AsyncSession, test_ids
    ):
        """Test deleting a single working memory key successfully."""
        # Setup: Create a key
        key = "research_data"
        await set_working_memory(
            db_session,
            test_ids["tenant_id"],
            test_ids["user_id"],
            test_ids["plan_id"],
            key,
            WorkingMemorySet(value={"topic": "AI research"}),
        )
        
        # Verify it exists
        existing = await get_working_memory(
            db_session,
            test_ids["tenant_id"],
            test_ids["user_id"],
            test_ids["plan_id"],
            key,
        )
        assert existing is not None
        
        # Delete the key
        deleted = await delete_working_memory_key(
            db_session,
            test_ids["tenant_id"],
            test_ids["user_id"],
            test_ids["plan_id"],
            key,
        )
        
        # Verify deletion
        assert deleted is True
        
        # Verify key is gone
        retrieved = await get_working_memory(
            db_session,
            test_ids["tenant_id"],
            test_ids["user_id"],
            test_ids["plan_id"],
            key,
        )
        assert retrieved is None

    async def test_delete_working_memory_key_not_found(
        self, db_session: AsyncSession, test_ids
    ):
        """Test deleting a non-existent key returns False."""
        key = "nonexistent_key"
        
        # Try to delete non-existent key
        deleted = await delete_working_memory_key(
            db_session,
            test_ids["tenant_id"],
            test_ids["user_id"],
            test_ids["plan_id"],
            key,
        )
        
        # Should return False, not raise error
        assert deleted is False

    async def test_delete_working_memory_key_multiple_keys(
        self, db_session: AsyncSession, test_ids
    ):
        """Test deleting one key doesn't affect other keys."""
        # Setup: Create multiple keys
        key1 = "research_data"
        key2 = "temporary_data"
        key3 = "persistent_data"
        
        await set_working_memory(
            db_session, test_ids["tenant_id"], test_ids["user_id"], test_ids["plan_id"],
            key1, WorkingMemorySet(value={"data": 1})
        )
        await set_working_memory(
            db_session, test_ids["tenant_id"], test_ids["user_id"], test_ids["plan_id"],
            key2, WorkingMemorySet(value={"data": 2})
        )
        await set_working_memory(
            db_session, test_ids["tenant_id"], test_ids["user_id"], test_ids["plan_id"],
            key3, WorkingMemorySet(value={"data": 3})
        )
        
        # Delete one key
        deleted = await delete_working_memory_key(
            db_session,
            test_ids["tenant_id"],
            test_ids["user_id"],
            test_ids["plan_id"],
            key2,
        )
        assert deleted is True
        
        # Verify other keys still exist
        assert await get_working_memory(
            db_session, test_ids["tenant_id"], test_ids["user_id"], test_ids["plan_id"], key1
        ) is not None
        assert await get_working_memory(
            db_session, test_ids["tenant_id"], test_ids["user_id"], test_ids["plan_id"], key2
        ) is None
        assert await get_working_memory(
            db_session, test_ids["tenant_id"], test_ids["user_id"], test_ids["plan_id"], key3
        ) is not None

    async def test_delete_all_working_memory_for_plan_success(
        self, db_session: AsyncSession, test_ids
    ):
        """Test deleting all working memory for a plan."""
        # Setup: Create multiple keys
        keys = ["key1", "key2", "key3"]
        for key in keys:
            await set_working_memory(
                db_session,
                test_ids["tenant_id"],
                test_ids["user_id"],
                test_ids["plan_id"],
                key,
                WorkingMemorySet(value={"data": key}),
            )
        
        # Delete all keys for plan
        count = await delete_working_memory_plan(
            db_session,
            test_ids["tenant_id"],
            test_ids["user_id"],
            test_ids["plan_id"],
        )
        
        # Verify count
        assert count == 3
        
        # Verify all keys are gone
        for key in keys:
            retrieved = await get_working_memory(
                db_session,
                test_ids["tenant_id"],
                test_ids["user_id"],
                test_ids["plan_id"],
                key,
            )
            assert retrieved is None

    async def test_delete_all_working_memory_empty_plan(
        self, db_session: AsyncSession, test_ids
    ):
        """Test deleting all working memory for empty plan returns 0."""
        # Don't create any keys
        
        # Delete all keys for empty plan
        count = await delete_working_memory_plan(
            db_session,
            test_ids["tenant_id"],
            test_ids["user_id"],
            test_ids["plan_id"],
        )
        
        # Should return 0
        assert count == 0

    async def test_delete_respects_tenant_isolation(
        self, db_session: AsyncSession, test_ids
    ):
        """Test delete respects RLS tenant isolation."""
        key = "sensitive_data"
        
        # Create key in tenant 1
        await set_working_memory(
            db_session,
            test_ids["tenant_id"],
            test_ids["user_id"],
            test_ids["plan_id"],
            key,
            WorkingMemorySet(value={"secret": "data"}),
        )
        
        # Try to delete from different tenant
        deleted = await delete_working_memory_key(
            db_session,
            test_ids["other_tenant_id"],  # Different tenant
            test_ids["user_id"],
            test_ids["plan_id"],
            key,
        )
        
        # Should return False (key doesn't exist for other tenant)
        assert deleted is False
        
        # Verify original key still exists
        retrieved = await get_working_memory(
            db_session,
            test_ids["tenant_id"],
            test_ids["user_id"],
            test_ids["plan_id"],
            key,
        )
        assert retrieved is not None

    async def test_delete_respects_user_isolation(
        self, db_session: AsyncSession, test_ids
    ):
        """Test delete respects user ownership within same tenant."""
        key = "user_private_data"

        # Create key for user A
        await set_working_memory(
            db_session,
            test_ids["tenant_id"],
            test_ids["user_id"],
            test_ids["plan_id"],
            key,
            WorkingMemorySet(value={"owner": "user_a"}),
        )

        # Attempt delete as user B in same tenant
        deleted = await delete_working_memory_key(
            db_session,
            test_ids["tenant_id"],
            test_ids["other_user_id"],
            test_ids["plan_id"],
            key,
        )

        assert deleted is False

        # Verify original key still exists for user A
        retrieved = await get_working_memory(
            db_session,
            test_ids["tenant_id"],
            test_ids["user_id"],
            test_ids["plan_id"],
            key,
        )
        assert retrieved is not None

    async def test_delete_respects_plan_isolation(
        self, db_session: AsyncSession, test_ids
    ):
        """Test delete respects plan isolation."""
        key = "plan_specific_data"
        
        # Create key in plan 1
        await set_working_memory(
            db_session,
            test_ids["tenant_id"],
            test_ids["user_id"],
            test_ids["plan_id"],
            key,
            WorkingMemorySet(value={"plan": 1}),
        )
        
        # Create same key in plan 2
        await set_working_memory(
            db_session,
            test_ids["tenant_id"],
            test_ids["user_id"],
            test_ids["other_plan_id"],
            key,
            WorkingMemorySet(value={"plan": 2}),
        )
        
        # Delete from plan 1
        deleted = await delete_working_memory_key(
            db_session,
            test_ids["tenant_id"],
            test_ids["user_id"],
            test_ids["plan_id"],
            key,
        )
        assert deleted is True
        
        # Verify plan 2 key still exists
        retrieved = await get_working_memory(
            db_session,
            test_ids["tenant_id"],
            test_ids["user_id"],
            test_ids["other_plan_id"],
            key,
        )
        assert retrieved is not None

    async def test_delete_with_invalid_plan_id(
        self, db_session: AsyncSession, test_ids
    ):
        """Test deleting with invalid plan_id gracefully returns False."""
        invalid_plan_id = uuid4()
        key = "nonexistent"
        
        # Try to delete from non-existent plan
        deleted = await delete_working_memory_key(
            db_session,
            test_ids["tenant_id"],
            test_ids["user_id"],
            invalid_plan_id,
            key,
        )
        
        # Should return False, not raise error
        assert deleted is False

    async def test_delete_all_returns_exact_count(
        self, db_session: AsyncSession, test_ids
    ):
        """Test delete_all returns exact count of deleted items."""
        # Create 5 keys
        for i in range(5):
            await set_working_memory(
                db_session,
                test_ids["tenant_id"],
                test_ids["user_id"],
                test_ids["plan_id"],
                f"key_{i}",
                WorkingMemorySet(value=i),
            )
        
        # Delete all
        count = await delete_working_memory_plan(
            db_session,
            test_ids["tenant_id"],
            test_ids["user_id"],
            test_ids["plan_id"],
        )
        
        # Should return exactly 5
        assert count == 5

    async def test_delete_multiple_calls_idempotent(
        self, db_session: AsyncSession, test_ids
    ):
        """Test that calling delete multiple times is safe (idempotent)."""
        key = "test_key"
        
        # Create key
        await set_working_memory(
            db_session,
            test_ids["tenant_id"],
            test_ids["user_id"],
            test_ids["plan_id"],
            key,
            WorkingMemorySet(value="data"),
        )
        
        # Delete first time
        deleted1 = await delete_working_memory_key(
            db_session,
            test_ids["tenant_id"],
            test_ids["user_id"],
            test_ids["plan_id"],
            key,
        )
        assert deleted1 is True
        
        # Delete second time (should be False)
        deleted2 = await delete_working_memory_key(
            db_session,
            test_ids["tenant_id"],
            test_ids["user_id"],
            test_ids["plan_id"],
            key,
        )
        assert deleted2 is False

    async def test_delete_all_multiple_plans_isolated(
        self, db_session: AsyncSession, test_ids
    ):
        """Test that delete_all only deletes from specified plan."""
        # Create keys in plan 1
        for i in range(3):
            await set_working_memory(
                db_session,
                test_ids["tenant_id"],
                test_ids["user_id"],
                test_ids["plan_id"],
                f"plan1_key_{i}",
                WorkingMemorySet(value=i),
            )
        
        # Create keys in plan 2
        for i in range(2):
            await set_working_memory(
                db_session,
                test_ids["tenant_id"],
                test_ids["user_id"],
                test_ids["other_plan_id"],
                f"plan2_key_{i}",
                WorkingMemorySet(value=i),
            )
        
        # Delete all from plan 1
        count1 = await delete_working_memory_plan(
            db_session,
            test_ids["tenant_id"],
            test_ids["user_id"],
            test_ids["plan_id"],
        )
        assert count1 == 3
        
        # Verify plan 2 keys still exist
        for i in range(2):
            retrieved = await get_working_memory(
                db_session,
                test_ids["tenant_id"],
                test_ids["user_id"],
                test_ids["other_plan_id"],
                f"plan2_key_{i}",
            )
            assert retrieved is not None
