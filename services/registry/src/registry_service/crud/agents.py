"""
CRUD operations for agent registry.
"""
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from soorma_common import AgentDefinition, AgentCapability
from ..models import AgentTable, AgentCapabilityTable
from ..core.cache import cache_agent, invalidate_agent_cache


def _ensure_utc(dt: datetime) -> datetime:
    """Ensure datetime has UTC timezone info (for SQLite compatibility)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _now_utc() -> datetime:
    """Get current UTC time without timezone info (for SQLite compatibility)."""
    # For SQLite, we store naive datetimes but represent UTC time
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AgentCRUD:
    """CRUD operations for agents."""
    
    async def create_agent(
        self, 
        db: AsyncSession, 
        agent: AgentDefinition
    ) -> AgentTable:
        """
        Create a new agent in the database.
        
        Args:
            db: Database session
            agent: Agent definition to create
            
        Returns:
            Created AgentTable instance
        """
        # Create agent table entry
        agent_table = AgentTable(
            agent_id=agent.agent_id,
            name=agent.name,
            description=agent.description,
            consumed_events=agent.consumed_events,
            produced_events=agent.produced_events,
            last_heartbeat=_now_utc()
        )
        db.add(agent_table)
        await db.flush()  # Get the ID
        
        # Clean up any orphaned capabilities that might exist with this agent_table_id
        # This can happen due to ID reuse in SQLite or after many delete/create cycles
        await db.execute(
            delete(AgentCapabilityTable).where(
                AgentCapabilityTable.agent_table_id == agent_table.id
            )
        )
        await db.flush()
        
        # Create capability entries
        for capability in agent.capabilities:
            capability_table = AgentCapabilityTable(
                agent_table_id=agent_table.id,
                task_name=capability.task_name,
                description=capability.description,
                consumed_event=capability.consumed_event,
                produced_events=capability.produced_events
            )
            db.add(capability_table)
        
        await db.flush()
        
        # Refresh to load relationships
        await db.refresh(agent_table, ["capabilities"])
        
        # Invalidate cache for this agent
        invalidate_agent_cache(agent.agent_id)
        
        return agent_table
    
    async def upsert_agent(
        self, 
        db: AsyncSession, 
        agent: AgentDefinition
    ) -> tuple[AgentTable, bool]:
        """
        Create or update an agent in the database.
        
        Args:
            db: Database session
            agent: Agent definition to upsert
            
        Returns:
            Tuple of (AgentTable instance, was_created: bool)
            was_created is True if a new agent was created, False if updated
        """
        # Check if agent exists (including expired ones)
        existing = await self.get_agent_by_id(db, agent.agent_id, include_expired=True)
        
        if existing:
            # Update existing agent
            existing.name = agent.name
            existing.description = agent.description
            existing.consumed_events = agent.consumed_events
            existing.produced_events = agent.produced_events
            existing.last_heartbeat = _now_utc()
            
            # Delete old capabilities
            await db.execute(
                delete(AgentCapabilityTable).where(
                    AgentCapabilityTable.agent_table_id == existing.id
                )
            )
            await db.flush()
            
            # Add new capabilities
            for capability in agent.capabilities:
                capability_table = AgentCapabilityTable(
                    agent_table_id=existing.id,
                    task_name=capability.task_name,
                    description=capability.description,
                    consumed_event=capability.consumed_event,
                    produced_events=capability.produced_events
                )
                db.add(capability_table)
            
            await db.flush()
            
            # Refresh to load relationships
            await db.refresh(existing, ["capabilities"])
            
            # Invalidate cache
            invalidate_agent_cache(agent.agent_id)
            
            return existing, False
        else:
            # Create new agent
            agent_table = await self.create_agent(db, agent)
            return agent_table, True
    
    @cache_agent
    async def get_agent_by_id(
        self, 
        db: AsyncSession, 
        agent_id: str,
        include_expired: bool = False,
        ttl_seconds: Optional[int] = None
    ) -> Optional[AgentTable]:
        """
        Get an agent by its ID.
        
        Args:
            db: Database session
            agent_id: ID of the agent
            include_expired: If False, exclude expired agents
            ttl_seconds: TTL in seconds (required if include_expired=False)
            
        Returns:
            AgentTable if found, None otherwise
        """
        query = select(AgentTable).where(AgentTable.agent_id == agent_id)
        
        if not include_expired and ttl_seconds is not None:
            expiry_threshold = _now_utc() - timedelta(seconds=ttl_seconds)
            query = query.where(AgentTable.last_heartbeat >= expiry_threshold)
        
        query = query.options(selectinload(AgentTable.capabilities))
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    @cache_agent
    async def get_agents_by_name(
        self, 
        db: AsyncSession, 
        name: str
    ) -> List[AgentTable]:
        """
        Get agents by name (partial match, case-insensitive).
        
        Args:
            db: Database session
            name: Name to search for
            
        Returns:
            List of AgentTable instances
        """
        result = await db.execute(
            select(AgentTable)
            .where(AgentTable.name.ilike(f"%{name}%"))
            .options(selectinload(AgentTable.capabilities))
            .order_by(AgentTable.name)
        )
        return list(result.scalars().all())
    
    @cache_agent
    async def get_agents_by_consumed_event(
        self, 
        db: AsyncSession, 
        event_name: str
    ) -> List[AgentTable]:
        """
        Get agents that consume a specific event.
        
        Args:
            db: Database session
            event_name: Name of the event
            
        Returns:
            List of AgentTable instances
        """
        # Get all agents and filter in Python for SQLite compatibility
        # (JSON columns don't support array contains operations)
        all_agents = await self.get_all_agents(db)
        return [a for a in all_agents if event_name in a.consumed_events]
    
    @cache_agent
    async def get_agents_by_produced_event(
        self, 
        db: AsyncSession, 
        event_name: str
    ) -> List[AgentTable]:
        """
        Get agents that produce a specific event.
        
        Args:
            db: Database session
            event_name: Name of the event
            
        Returns:
            List of AgentTable instances
        """
        # Get all agents and filter in Python for SQLite compatibility
        all_agents = await self.get_all_agents(db)
        return [a for a in all_agents if event_name in a.produced_events]
    
    @cache_agent
    async def get_all_agents(
        self, 
        db: AsyncSession,
        include_expired: bool = False,
        ttl_seconds: Optional[int] = None
    ) -> List[AgentTable]:
        """
        Get all agents.
        
        Args:
            db: Database session
            include_expired: If False, exclude expired agents
            ttl_seconds: TTL in seconds (required if include_expired=False)
            
        Returns:
            List of all AgentTable instances
        """
        query = select(AgentTable)
        
        if not include_expired and ttl_seconds is not None:
            expiry_threshold = _now_utc() - timedelta(seconds=ttl_seconds)
            query = query.where(AgentTable.last_heartbeat >= expiry_threshold)
        
        query = query.options(selectinload(AgentTable.capabilities)).order_by(AgentTable.name)
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    @cache_agent
    async def agent_exists(
        self, 
        db: AsyncSession, 
        agent_id: str
    ) -> bool:
        """
        Check if an agent exists.
        
        Args:
            db: Database session
            agent_id: ID of the agent
            
        Returns:
            True if agent exists, False otherwise
        """
        result = await db.execute(
            select(AgentTable.id).where(AgentTable.agent_id == agent_id)
        )
        return result.scalar_one_or_none() is not None
    
    async def update_heartbeat(
        self,
        db: AsyncSession,
        agent_id: str
    ) -> bool:
        """
        Update the heartbeat timestamp for an agent.
        
        Args:
            db: Database session
            agent_id: ID of the agent
            
        Returns:
            True if agent was found and updated, False otherwise
        """
        agent = await self.get_agent_by_id(db, agent_id, include_expired=True)
        if not agent:
            return False
        
        agent.last_heartbeat = _now_utc()
        await db.flush()
        
        # Invalidate cache for this agent
        invalidate_agent_cache(agent_id)
        
        return True
    
    async def get_expired_agents(
        self,
        db: AsyncSession,
        ttl_seconds: int
    ) -> List[AgentTable]:
        """
        Get all agents whose last heartbeat is older than TTL.
        
        Args:
            db: Database session
            ttl_seconds: TTL in seconds
            
        Returns:
            List of expired AgentTable instances
        """
        expiry_threshold = _now_utc() - timedelta(seconds=ttl_seconds)
        result = await db.execute(
            select(AgentTable)
            .where(AgentTable.last_heartbeat < expiry_threshold)
            .options(selectinload(AgentTable.capabilities))
        )
        return list(result.scalars().all())
    
    async def delete_expired_agents(
        self,
        db: AsyncSession,
        ttl_seconds: int
    ) -> int:
        """
        Delete all agents whose last heartbeat is older than TTL.
        This method properly deletes agents one by one to trigger ORM-level cascades,
        ensuring that related records (capabilities, etc.) are also deleted.
        
        Args:
            db: Database session
            ttl_seconds: TTL in seconds
            
        Returns:
            Number of agents deleted
        """
        # Get expired agents with their relationships loaded
        expired_agents = await self.get_expired_agents(db, ttl_seconds)
        
        # Delete each agent individually to trigger ORM cascade
        # This ensures capabilities and other related records are properly deleted
        for agent in expired_agents:
            # Invalidate cache before deletion
            invalidate_agent_cache(agent.agent_id)
            
            # Delete using ORM (not bulk delete) to trigger cascade
            await db.delete(agent)
        
        await db.flush()
        
        return len(expired_agents)
    
    async def cleanup_orphaned_capabilities(
        self,
        db: AsyncSession
    ) -> int:
        """
        Clean up orphaned capabilities that reference non-existent agents.
        This should be called periodically by background tasks to maintain database integrity.
        
        Args:
            db: Database session
            
        Returns:
            Number of orphaned capabilities deleted
        """
        # Find capabilities that reference non-existent agents
        result = await db.execute(
            select(AgentCapabilityTable)
            .outerjoin(AgentTable, AgentCapabilityTable.agent_table_id == AgentTable.id)
            .where(AgentTable.id.is_(None))
        )
        orphaned_capabilities = list(result.scalars().all())
        
        # Delete orphaned capabilities
        for capability in orphaned_capabilities:
            await db.delete(capability)
        
        await db.flush()
        
        return len(orphaned_capabilities)
    
    def agent_to_dto(self, agent: AgentTable) -> AgentDefinition:
        """
        Convert AgentTable to AgentDefinition DTO.
        
        Args:
            agent: AgentTable instance (with capabilities loaded)
            
        Returns:
            AgentDefinition DTO
        """
        capabilities = [
            AgentCapability(
                task_name=cap.task_name,
                description=cap.description,
                consumed_event=cap.consumed_event,
                produced_events=cap.produced_events
            )
            for cap in agent.capabilities
        ]
        
        # Derive agent-level events from capabilities
        # If agent has legacy data in consumed_events/produced_events, use those
        # Otherwise, derive from capabilities
        if agent.consumed_events and agent.produced_events:
            consumed_events = agent.consumed_events
            produced_events = agent.produced_events
        else:
            # Derive from capabilities
            consumed_events = list(set(cap.consumed_event for cap in capabilities))
            produced_events = list(set(
                event 
                for cap in capabilities 
                for event in cap.produced_events
            ))
        
        return AgentDefinition(
            agent_id=agent.agent_id,
            name=agent.name,
            description=agent.description,
            capabilities=capabilities,
            consumed_events=consumed_events,
            produced_events=produced_events
        )


# Singleton instance
agent_crud = AgentCRUD()
