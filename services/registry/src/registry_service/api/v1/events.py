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
from ..dependencies import get_developer_tenant_id

router = APIRouter(prefix="/events", tags=["events"])


@router.post("", response_model=EventRegistrationResponse)
async def register_event(
    request: EventRegistrationRequest,
    db: AsyncSession = Depends(get_db),
    developer_tenant_id: UUID = Depends(get_developer_tenant_id)
) -> EventRegistrationResponse:
    """
    Register or update an event in the event registry (upsert operation).
    
    Args:
        request: Event registration request with event definition
        db: Database session (injected)
        developer_tenant_id: Developer's own tenant UUID from X-Tenant-ID header
        
    Returns:
        EventRegistrationResponse with registration status
        
    Raises:
        HTTPException: 400 if registration fails
    """
    response = await EventRegistryService.register_event(
        db, request.event, developer_tenant_id
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
    developer_tenant_id: UUID = Depends(get_developer_tenant_id)
) -> EventQueryResponse:
    """
    Query events based on filters. Returns all events if no filters provided.
    Automatically filters by developer_tenant_id from auth context.
    
    Args:
        event_name: Optional event name filter
        topic: Optional topic filter
        db: Database session (injected)
        developer_tenant_id: Developer's own tenant UUID from X-Tenant-ID header
        
    Returns:
        EventQueryResponse with matching events
    """
    return await EventRegistryService.query_events(
        db=db,
        developer_tenant_id=developer_tenant_id,
        event_name=event_name,
        topic=topic
    )
