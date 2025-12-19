"""
Tests for background cleanup task.
"""
import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock
from sqlalchemy import update

from registry_service.core.background_tasks import BackgroundTaskManager
from registry_service.core.database import AsyncSessionLocal
from registry_service.crud import agent_crud
from registry_service.services.agent_service import AgentRegistryService
from registry_service.models.agent import AgentTable
from soorma_common import AgentDefinition, AgentCapability


@pytest.mark.asyncio
async def test_background_task_manager_start_stop():
    """Test starting and stopping the background task manager."""
    manager = BackgroundTaskManager()
    
    # Start tasks
    await manager.start()
    assert manager._running is True
    assert manager._cleanup_task is not None
    
    # Stop tasks
    await manager.stop()
    assert manager._running is False


@pytest.mark.asyncio
async def test_background_task_manager_double_start():
    """Test that starting twice doesn't create duplicate tasks."""
    manager = BackgroundTaskManager()
    
    await manager.start()
    first_task = manager._cleanup_task
    
    # Try starting again
    await manager.start()
    second_task = manager._cleanup_task
    
    # Should be the same task
    assert first_task == second_task
    
    await manager.stop()


@pytest.mark.asyncio
async def test_cleanup_expired_agents():
    """Test that the cleanup task removes expired agents."""
    async with AsyncSessionLocal() as db:
        # Create test agents
        active_agent = AgentDefinition(
            agent_id="cleanup-active",
            name="Active Agent",
            description="Should not be deleted",
            capabilities=[],
            consumed_events=[],
            produced_events=[]
        )
        expired_agent = AgentDefinition(
            agent_id="cleanup-expired",
            name="Expired Agent",
            description="Should be deleted",
            capabilities=[],
            consumed_events=[],
            produced_events=[]
        )
        
        # Register both agents
        await AgentRegistryService.register_agent(db, active_agent)
        await AgentRegistryService.register_agent(db, expired_agent)
        
        # Expire one agent using SQL update
        old_heartbeat = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=2)
        await db.execute(
            update(AgentTable)
            .where(AgentTable.agent_id == "cleanup-expired")
            .values(last_heartbeat=old_heartbeat)
        )
        await db.commit()
        
        # Manually trigger cleanup
        deleted_count = await agent_crud.delete_expired_agents(db, ttl_seconds=1800)
        await db.commit()
        
        assert deleted_count >= 1
        
        # Verify expired agent is gone
        expired_check = await agent_crud.get_agent_by_id(
            db,
            "cleanup-expired",
            include_expired=True
        )
        assert expired_check is None
        
        # Verify active agent still exists
        active_check = await agent_crud.get_agent_by_id(
            db,
            "cleanup-active",
            include_expired=True
        )
        assert active_check is not None


@pytest.mark.asyncio
async def test_cleanup_with_no_expired_agents():
    """Test cleanup when there are no expired agents."""
    async with AsyncSessionLocal() as db:
        # Register an active agent
        active_agent = AgentDefinition(
            agent_id="cleanup-active-only",
            name="Active Only",
            description="Active agent",
            capabilities=[],
            consumed_events=[],
            produced_events=[]
        )
        await AgentRegistryService.register_agent(db, active_agent)
        
        # Run cleanup
        deleted_count = await agent_crud.delete_expired_agents(db, ttl_seconds=300)
        await db.commit()
        
        # No agents should be deleted
        assert deleted_count == 0
        
        # Agent should still exist
        agent_check = await agent_crud.get_agent_by_id(
            db,
            "cleanup-active-only",
            include_expired=True
        )
        assert agent_check is not None


@pytest.mark.asyncio
async def test_cleanup_loop_error_handling():
    """Test that cleanup loop continues despite errors."""
    manager = BackgroundTaskManager()
    
    # Mock the delete_expired_agents to raise an error once
    call_count = 0
    original_delete = agent_crud.delete_expired_agents
    
    async def mock_delete_with_error(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("Simulated error")
        return await original_delete(*args, **kwargs)
    
    with patch.object(agent_crud, 'delete_expired_agents', side_effect=mock_delete_with_error):
        # Start manager with very short interval for testing
        with patch('registry_service.core.config.settings.AGENT_CLEANUP_INTERVAL_SECONDS', 0.1):
            await manager.start()
            
            # Wait for a couple of cleanup cycles
            await asyncio.sleep(0.3)
            
            # Task should still be running despite error
            assert manager._running is True
            assert not manager._cleanup_task.done()
            
            await manager.stop()


@pytest.mark.asyncio
async def test_multiple_expired_agents_cleanup():
    """Test cleanup of multiple expired agents at once."""
    async with AsyncSessionLocal() as db:
        # Create multiple expired agents
        for i in range(5):
            agent = AgentDefinition(
                agent_id=f"multi-expired-{i}",
                name=f"Expired {i}",
                description="Expired agent",
                capabilities=[],
                consumed_events=[],
                produced_events=[]
            )
            await AgentRegistryService.register_agent(db, agent)
            
            # Expire it using SQL update
            old_heartbeat = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)
            await db.execute(
                update(AgentTable)
                .where(AgentTable.agent_id == f"multi-expired-{i}")
                .values(last_heartbeat=old_heartbeat)
            )
        
        await db.commit()
        
        # Run cleanup
        deleted_count = await agent_crud.delete_expired_agents(db, ttl_seconds=1800)
        await db.commit()
        
        assert deleted_count >= 5
