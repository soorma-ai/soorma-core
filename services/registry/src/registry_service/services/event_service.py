"""
Service layer for event registry operations.
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from soorma_common import (
    EventDefinition,
    EventRegistrationResponse,
    EventQueryResponse,
)
from ..crud import event_crud


class EventRegistryService:
    """Service for managing event registrations."""
    
    @staticmethod
    async def register_event(
        db: AsyncSession,
        event: EventDefinition
    ) -> EventRegistrationResponse:
        """
        Register or update an event in the registry (upsert operation).
        
        Args:
            db: Database session
            event: Event definition to register/update
            
        Returns:
            EventRegistrationResponse with registration status
        """
        try:
            # Upsert the event
            event_table, was_created = await event_crud.upsert_event(db, event)
            await db.commit()
            
            if was_created:
                return EventRegistrationResponse(
                    event_name=event.event_name,
                    success=True,
                    message=f"Event '{event.event_name}' registered successfully."
                )
            else:
                return EventRegistrationResponse(
                    event_name=event.event_name,
                    success=True,
                    message=f"Event '{event.event_name}' updated successfully."
                )
        except Exception as e:
            await db.rollback()
            return EventRegistrationResponse(
                event_name=event.event_name,
                success=False,
                message=f"Failed to register event: {str(e)}"
            )
    
    @staticmethod
    async def query_events(
        db: AsyncSession,
        event_name: Optional[str] = None,
        topic: Optional[str] = None
    ) -> EventQueryResponse:
        """
        Query events based on filters.
        
        Args:
            db: Database session
            event_name: Specific event name to query
            topic: Filter by topic
            
        Returns:
            EventQueryResponse with matching events
        """
        try:
            if event_name:
                event_table = await event_crud.get_event_by_name(db, event_name)
                events = [event_crud.event_to_dto(event_table)] if event_table else []
            elif topic:
                event_tables = await event_crud.get_events_by_topic(db, topic)
                events = [event_crud.event_to_dto(e) for e in event_tables]
            else:
                event_tables = await event_crud.get_all_events(db)
                events = [event_crud.event_to_dto(e) for e in event_tables]
            
            return EventQueryResponse(
                events=events,
                count=len(events)
            )
        except Exception as e:
            return EventQueryResponse(
                events=[],
                count=0
            )
