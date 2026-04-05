"""Mapping policy API endpoints."""

from fastapi import APIRouter, Depends
from soorma_common.models import MappingEvaluationRequest, MappingEvaluationResponse

from identity_service.core.dependencies import TenantContext, require_user_tenant_context
from identity_service.services.mapping_service import mapping_service

router = APIRouter(prefix="/mappings", tags=["Mappings"])


@router.post("/evaluate", response_model=MappingEvaluationResponse)
async def evaluate_mapping(
    request: MappingEvaluationRequest,
    context: TenantContext = Depends(require_user_tenant_context),
):
    """Evaluate mapping/collision policy."""
    return await mapping_service.evaluate_mapping(context.db, request)
