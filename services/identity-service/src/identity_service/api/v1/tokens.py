"""Token issuance API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from soorma_common.models import TokenIssueRequest, TokenIssueResponse

from identity_service.core.dependencies import (
    TenantContext,
    require_admin_authorization,
    require_user_tenant_context,
)
from identity_service.services.errors import IdentityServiceError
from identity_service.services.token_service import token_service

router = APIRouter(prefix="/tokens", tags=["Tokens"])


@router.post("/issue", response_model=TokenIssueResponse)
async def issue_token(
    request: TokenIssueRequest,
    _admin: None = Depends(require_admin_authorization),
    context: TenantContext = Depends(require_user_tenant_context),
):
    """Issue token."""
    try:
        return await token_service.issue_token(context.db, request)
    except IdentityServiceError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={
                "code": exc.code,
                "message": exc.message,
                "correlation_id": context.correlation_id,
            },
        ) from exc
