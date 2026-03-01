"""
API endpoints for event registry.
"""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Query, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from soorma_common import (
    EventRegistrationRequest,
    EventRegistrationResponse,
    EventQueryResponse,
)
from ...services import EventRegistryService
from ...core.database import get_db
from ..dependencies import get_auth_context

router = APIRouter(prefix="/events", tags=["events"])


@router.post("", response_model=EventRegistrationResponse)
async def register_event(
    request: EventRegistrationRequest,
    db: AsyncSession = Depends(get_db),
    auth_context: tuple[UUID, UUID] = Depends(get_auth_context)
) -> EventRegistrationResponse:
    """
    Register or update an event in the event registry (upsert operation).
    
    Args:
        request: Event registration request with event definition
        db: Database session (injected)
        auth_context: (tenant_id, user_id) from authentication headers
        
    Returns:
        EventRegistrationResponse with registration status
        
    Raises:
        HTTPException: 400 if registration fails
    """
    tenant_id, user_id = auth_context
    response = await EventRegistryService.register_event(
        db, request.event, tenant_id, user_id
    )
    
    # If registration failed, return 400 Bad Request
    if not response.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=response.message
        )
    
    return response


@router.get("", response_model=EventQueryResponse)
async def query_events(
    event_name: Optional[str] = Query(None, description="Filter by event name"),
    topic: Optional[str] = Query(None, description="Filter by topic"),
    db: AsyncSession = Depends(get_db),
    auth_context: tuple[UUID, UUID] = Depends(get_auth_context)
) -> EventQueryResponse:
    """
    Query events based on filters. Returns all events if no filters provided.
    Automatically filters by tenant_id from auth context.
    
    Args:
        event_name: Optional event name filter
        topic: Optional topic filter
        db: Database session (injected)
        auth_context: (tenant_id, user_id) from authentication headers
        
    Returns:
        EventQueryResponse with matching events
    """
    tenant_id, user_id = auth_context
    return await EventRegistryService.query_events(
        db=db,
        tenant_id=tenant_id,
        event_name=event_name,
        topic=topic
    )
