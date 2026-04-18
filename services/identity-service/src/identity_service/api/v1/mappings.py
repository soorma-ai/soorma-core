"""Mapping policy API endpoints."""

from fastapi import APIRouter, Depends
from soorma_common.models import MappingEvaluationRequest, MappingEvaluationResponse

from identity_service.core.dependencies import (
    TenantContext,
    get_tenant_context,
    require_tenant_admin_authorization,
)
from identity_service.services.mapping_service import mapping_service

router = APIRouter(prefix="/mappings", tags=["Mappings"])


@router.post("/evaluate", response_model=MappingEvaluationResponse)
async def evaluate_mapping(
    request: MappingEvaluationRequest,
    _tenant_admin: str = Depends(require_tenant_admin_authorization),
    context: TenantContext = Depends(get_tenant_context),
):
    """Evaluate mapping/collision policy."""
    return await mapping_service.evaluate_mapping(context.db, request)
