"""
Tests for PlatformTenantDataDeletion abstract base class.

RED phase: tests verify the ABC contract (cannot instantiate directly,
partial subclass cannot instantiate, complete subclass can).
These tests pass in both RED and GREEN phases — they test structural invariants,
not NotImplementedError-raising stubs.
"""
import pytest
from unittest.mock import AsyncMock

from soorma_service_common.deletion import PlatformTenantDataDeletion


class TestPlatformTenantDataDeletionABC:
    """PlatformTenantDataDeletion is an ABC with three abstract methods."""

    def test_cannot_instantiate_abc_directly(self):
        """PlatformTenantDataDeletion cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            PlatformTenantDataDeletion()

    def test_partial_subclass_without_all_methods_cannot_instantiate(self):
        """A subclass missing any abstract method cannot be instantiated."""
        class Partial(PlatformTenantDataDeletion):
            async def delete_by_platform_tenant(self, db, platform_tenant_id):
                return 0
            # missing delete_by_service_tenant and delete_by_service_user

        with pytest.raises(TypeError):
            Partial()

    def test_complete_subclass_can_be_instantiated(self):
        """A subclass implementing all three methods can be instantiated."""
        class Complete(PlatformTenantDataDeletion):
            async def delete_by_platform_tenant(self, db, platform_tenant_id):
                return 0

            async def delete_by_service_tenant(self, db, platform_tenant_id, service_tenant_id):
                return 0

            async def delete_by_service_user(self, db, platform_tenant_id, service_tenant_id, service_user_id):
                return 0

        instance = Complete()
        assert isinstance(instance, PlatformTenantDataDeletion)

    @pytest.mark.asyncio
    async def test_complete_subclass_delete_by_platform_tenant_returns_int(self):
        """delete_by_platform_tenant must return an int (row count)."""
        class Complete(PlatformTenantDataDeletion):
            async def delete_by_platform_tenant(self, db, platform_tenant_id):
                return 42

            async def delete_by_service_tenant(self, db, platform_tenant_id, service_tenant_id):
                return 0

            async def delete_by_service_user(self, db, platform_tenant_id, service_tenant_id, service_user_id):
                return 0

        instance = Complete()
        result = await instance.delete_by_platform_tenant(AsyncMock(), "spt_acme")
        assert isinstance(result, int)
        assert result == 42

    @pytest.mark.asyncio
    async def test_complete_subclass_delete_by_service_tenant_returns_int(self):
        """delete_by_service_tenant must return an int (row count)."""
        class Complete(PlatformTenantDataDeletion):
            async def delete_by_platform_tenant(self, db, platform_tenant_id):
                return 0

            async def delete_by_service_tenant(self, db, platform_tenant_id, service_tenant_id):
                return 7

            async def delete_by_service_user(self, db, platform_tenant_id, service_tenant_id, service_user_id):
                return 0

        instance = Complete()
        result = await instance.delete_by_service_tenant(AsyncMock(), "spt_acme", "tenant-1")
        assert result == 7

    @pytest.mark.asyncio
    async def test_complete_subclass_delete_by_service_user_returns_int(self):
        """delete_by_service_user must return an int (row count)."""
        class Complete(PlatformTenantDataDeletion):
            async def delete_by_platform_tenant(self, db, platform_tenant_id):
                return 0

            async def delete_by_service_tenant(self, db, platform_tenant_id, service_tenant_id):
                return 0

            async def delete_by_service_user(self, db, platform_tenant_id, service_tenant_id, service_user_id):
                return 3

        instance = Complete()
        result = await instance.delete_by_service_user(
            AsyncMock(), "spt_acme", "tenant-1", "user-42"
        )
        assert result == 3
