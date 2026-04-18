"""Tenant admin credential API endpoints."""

from fastapi import APIRouter, Depends
from soorma_common.models import TenantAdminCredentialRotateResponse

from identity_service.core.dependencies import (
    TenantContext,
    get_tenant_context,
    require_tenant_admin_authorization,
)
from identity_service.services.admin_api_keys import tenant_admin_api_key_service

router = APIRouter(prefix="/tenant-admin-credentials", tags=["Tenant Admin Credentials"])


@router.post("/rotate", response_model=TenantAdminCredentialRotateResponse)
async def rotate_tenant_admin_credential(
    _tenant_admin: str = Depends(require_tenant_admin_authorization),
    context: TenantContext = Depends(get_tenant_context),
):
    """Rotate the current tenant admin API credential."""
    actor_id = context.principal_id or context.service_user_id or "identity-tenant-admin-api-key"
    return await tenant_admin_api_key_service.rotate_api_key(
        context.db,
        context.platform_tenant_id,
        actor_id=actor_id,
    )
