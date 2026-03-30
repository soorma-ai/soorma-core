"""Admin GDPR data deletion endpoints (BR-U4-08).

Uses bare get_db (no tenant context) — these are admin/platform-level operations.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from memory_service.core.dependencies import require_admin_authorization
from memory_service.core.database import get_db
from memory_service.services.data_deletion import MemoryDataDeletion

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(require_admin_authorization)],
)


@router.delete("/platform/{platform_tenant_id}", status_code=204)
async def delete_platform_tenant_data(
    platform_tenant_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete all memory data for a platform tenant (all service tenants and users)."""
    await MemoryDataDeletion().delete_by_platform_tenant(db, platform_tenant_id)


@router.delete("/tenant/{platform_tenant_id}/{service_tenant_id}", status_code=204)
async def delete_service_tenant_data(
    platform_tenant_id: str,
    service_tenant_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete all memory data for a service tenant within a platform tenant."""
    await MemoryDataDeletion().delete_by_service_tenant(db, platform_tenant_id, service_tenant_id)


@router.delete("/user/{platform_tenant_id}/{service_tenant_id}/{service_user_id}", status_code=204)
async def delete_user_data(
    platform_tenant_id: str,
    service_tenant_id: str,
    service_user_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete all memory data for a specific user (GDPR right to erasure)."""
    await MemoryDataDeletion().delete_by_service_user(db, platform_tenant_id, service_tenant_id, service_user_id)
