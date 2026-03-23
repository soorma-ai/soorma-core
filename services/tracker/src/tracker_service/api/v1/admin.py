"""Admin deletion endpoints for tracker GDPR/operational cleanup."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from tracker_service.core.db import get_db
from tracker_service.services.data_deletion import TrackerDataDeletion

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.delete("/platform/{platform_tenant_id}", status_code=204)
async def delete_platform_tenant_data(
    platform_tenant_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete all tracker data for a platform tenant."""
    await TrackerDataDeletion().delete_by_platform_tenant(db, platform_tenant_id)


@router.delete("/tenant/{platform_tenant_id}/{service_tenant_id}", status_code=204)
async def delete_service_tenant_data(
    platform_tenant_id: str,
    service_tenant_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete tracker data for a service tenant within a platform tenant."""
    await TrackerDataDeletion().delete_by_service_tenant(db, platform_tenant_id, service_tenant_id)


@router.delete("/user/{platform_tenant_id}/{service_tenant_id}/{service_user_id}", status_code=204)
async def delete_service_user_data(
    platform_tenant_id: str,
    service_tenant_id: str,
    service_user_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete tracker data for a service user."""
    await TrackerDataDeletion().delete_by_service_user(
        db,
        platform_tenant_id,
        service_tenant_id,
        service_user_id,
    )
