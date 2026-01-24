"""Sessions API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Query

from memory_service.core.dependencies import TenantContext, get_tenant_context
from soorma_common.models import (
    SessionCreate,
    SessionSummary,
)
from memory_service.services.session_service import session_service

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.post("", response_model=SessionSummary, status_code=status.HTTP_201_CREATED)
async def create_session_endpoint(
    data: SessionCreate,
    context: TenantContext = Depends(get_tenant_context),
):
    """Create a new session."""
    return await session_service.create(context.db, context.tenant_id, context.user_id, data)


@router.get("", response_model=list[SessionSummary])
async def list_sessions_endpoint(
    limit: int = Query(20, ge=1, le=100),
    context: TenantContext = Depends(get_tenant_context),
):
    """List sessions for the authenticated user."""
    return await session_service.list(context.db, context.tenant_id, context.user_id, limit)


@router.get("/{session_id}", response_model=SessionSummary)
async def get_session_endpoint(
    session_id: str,
    context: TenantContext = Depends(get_tenant_context),
):
    """Get session details."""
    result = await session_service.get(context.db, context.tenant_id, session_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
        )
    return result


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session_endpoint(
    session_id: str,
    context: TenantContext = Depends(get_tenant_context),
):
    """Delete session."""
    deleted = await session_service.delete(context.db, context.tenant_id, session_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
        )
