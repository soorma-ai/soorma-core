"""
API endpoints for event registry.
"""
from typing import Optional
from fastapi import APIRouter, Query, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from soorma_common import (
    EventRegistrationRequest,
    EventRegistrationResponse,
    EventQueryResponse,
)
from ...services import EventRegistryService
from ...core.database import get_db

router = APIRouter(prefix="/events", tags=["events"])


@router.post("", response_model=EventRegistrationResponse)
async def register_event(
    request: EventRegistrationRequest,
    db: AsyncSession = Depends(get_db)
) -> EventRegistrationResponse:
    """
    Register or update an event in the event registry (upsert operation).
    
    Args:
        request: Event registration request with event definition
        db: Database session (injected)
        
    Returns:
        EventRegistrationResponse with registration status
        
    Raises:
        HTTPException: 400 if registration fails
    """
    response = await EventRegistryService.register_event(db, request.event)
    
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
    db: AsyncSession = Depends(get_db)
) -> EventQueryResponse:
    """
    Query events based on filters. Returns all events if no filters provided.
    
    Args:
        event_name: Optional event name filter
        topic: Optional topic filter
        db: Database session (injected)
        
    Returns:
        EventQueryResponse with matching events
    """
    return await EventRegistryService.query_events(
        db=db,
        event_name=event_name,
        topic=topic
    )
