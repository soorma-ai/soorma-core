"""
CRUD operations for event registry.
"""
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from soorma_common import EventDefinition
from ..models import EventTable
from ..core.cache import cache_event, invalidate_event_cache


class EventCRUD:
    """CRUD operations for events."""
    
    async def create_event(
        self, 
        db: AsyncSession, 
        event: EventDefinition,
        developer_tenant_id: UUID
    ) -> EventTable:
        """
        Create a new event in the database.
        
        Args:
            db: Database session
            event: Event definition to create
            developer_tenant_id: Developer's own tenant UUID
            
        Returns:
            Created EventTable instance
        """
        event_table = EventTable(
            event_name=event.event_name,
            topic=event.topic,
            description=event.description,
            payload_schema=event.payload_schema,
            response_schema=event.response_schema,
            tenant_id=developer_tenant_id
        )
        db.add(event_table)
        await db.flush()
        
        # Invalidate cache for this event and related queries
        invalidate_event_cache(event.event_name)
        
        return event_table
    
    async def upsert_event(
        self, 
        db: AsyncSession, 
        event: EventDefinition,
        developer_tenant_id: UUID
    ) -> tuple[EventTable, bool]:
        """
        Create or update an event in the database.
        
        Args:
            db: Database session
            event: Event definition to upsert
            developer_tenant_id: Developer's own tenant UUID
            
        Returns:
            Tuple of (EventTable instance, was_created: bool)
            was_created is True if a new event was created, False if updated
        """
        # Check if event exists (by event_name and developer_tenant_id - new unique constraint)
        existing = await self.get_event_by_name(db, event.event_name, developer_tenant_id)
        
        if existing:
            # Update existing event
            existing.description = event.description
            existing.payload_schema = event.payload_schema
            existing.response_schema = event.response_schema
            await db.flush()
            
            # Invalidate cache
            invalidate_event_cache(event.event_name)
            
            return existing, False
        else:
            # Create new event
            event_table = await self.create_event(db, event, developer_tenant_id)
            return event_table, True
    
    async def get_event_by_name_and_topic(
        self, 
        db: AsyncSession, 
        event_name: str,
        topic: str
    ) -> Optional[EventTable]:
        """
        Get an event by its name and topic.
        
        Args:
            db: Database session
            event_name: Name of the event
            topic: Topic of the event
            
        Returns:
            EventTable if found, None otherwise
        """
        result = await db.execute(
            select(EventTable).where(
                EventTable.event_name == event_name,
                EventTable.topic == topic
            )
        )
        return result.scalar_one_or_none()
    
    @cache_event
    async def get_event_by_name(
        self, 
        db: AsyncSession, 
        event_name: str,
        tenant_id: UUID
    ) -> Optional[EventTable]:
        """
        Get an event by its name within a tenant.
        
        Args:
            db: Database session
            event_name: Name of the event
            tenant_id: Tenant ID from authentication
            
        Returns:
            EventTable if found, None otherwise
        """
        result = await db.execute(
            select(EventTable).where(
                EventTable.event_name == event_name,
                EventTable.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()
    
    @cache_event
    async def get_events_by_topic(
        self, 
        db: AsyncSession, 
        topic: str,
        tenant_id: UUID
    ) -> List[EventTable]:
        """
        Get all events for a specific topic.
        
        Args:
            db: Database session
            topic: Topic to filter by
            tenant_id: Tenant ID from authentication
            
        Returns:
            List of EventTable instances
        """
        result = await db.execute(
            select(EventTable)
            .where(
                EventTable.topic == topic,
                EventTable.tenant_id == tenant_id
            )
            .order_by(EventTable.event_name)
        )
        return list(result.scalars().all())
    
    @cache_event
    async def get_all_events(
        self, 
        db: AsyncSession,
        tenant_id: UUID
    ) -> List[EventTable]:
        """
        Get all events for a tenant.
        
        Args:
            db: Database session
            tenant_id: Tenant ID from authentication
            
        Returns:
            List of all EventTable instances for this tenant
        """
        result = await db.execute(
            select(EventTable)
            .where(EventTable.tenant_id == tenant_id)
            .order_by(EventTable.event_name)
        )
        return list(result.scalars().all())
    
    @cache_event
    async def event_exists(
        self, 
        db: AsyncSession, 
        event_name: str
    ) -> bool:
        """
        Check if an event exists.
        
        Args:
            db: Database session
            event_name: Name of the event
            
        Returns:
            True if event exists, False otherwise
        """
        result = await db.execute(
            select(EventTable.id).where(EventTable.event_name == event_name)
        )
        return result.scalar_one_or_none() is not None
    
    def event_to_dto(self, event: EventTable) -> EventDefinition:
        """
        Convert EventTable to EventDefinition DTO.
        
        Args:
            event: EventTable instance
            
        Returns:
            EventDefinition DTO
        """
        return EventDefinition(
            event_name=event.event_name,
            topic=event.topic,
            description=event.description,
            payload_schema=event.payload_schema,
            response_schema=event.response_schema
        )


# Singleton instance
event_crud = EventCRUD()
