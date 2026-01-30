"""Tests for working memory deletion in SDK (RF-SDK-020)."""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from soorma.memory.client import MemoryClient
from soorma_common.models import (
    WorkingMemoryResponse,
    WorkingMemoryDeleteKeyResponse,
    WorkingMemoryDeletePlanResponse,
)


class TestMemoryClientWorkingMemoryDeletion:
    """Test working memory deletion in MemoryClient."""

    @pytest.fixture
    def client(self):
        """Create and cleanup MemoryClient."""
        client = MemoryClient(base_url="http://localhost:8083")
        yield client
        # Note: close() is async, so we can't call it directly in sync fixture
        # The client will be cleaned up via context manager in tests that need it

    @pytest.fixture
    def test_ids(self):
        """Generate test IDs."""
        return {
            "plan_id": str(uuid4()),
            "tenant_id": str(uuid4()),
            "user_id": str(uuid4()),
            "key": "test_key",
        }

    @pytest.mark.asyncio
    async def test_delete_plan_state_key_success(self, client, test_ids):
        """Test deleting a single working memory key."""
        # Create a mock response object
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(return_value={
            "success": True,
            "deleted": True,
            "message": "Working memory key deleted",
        })
        
        # Create async mock for delete
        async_mock = AsyncMock(return_value=mock_response)
        
        with patch.object(client._client, "delete", async_mock):
            # Delete key
            result = await client.delete_plan_state(
                plan_id=test_ids["plan_id"],
                tenant_id=test_ids["tenant_id"],
                user_id=test_ids["user_id"],
                key=test_ids["key"],
            )

            # Verify
            assert isinstance(result, WorkingMemoryDeleteKeyResponse)
            assert result.success is True
            assert result.deleted is True
            assert result.message == "Working memory key deleted"
            
            # Verify correct endpoint called
            async_mock.assert_called_once()
            call_url = async_mock.call_args[0][0]
            assert test_ids["plan_id"] in call_url
            assert test_ids["key"] in call_url

    @pytest.mark.asyncio
    async def test_delete_plan_state_key_not_found(self, client, test_ids):
        """Test deleting non-existent key returns deleted=False."""
        # Create a mock response object
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(return_value={
            "success": True,
            "deleted": False,
            "message": "Working memory key not found",
        })
        
        # Create async mock for delete
        async_mock = AsyncMock(return_value=mock_response)
        
        with patch.object(client._client, "delete", async_mock):
            # Delete non-existent key
            result = await client.delete_plan_state(
                plan_id=test_ids["plan_id"],
                tenant_id=test_ids["tenant_id"],
                user_id=test_ids["user_id"],
                key=test_ids["key"],
            )

            # Verify
            assert isinstance(result, WorkingMemoryDeleteKeyResponse)
            assert result.deleted is False

    @pytest.mark.asyncio
    async def test_delete_all_plan_state_success(self, client, test_ids):
        """Test deleting all working memory for a plan."""
        # Create a mock response object
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(return_value={
            "success": True,
            "count_deleted": 5,
            "message": "Deleted 5 working memory keys",
        })
        
        # Create async mock for delete
        async_mock = AsyncMock(return_value=mock_response)
        
        with patch.object(client._client, "delete", async_mock):
            # Delete all keys for plan
            result = await client.delete_plan_state(
                plan_id=test_ids["plan_id"],
                tenant_id=test_ids["tenant_id"],
                user_id=test_ids["user_id"],
            )

            # Verify
            assert isinstance(result, WorkingMemoryDeletePlanResponse)
            assert result.success is True
            assert result.count_deleted == 5
            assert result.message == "Deleted 5 working memory keys"

            # Verify correct endpoint called (no key in URL)
            async_mock.assert_called_once()
            call_url = async_mock.call_args[0][0]
            assert test_ids["plan_id"] in call_url
            assert test_ids["key"] not in call_url

    @pytest.mark.asyncio
    async def test_delete_all_plan_state_empty(self, client, test_ids):
        """Test deleting from empty plan returns count=0."""
        # Create a mock response object
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(return_value={
            "success": True,
            "count_deleted": 0,
            "message": "Deleted 0 working memory keys",
        })
        
        # Create async mock for delete
        async_mock = AsyncMock(return_value=mock_response)
        
        with patch.object(client._client, "delete", async_mock):
            # Delete all keys from empty plan
            result = await client.delete_plan_state(
                plan_id=test_ids["plan_id"],
                tenant_id=test_ids["tenant_id"],
                user_id=test_ids["user_id"],
            )

            # Verify
            assert result.count_deleted == 0

    @pytest.mark.asyncio
    async def test_delete_sends_correct_parameters(self, client, test_ids):
        """Test that delete sends correct headers."""
        # Create a mock response object
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(return_value={
            "success": True,
            "deleted": True,
            "message": "Deleted",
        })
        
        # Create async mock for delete
        async_mock = AsyncMock(return_value=mock_response)
        
        with patch.object(client._client, "delete", async_mock):
            await client.delete_plan_state(
                plan_id=test_ids["plan_id"],
                tenant_id=test_ids["tenant_id"],
                user_id=test_ids["user_id"],
                key=test_ids["key"],
            )

            # Verify the call was made
            async_mock.assert_called_once()
            # Check URL includes plan_id and key
            call_args = async_mock.call_args
            assert test_ids["plan_id"] in call_args[0][0]
            assert test_ids["key"] in call_args[0][0]
            # Check headers include tenant_id and user_id
            headers = call_args[1]["headers"]
            assert headers["X-Tenant-ID"] == test_ids["tenant_id"]
            assert headers["X-User-ID"] == test_ids["user_id"]


