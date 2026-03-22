"""
Abstract base class for GDPR-compliant platform-scoped data deletion.

Concrete implementations (MemoryDataDeletion, TrackerDataDeletion) live in
each respective service and register with the platform deletion API.
"""
from abc import ABC, abstractmethod

from sqlalchemy.ext.asyncio import AsyncSession


class PlatformTenantDataDeletion(ABC):
    """
    Abstract base for GDPR erasure scoped to the platform tenant namespace.

    All three methods execute within the caller's DB transaction; callers are
    responsible for commit/rollback.  Return values are total rows deleted
    (across all covered tables) to support audit logging.

    Implementors:
        - MemoryDataDeletion   (services/memory_service/)
        - TrackerDataDeletion  (services/tracker_service/)
    """

    @abstractmethod
    async def delete_by_platform_tenant(
        self,
        db: AsyncSession,
        platform_tenant_id: str,
    ) -> int:
        """
        Delete ALL rows across ALL covered tables for a platform tenant.

        Used when an organisation fully offboards from Soorma.  Cascades
        through service-tenant and user scopes within the platform tenant.

        Args:
            db: Open AsyncSession with set_config already active.
            platform_tenant_id: Platform tenant whose data to erase.

        Returns:
            Total number of rows deleted across all tables.
        """
        ...

    @abstractmethod
    async def delete_by_service_tenant(
        self,
        db: AsyncSession,
        platform_tenant_id: str,
        service_tenant_id: str,
    ) -> int:
        """
        Delete all rows for a service tenant within a platform tenant's namespace.

        Used when a service-level tenant is removed while the platform tenant
        remains active.

        Args:
            db: Open AsyncSession with set_config already active.
            platform_tenant_id: Owning platform tenant.
            service_tenant_id: Service tenant whose data to erase.

        Returns:
            Total number of rows deleted.
        """
        ...

    @abstractmethod
    async def delete_by_service_user(
        self,
        db: AsyncSession,
        platform_tenant_id: str,
        service_tenant_id: str,
        service_user_id: str,
    ) -> int:
        """
        Delete all rows for a specific service user (right-to-erasure / GDPR Article 17).

        Args:
            db: Open AsyncSession with set_config already active.
            platform_tenant_id: Owning platform tenant.
            service_tenant_id: Owning service tenant.
            service_user_id: User whose data to erase.

        Returns:
            Total number of rows deleted.
        """
        ...
