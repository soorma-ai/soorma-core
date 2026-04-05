"""Principal lifecycle API endpoints."""

from fastapi import APIRouter, Depends
from soorma_common.models import PrincipalRequest, PrincipalResponse

from identity_service.core.dependencies import TenantContext, require_user_tenant_context
from identity_service.services.principal_service import principal_service

router = APIRouter(prefix="/principals", tags=["Principals"])


@router.post("", response_model=PrincipalResponse)
async def create_principal(
    request: PrincipalRequest,
    context: TenantContext = Depends(require_user_tenant_context),
):
    """Create principal."""
    return await principal_service.create_principal(context.db, request)


@router.put("/{principal_id}", response_model=PrincipalResponse)
async def update_principal(
    principal_id: str,
    request: PrincipalRequest,
    context: TenantContext = Depends(require_user_tenant_context),
):
    """Update principal."""
    return await principal_service.update_principal(context.db, principal_id, request)


@router.post("/{principal_id}/revoke", response_model=PrincipalResponse)
async def revoke_principal(
    principal_id: str,
    context: TenantContext = Depends(require_user_tenant_context),
):
    """Revoke principal."""
    return await principal_service.revoke_principal(context.db, principal_id)
