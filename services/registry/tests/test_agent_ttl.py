"""
Unit tests for agent TTL and heartbeat functionality.
"""
import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update

from registry_service.core.database import AsyncSessionLocal
from registry_service.core.cache import invalidate_agent_cache
from registry_service.crud import agent_crud
from registry_service.services.agent_service import AgentRegistryService
from registry_service.models.agent import AgentTable
from soorma_common import AgentDefinition, AgentCapability


@pytest.fixture
def sample_agent():
    """Create a sample agent definition for testing."""
    return AgentDefinition(
        agent_id="test-agent-ttl",
        name="Test Agent TTL",
        description="Agent for testing TTL functionality",
        capabilities=[
            AgentCapability(
                task_name="test_task",
                description="Test task",
                consumed_event="test.event",
                produced_events=["test.result"]
            )
        ]
    )


@pytest.mark.asyncio
async def test_agent_creation_sets_heartbeat(sample_agent):
    """Test that creating an agent sets the last_heartbeat timestamp."""
    async with AsyncSessionLocal() as db:
        # Register agent
        result = await AgentRegistryService.register_agent(db, sample_agent)
        assert result.success is True
        
        # Retrieve agent and check last_heartbeat
        agent_table = await agent_crud.get_agent_by_id(
            db, 
            sample_agent.agent_id,
            include_expired=True
        )
        assert agent_table is not None
        assert agent_table.last_heartbeat is not None
        
        # Heartbeat should be recent (within last 5 seconds)
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        time_diff = (now - agent_table.last_heartbeat).total_seconds()
        assert time_diff < 5


@pytest.mark.asyncio
async def test_update_heartbeat(sample_agent):
    """Test updating an agent's heartbeat."""
    async with AsyncSessionLocal() as db:
        # Register agent
        await AgentRegistryService.register_agent(db, sample_agent)
        
        # Get initial heartbeat
        agent_table = await agent_crud.get_agent_by_id(
            db,
            sample_agent.agent_id,
            include_expired=True
        )
        initial_heartbeat = agent_table.last_heartbeat
        
        # Wait a moment
        await asyncio.sleep(0.1)
        
        # Update heartbeat
        success = await agent_crud.update_heartbeat(db, sample_agent.agent_id)
        await db.commit()
        assert success is True
        
        # Re-fetch agent to check heartbeat was updated
        updated_agent_table = await agent_crud.get_agent_by_id(
            db,
            sample_agent.agent_id,
            include_expired=True
        )
        assert updated_agent_table.last_heartbeat > initial_heartbeat


@pytest.mark.asyncio
async def test_refresh_agent_heartbeat_service(sample_agent):
    """Test the service layer heartbeat refresh."""
    async with AsyncSessionLocal() as db:
        # Register agent
        await AgentRegistryService.register_agent(db, sample_agent)
        
        # Refresh heartbeat via service
        result = await AgentRegistryService.refresh_agent_heartbeat(
            db,
            sample_agent.agent_id
        )
        
        assert result.success is True
        assert "refreshed successfully" in result.message


@pytest.mark.asyncio
async def test_refresh_nonexistent_agent():
    """Test refreshing heartbeat for a non-existent agent."""
    async with AsyncSessionLocal() as db:
        result = await AgentRegistryService.refresh_agent_heartbeat(
            db,
            "nonexistent-agent"
        )
        
        assert result.success is False
        assert "not found" in result.message


@pytest.mark.asyncio
async def test_get_expired_agents(sample_agent):
    """Test retrieving expired agents."""
    async with AsyncSessionLocal() as db:
        # Register agent
        await AgentRegistryService.register_agent(db, sample_agent)
        
        # Get agent and manually set old heartbeat
        agent_table = await agent_crud.get_agent_by_id(
            db,
            sample_agent.agent_id,
            include_expired=True
        )
        
        # Set heartbeat to 1 hour ago
        old_heartbeat = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)
        await db.execute(
            update(AgentTable)
            .where(AgentTable.agent_id == sample_agent.agent_id)
            .values(last_heartbeat=old_heartbeat)
        )
        await db.commit()
        
        # Invalidate cache so queries use fresh data
        invalidate_agent_cache(sample_agent.agent_id)
        
        # Get expired agents (TTL = 30 minutes)
        expired = await agent_crud.get_expired_agents(db, ttl_seconds=1800)
        
        assert len(expired) > 0
        assert any(a.agent_id == sample_agent.agent_id for a in expired)


@pytest.mark.asyncio
async def test_get_expired_agents_excludes_active(sample_agent):
    """Test that get_expired_agents doesn't return active agents."""
    async with AsyncSessionLocal() as db:
        # Register agent (with current heartbeat)
        await AgentRegistryService.register_agent(db, sample_agent)
        
        # Get expired agents with short TTL (should not include our agent)
        expired = await agent_crud.get_expired_agents(db, ttl_seconds=3600)
        
        # Our agent should not be in expired list
        assert not any(a.agent_id == sample_agent.agent_id for a in expired)


@pytest.mark.asyncio
async def test_delete_expired_agents(sample_agent):
    """Test deleting expired agents."""
    # Clear cache before test
    from registry_service.core.cache import _agent_cache
    _agent_cache.clear()
    
    async with AsyncSessionLocal() as db:
        # Register agent
        await AgentRegistryService.register_agent(db, sample_agent)
        
        # Set old heartbeat using SQL update
        old_heartbeat = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)
        await db.execute(
            update(AgentTable)
            .where(AgentTable.agent_id == sample_agent.agent_id)
            .values(last_heartbeat=old_heartbeat)
        )
        await db.commit()
        
        # Delete expired agents
        deleted_count = await agent_crud.delete_expired_agents(db, ttl_seconds=1800)
        await db.commit()
        
        assert deleted_count > 0
    
    # Clear cache and use fresh session to verify deletion
    _agent_cache.clear()
    async with AsyncSessionLocal() as db:
        # Verify agent is gone
        agent_table = await agent_crud.get_agent_by_id(
            db,
            sample_agent.agent_id,
            include_expired=True
        )
        assert agent_table is None
