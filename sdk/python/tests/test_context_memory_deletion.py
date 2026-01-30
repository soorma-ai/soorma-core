"""Tests for working memory deletion in PlatformContext.MemoryClient wrapper (RF-SDK-021)."""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from soorma.context import MemoryClient as ContextMemoryClient
from soorma_common.models import (
    WorkingMemoryDeleteKeyResponse,
    WorkingMemoryDeletePlanResponse,
)


class TestContextMemoryClientDeletion:
    """Test working memory deletion in context.MemoryClient wrapper."""

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
    async def test_delete_key_single_key(self, setup):
        """Test delete_key() deletes a single key."""
        # Create context memory client
        context_memory = ContextMemoryClient(base_url="http://localhost:8083")
        
        # Mock the underlying service client
        mock_service_client = AsyncMock()
        mock_service_client.delete_plan_state.return_value = WorkingMemoryDeleteKeyResponse(
            success=True,
            deleted=True,
            message="Key deleted",
        )
        context_memory._client = mock_service_client
        
        # Delete key
        result = await context_memory.delete_key(
            plan_id=setup["plan_id"],
            tenant_id=setup["tenant_id"],
            user_id=setup["user_id"],
            key=setup["key"],
        )
        
        # Verify
        assert isinstance(result, WorkingMemoryDeleteKeyResponse)
        assert result.deleted is True
        mock_service_client.delete_plan_state.assert_called_once_with(
            plan_id=setup["plan_id"],
            tenant_id=setup["tenant_id"],
            user_id=setup["user_id"],
            key=setup["key"],
        )

    @pytest.mark.asyncio
    async def test_delete_key_not_found(self, setup):
        """Test delete_key() returns deleted=False if key not found."""
        # Create context memory client
        context_memory = ContextMemoryClient(base_url="http://localhost:8083")
        
        # Mock the underlying service client
        mock_service_client = AsyncMock()
        mock_service_client.delete_plan_state.return_value = WorkingMemoryDeleteKeyResponse(
            success=True,
            deleted=False,
            message="Key not found",
        )
        context_memory._client = mock_service_client
        
        # Delete non-existent key
        result = await context_memory.delete_key(
            plan_id=setup["plan_id"],
            tenant_id=setup["tenant_id"],
            user_id=setup["user_id"],
            key=setup["key"],
        )
        
        # Verify
        assert result.deleted is False

    @pytest.mark.asyncio
    async def test_cleanup_plan_removes_all_keys(self, setup):
        """Test cleanup_plan() removes all keys for a plan."""
        # Create context memory client
        context_memory = ContextMemoryClient(base_url="http://localhost:8083")
        
        # Mock the underlying service client
        mock_service_client = AsyncMock()
        mock_service_client.delete_plan_state.return_value = WorkingMemoryDeletePlanResponse(
            success=True,
            count_deleted=5,
            message="Deleted 5 keys",
        )
        context_memory._client = mock_service_client
        
        # Cleanup all keys
        result = await context_memory.cleanup_plan(
            plan_id=setup["plan_id"],
            tenant_id=setup["tenant_id"],
            user_id=setup["user_id"],
        )
        
        # Verify
        assert isinstance(result, WorkingMemoryDeletePlanResponse)
        assert result.count_deleted == 5
        mock_service_client.delete_plan_state.assert_called_once_with(
            plan_id=setup["plan_id"],
            tenant_id=setup["tenant_id"],
            user_id=setup["user_id"],
            key=None,
        )

    @pytest.mark.asyncio
    async def test_cleanup_plan_empty_plan(self, setup):
        """Test cleanup_plan() on empty plan returns count=0."""
        # Create context memory client
        context_memory = ContextMemoryClient(base_url="http://localhost:8083")
        
        # Mock the underlying service client
        mock_service_client = AsyncMock()
        mock_service_client.delete_plan_state.return_value = WorkingMemoryDeletePlanResponse(
            success=True,
            count_deleted=0,
            message="Plan was empty",
        )
        context_memory._client = mock_service_client
        
        # Cleanup empty plan
        result = await context_memory.cleanup_plan(
            plan_id=setup["plan_id"],
            tenant_id=setup["tenant_id"],
            user_id=setup["user_id"],
        )
        
        # Verify
        assert result.count_deleted == 0

    @pytest.mark.asyncio
    async def test_delete_key_returns_correct_pydantic_type(self, setup):
        """Test delete_key() returns WorkingMemoryDeleteKeyResponse Pydantic model."""
        # Create context memory client
        context_memory = ContextMemoryClient(base_url="http://localhost:8083")
        
        # Mock the underlying service client with Pydantic model
        mock_service_client = AsyncMock()
        response = WorkingMemoryDeleteKeyResponse(
            success=True,
            deleted=True,
            message="Deleted",
        )
        mock_service_client.delete_plan_state.return_value = response
        context_memory._client = mock_service_client
        
        # Delete key
        result = await context_memory.delete_key(
            plan_id=setup["plan_id"],
            tenant_id=setup["tenant_id"],
            user_id=setup["user_id"],
            key=setup["key"],
        )
        
        # Verify we get the Pydantic model, not a dict
        assert isinstance(result, WorkingMemoryDeleteKeyResponse)
        assert hasattr(result, "deleted")
        assert hasattr(result, "success")
        assert hasattr(result, "message")

    @pytest.mark.asyncio
    async def test_cleanup_plan_returns_correct_pydantic_type(self, setup):
        """Test cleanup_plan() returns WorkingMemoryDeletePlanResponse Pydantic model."""
        # Create context memory client
        context_memory = ContextMemoryClient(base_url="http://localhost:8083")
        
        # Mock the underlying service client with Pydantic model
        mock_service_client = AsyncMock()
        response = WorkingMemoryDeletePlanResponse(
            success=True,
            count_deleted=3,
            message="Deleted 3 keys",
        )
        mock_service_client.delete_plan_state.return_value = response
        context_memory._client = mock_service_client
        
        # Cleanup plan
        result = await context_memory.cleanup_plan(
            plan_id=setup["plan_id"],
            tenant_id=setup["tenant_id"],
            user_id=setup["user_id"],
        )
        
        # Verify we get the Pydantic model, not a dict
        assert isinstance(result, WorkingMemoryDeletePlanResponse)
        assert hasattr(result, "count_deleted")
        assert hasattr(result, "success")
        assert hasattr(result, "message")