class TestWorkflowStateDelete:
    """Test working memory deletion in WorkflowState helper."""

    @pytest.fixture
    def setup(self):
        """Setup test data."""
        return {
            "plan_id": str(uuid4()),
            "user_id": str(uuid4()),
            "tenant_id": str(uuid4()),
            "key": "test_state",
        }

    @pytest.mark.asyncio
    async def test_workflow_state_delete_key(self, setup):
        """Test deleting a single key via WorkflowState."""
        from soorma.workflow import WorkflowState

        # Create mock memory client
        mock_memory = AsyncMock()
        mock_memory.delete_key.return_value = WorkingMemoryDeleteKeyResponse(
            success=True,
            deleted=True,
            message="Deleted",
        )

        state = WorkflowState(
            memory_client=mock_memory,
            plan_id=setup["plan_id"],
            tenant_id=setup["tenant_id"],
            user_id=setup["user_id"],
        )

        # Delete key
        result = await state.delete(setup["key"])

        # Verify
        assert result is True
        mock_memory.delete_key.assert_called_once_with(
            plan_id=setup["plan_id"],
            tenant_id=setup["tenant_id"],
            user_id=setup["user_id"],
            key=setup["key"],
        )

    @pytest.mark.asyncio
    async def test_workflow_state_cleanup_all_keys(self, setup):
        """Test cleanup all keys via WorkflowState."""
        from soorma.workflow import WorkflowState

        # Create mock memory client
        mock_memory = AsyncMock()
        mock_memory.cleanup_plan.return_value = WorkingMemoryDeletePlanResponse(
            success=True,
            count_deleted=3,
            message="Deleted 3 keys",
        )

        state = WorkflowState(
            memory_client=mock_memory,
            plan_id=setup["plan_id"],
            tenant_id=setup["tenant_id"],
            user_id=setup["user_id"],
        )

        # Cleanup all
        count = await state.cleanup()

        # Verify
        assert count == 3
        mock_memory.cleanup_plan.assert_called_once_with(
            plan_id=setup["plan_id"],
            tenant_id=setup["tenant_id"],
            user_id=setup["user_id"],
        )

    @pytest.mark.asyncio
    async def test_workflow_state_delete_returns_false_if_not_found(self, setup):
        """Test delete returns False if key doesn't exist."""
        from soorma.workflow import WorkflowState

        # Create mock memory client
        mock_memory = AsyncMock()
        mock_memory.delete_key.return_value = WorkingMemoryDeleteKeyResponse(
            success=True,
            deleted=False,
            message="Not found",
        )

        state = WorkflowState(
            memory_client=mock_memory,
            plan_id=setup["plan_id"],
            tenant_id=setup["tenant_id"],
            user_id=setup["user_id"],
        )

        # Delete non-existent key
        result = await state.delete(setup["key"])

        # Verify
        assert result is False
