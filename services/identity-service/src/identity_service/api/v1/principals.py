"""Principal lifecycle API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from soorma_common.models import PrincipalRequest, PrincipalResponse

from identity_service.core.dependencies import (
    TenantContext,
    get_tenant_context,
    require_admin_authorization,
)
from identity_service.crud.principals import principal_repository
from identity_service.crud.tenant_domains import tenant_domain_repository
from identity_service.services.principal_service import principal_service

router = APIRouter(prefix="/principals", tags=["Principals"])


async def _ensure_tenant_domain_platform_match(
    context: TenantContext,
    tenant_domain_id: str,
) -> None:
    """Fail closed when tenant domain is outside current platform tenant context."""
    tenant_domain = await tenant_domain_repository.get_domain(context.db, tenant_domain_id)
    if tenant_domain is None:
        raise HTTPException(status_code=404, detail="Tenant domain was not found.")

    if str(tenant_domain["platform_tenant_id"]) != context.platform_tenant_id:
        raise HTTPException(
            status_code=403,
            detail="Tenant domain does not belong to current platform tenant context.",
        )


async def _ensure_principal_platform_match(
    context: TenantContext,
    principal_id: str,
    request_tenant_domain_id: str | None = None,
) -> None:
    """Fail closed for cross-tenant access and inconsistent update payload scope."""
    principal = await principal_repository.get_principal(context.db, principal_id)
    if principal is None:
        raise HTTPException(status_code=404, detail="Principal was not found.")

    principal_tenant_domain_id = str(principal["tenant_domain_id"])
    if (
        request_tenant_domain_id is not None
        and request_tenant_domain_id != principal_tenant_domain_id
    ):
        raise HTTPException(
            status_code=400,
            detail="Principal tenant domain in payload does not match persisted principal tenant domain.",
        )

    await _ensure_tenant_domain_platform_match(
        context,
        principal_tenant_domain_id,
    )


@router.post("", response_model=PrincipalResponse)
async def create_principal(
    request: PrincipalRequest,
    _admin: None = Depends(require_admin_authorization),
    context: TenantContext = Depends(get_tenant_context),
):
    """Create principal."""
    await _ensure_tenant_domain_platform_match(context, request.tenant_domain_id)
    return await principal_service.create_principal(context.db, request)


@router.put("/{principal_id}", response_model=PrincipalResponse)
async def update_principal(
    principal_id: str,
    request: PrincipalRequest,
    _admin: None = Depends(require_admin_authorization),
    context: TenantContext = Depends(get_tenant_context),
):
    """Update principal."""
    await _ensure_principal_platform_match(
        context,
        principal_id,
        request_tenant_domain_id=request.tenant_domain_id,
    )
    return await principal_service.update_principal(context.db, principal_id, request)


@router.post("/{principal_id}/revoke", response_model=PrincipalResponse)
async def revoke_principal(
    principal_id: str,
    _admin: None = Depends(require_admin_authorization),
    context: TenantContext = Depends(get_tenant_context),
):
    """Revoke principal."""
    await _ensure_principal_platform_match(context, principal_id)
    return await principal_service.revoke_principal(context.db, principal_id)
