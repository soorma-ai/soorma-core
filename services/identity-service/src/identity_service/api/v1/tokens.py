"""Token issuance API endpoints."""

from fastapi import APIRouter, Depends
from soorma_common.models import TokenIssueRequest, TokenIssueResponse

from identity_service.core.dependencies import (
    TenantContext,
    get_tenant_context,
    require_admin_authorization,
)
from identity_service.crud.principals import principal_repository
from identity_service.crud.tenant_domains import tenant_domain_repository
from identity_service.services.errors import IdentityServiceError
from identity_service.services.token_service import token_service

router = APIRouter(prefix="/tokens", tags=["Tokens"])


async def _ensure_principal_platform_match(
    context: TenantContext,
    principal_id: str,
) -> None:
    """Fail closed when principal is outside current platform tenant context."""
    principal = await principal_repository.get_principal(context.db, principal_id)
    if principal is None:
        raise IdentityServiceError(
            code="principal_not_found",
            message="Principal was not found.",
            status_code=404,
        )

    tenant_domain = await tenant_domain_repository.get_domain(
        context.db,
        str(principal["tenant_domain_id"]),
    )
    if tenant_domain is None:
        raise IdentityServiceError(
            code="tenant_domain_not_found",
            message="Tenant domain was not found.",
            status_code=404,
        )

    if str(tenant_domain["platform_tenant_id"]) != context.platform_tenant_id:
        raise IdentityServiceError(
            code="principal_platform_tenant_mismatch",
            message="Principal does not belong to current platform tenant context.",
            status_code=403,
        )


@router.post("/issue", response_model=TokenIssueResponse)
async def issue_token(
    request: TokenIssueRequest,
    _admin: None = Depends(require_admin_authorization),
    context: TenantContext = Depends(get_tenant_context),
):
    """Issue token."""
    try:
        await _ensure_principal_platform_match(context, request.principal_id)
        return await token_service.issue_token(context.db, request)
    except IdentityServiceError as exc:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=exc.status_code,
            detail={
                "code": exc.code,
                "message": exc.message,
                "correlation_id": context.correlation_id,
            },
        ) from exc
