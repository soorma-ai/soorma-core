"""
Service layer for agent registry operations.
"""
from typing import Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from soorma_common import (
    AgentDefinition,
    AgentRegistrationResponse,
    AgentQueryResponse,
)
from ..crud import agent_crud
from ..core.config import settings


def _now_utc() -> datetime:
    """Get current UTC time without timezone info (for SQLite compatibility)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AgentRegistryService:
    """Service for managing agent registrations."""
    
    @staticmethod
    async def register_agent(
        db: AsyncSession,
        agent: AgentDefinition
    ) -> AgentRegistrationResponse:
        """
        Register or update an agent in the registry (upsert operation).
        
        Args:
            db: Database session
            agent: Agent definition to register/update
            
        Returns:
            AgentRegistrationResponse with registration status
        """
        try:
            # Derive agent-level events from capabilities if not provided
            if not agent.consumed_events:
                agent.consumed_events = list(set(cap.consumed_event for cap in agent.capabilities))
            
            if not agent.produced_events:
                agent.produced_events = list(set(
                    event 
                    for cap in agent.capabilities 
                    for event in cap.produced_events
                ))
            
            # Upsert the agent
            agent_table, was_created = await agent_crud.upsert_agent(db, agent)
            await db.commit()
            
            if was_created:
                return AgentRegistrationResponse(
                    agent_id=agent.agent_id,
                    success=True,
                    message=f"Agent '{agent.agent_id}' registered successfully."
                )
            else:
                return AgentRegistrationResponse(
                    agent_id=agent.agent_id,
                    success=True,
                    message=f"Agent '{agent.agent_id}' updated successfully."
                )
        except Exception as e:
            await db.rollback()
            return AgentRegistrationResponse(
                agent_id=agent.agent_id,
                success=False,
                message=f"Failed to register agent: {str(e)}"
            )
    
    @staticmethod
    async def refresh_agent_heartbeat(
        db: AsyncSession,
        agent_id: str
    ) -> AgentRegistrationResponse:
        """
        Refresh an agent's heartbeat to extend its TTL.
        
        Args:
            db: Database session
            agent_id: ID of the agent to refresh
            
        Returns:
            AgentRegistrationResponse with refresh status
        """
        try:
            success = await agent_crud.update_heartbeat(db, agent_id)
            
            if not success:
                return AgentRegistrationResponse(
                    agent_id=agent_id,
                    success=False,
                    message=f"Agent '{agent_id}' not found."
                )
            
            await db.commit()
            
            return AgentRegistrationResponse(
                agent_id=agent_id,
                success=True,
                message=f"Agent '{agent_id}' heartbeat refreshed successfully."
            )
        except Exception as e:
            await db.rollback()
            return AgentRegistrationResponse(
                agent_id=agent_id,
                success=False,
                message=f"Failed to refresh agent heartbeat: {str(e)}"
            )
    
    @staticmethod
    async def delete_agent(
        db: AsyncSession,
        agent_id: str
    ) -> bool:
        """
        Delete an agent.
        
        Args:
            db: Database session
            agent_id: ID of the agent
            
        Returns:
            True if deleted, False if not found
        """
        try:
            success = await agent_crud.delete_agent(db, agent_id)
            await db.commit()
            return success
        except Exception:
            await db.rollback()
            raise

    @staticmethod
    async def query_agents(
        db: AsyncSession,
        agent_id: Optional[str] = None,
        name: Optional[str] = None,
        consumed_event: Optional[str] = None,
        produced_event: Optional[str] = None,
        include_expired: bool = False
    ) -> AgentQueryResponse:
        """
        Query agents based on filters.
        
        Args:
            db: Database session
            agent_id: Specific agent ID to query
            name: Filter by agent name
            consumed_event: Filter by consumed event
            produced_event: Filter by produced event
            include_expired: If True, include expired agents in results
            
        Returns:
            AgentQueryResponse with matching agents
        """
        try:
            ttl_seconds = settings.AGENT_TTL_SECONDS if not include_expired else None
            
            if agent_id:
                agent_table = await agent_crud.get_agent_by_id(
                    db, 
                    agent_id,
                    include_expired=include_expired,
                    ttl_seconds=ttl_seconds
                )
                agents = [agent_crud.agent_to_dto(agent_table)] if agent_table else []
            elif name:
                agent_tables = await agent_crud.get_agents_by_name(db, name)
                # Filter expired agents manually for name search
                if not include_expired:
                    expiry_threshold = _now_utc() - timedelta(seconds=settings.AGENT_TTL_SECONDS)
                    agent_tables = [a for a in agent_tables if a.last_heartbeat >= expiry_threshold]
                agents = [agent_crud.agent_to_dto(a) for a in agent_tables]
            elif consumed_event:
                agent_tables = await agent_crud.get_agents_by_consumed_event(db, consumed_event)
                # Filter expired agents manually
                if not include_expired:
                    expiry_threshold = _now_utc() - timedelta(seconds=settings.AGENT_TTL_SECONDS)
                    agent_tables = [a for a in agent_tables if a.last_heartbeat >= expiry_threshold]
                agents = [agent_crud.agent_to_dto(a) for a in agent_tables]
            elif produced_event:
                agent_tables = await agent_crud.get_agents_by_produced_event(db, produced_event)
                # Filter expired agents manually
                if not include_expired:
                    expiry_threshold = _now_utc() - timedelta(seconds=settings.AGENT_TTL_SECONDS)
                    agent_tables = [a for a in agent_tables if a.last_heartbeat >= expiry_threshold]
                agents = [agent_crud.agent_to_dto(a) for a in agent_tables]
            else:
                agent_tables = await agent_crud.get_all_agents(
                    db,
                    include_expired=include_expired,
                    ttl_seconds=ttl_seconds
                )
                agents = [agent_crud.agent_to_dto(a) for a in agent_tables]
            
            return AgentQueryResponse(
                agents=agents,
                count=len(agents)
            )
        except Exception as e:
            return AgentQueryResponse(
                agents=[],
                count=0
            )
    
    @staticmethod
    async def cleanup_expired_agents(
        db: AsyncSession,
        ttl_seconds: Optional[int] = None
    ) -> int:
        """
        Cleanup expired agent registrations and orphaned capabilities.
        This method properly deletes agents through the CRUD layer,
        ensuring that related records (capabilities, etc.) are also deleted.
        Also cleans up any orphaned capabilities that reference non-existent agents.
        
        Args:
            db: Database session
            ttl_seconds: TTL in seconds (defaults to settings.AGENT_TTL_SECONDS)
            
        Returns:
            Number of agents deleted
        """
        if ttl_seconds is None:
            ttl_seconds = settings.AGENT_TTL_SECONDS
        
        try:
            # Delete expired agents
            deleted_count = await agent_crud.delete_expired_agents(db, ttl_seconds)
            
            # Clean up any orphaned capabilities (from past bugs or edge cases)
            orphaned_count = await agent_crud.cleanup_orphaned_capabilities(db)
            if orphaned_count > 0:
                from logging import getLogger
                logger = getLogger(__name__)
                logger.info(f"Cleaned up {orphaned_count} orphaned capability/capabilities")
            
            await db.commit()
            return deleted_count
        except Exception as e:
            await db.rollback()
            raise
