"""Token issuance API endpoints."""

from fastapi import APIRouter, Depends
from soorma_common.models import TokenIssueRequest, TokenIssueResponse

from identity_service.core.dependencies import TenantContext, require_user_tenant_context
from identity_service.services.token_service import token_service

router = APIRouter(prefix="/tokens", tags=["Tokens"])


@router.post("/issue", response_model=TokenIssueResponse)
async def issue_token(
    request: TokenIssueRequest,
    context: TenantContext = Depends(require_user_tenant_context),
):
    """Issue token."""
    return await token_service.issue_token(context.db, request)
