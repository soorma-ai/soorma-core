"""
Test for verifying that expired agent cleanup properly deletes related records.

This test specifically addresses the bug where deleting expired agents left
orphaned capabilities in the database, which could then appear in other agents.
"""
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from registry_service.core.database import AsyncSessionLocal
from registry_service.core.cache import invalidate_agent_cache
from registry_service.crud import agent_crud
from registry_service.services.agent_service import AgentRegistryService
from registry_service.models.agent import AgentTable, AgentCapabilityTable
from soorma_common import AgentDefinition, AgentCapability


@pytest.fixture
def agent_with_multiple_capabilities():
    """Create an agent with multiple capabilities for testing."""
    return AgentDefinition(
        agent_id="agent-with-caps",
        name="Agent With Capabilities",
        description="Agent for testing capability cascade deletion",
        capabilities=[
            AgentCapability(
                task_name="capability_one",
                description="First capability",
                consumed_event="event.one",
                produced_events=["result.one"]
            ),
            AgentCapability(
                task_name="capability_two",
                description="Second capability",
                consumed_event="event.two",
                produced_events=["result.two", "result.three"]
            ),
            AgentCapability(
                task_name="capability_three",
                description="Third capability",
                consumed_event="event.three",
                produced_events=["result.four"]
            )
        ]
    )


@pytest.mark.asyncio
async def test_expired_agent_cleanup_deletes_capabilities(agent_with_multiple_capabilities):
    """
    Test that when an expired agent is deleted, all its capabilities are also deleted.
    
    This is a regression test for the bug where bulk delete didn't trigger
    ORM-level cascades, leaving orphaned capabilities.
    """
    async with AsyncSessionLocal() as db:
        # Register agent with capabilities
        result = await AgentRegistryService.register_agent(db, agent_with_multiple_capabilities)
        assert result.success is True
        
        # Get the agent and verify capabilities exist
        agent_table = await agent_crud.get_agent_by_id(
            db,
            agent_with_multiple_capabilities.agent_id,
            include_expired=True
        )
        assert agent_table is not None
        agent_table_id = agent_table.id
        assert len(agent_table.capabilities) == 3
        
        # Verify capabilities are in database
        caps_result = await db.execute(
            select(AgentCapabilityTable).where(
                AgentCapabilityTable.agent_table_id == agent_table_id
            )
        )
        capabilities_before = list(caps_result.scalars().all())
        assert len(capabilities_before) == 3
        
        # Expire the agent by setting old heartbeat
        old_heartbeat = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=2)
        await db.execute(
            update(AgentTable)
            .where(AgentTable.agent_id == agent_with_multiple_capabilities.agent_id)
            .values(last_heartbeat=old_heartbeat)
        )
        await db.commit()
        
        # Clear cache to ensure fresh queries
        invalidate_agent_cache(agent_with_multiple_capabilities.agent_id)
        
        # Delete expired agents using the service layer (proper way)
        deleted_count = await AgentRegistryService.cleanup_expired_agents(db, ttl_seconds=1800)
        assert deleted_count == 1
        
        # Verify agent is deleted
        agent_check = await agent_crud.get_agent_by_id(
            db,
            agent_with_multiple_capabilities.agent_id,
            include_expired=True
        )
        assert agent_check is None
        
        # CRITICAL: Verify ALL capabilities are also deleted (not orphaned)
        caps_result_after = await db.execute(
            select(AgentCapabilityTable).where(
                AgentCapabilityTable.agent_table_id == agent_table_id
            )
        )
        capabilities_after = list(caps_result_after.scalars().all())
        assert len(capabilities_after) == 0, \
            f"Expected 0 capabilities after agent deletion, but found {len(capabilities_after)}"


@pytest.mark.asyncio
async def test_capabilities_not_orphaned_across_agents():
    """
    Test that capabilities from deleted agents don't appear in other agents.
    
    This verifies the specific issue where orphaned capabilities were somehow
    showing up within other agents' capability lists.
    """
    async with AsyncSessionLocal() as db:
        # Create two agents with different capabilities
        agent1 = AgentDefinition(
            agent_id="agent-one",
            name="Agent One",
            description="First agent",
            capabilities=[
                AgentCapability(
                    task_name="agent_one_task",
                    description="Task for agent one",
                    consumed_event="event.agent.one",
                    produced_events=["result.agent.one"]
                )
            ]
        )
        
        agent2 = AgentDefinition(
            agent_id="agent-two",
            name="Agent Two",
            description="Second agent",
            capabilities=[
                AgentCapability(
                    task_name="agent_two_task",
                    description="Task for agent two",
                    consumed_event="event.agent.two",
                    produced_events=["result.agent.two"]
                )
            ]
        )
        
        # Register both agents
        await AgentRegistryService.register_agent(db, agent1)
        await AgentRegistryService.register_agent(db, agent2)
        
        # Get agent1's capability ID for later verification
        agent1_table = await agent_crud.get_agent_by_id(db, "agent-one", include_expired=True)
        agent1_capability_ids = [cap.id for cap in agent1_table.capabilities]
        
        # Expire agent1
        old_heartbeat = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=2)
        await db.execute(
            update(AgentTable)
            .where(AgentTable.agent_id == "agent-one")
            .values(last_heartbeat=old_heartbeat)
        )
        await db.commit()
        
        # Clear caches
        invalidate_agent_cache("agent-one")
        invalidate_agent_cache("agent-two")
        
        # Delete expired agents (agent1)
        deleted_count = await AgentRegistryService.cleanup_expired_agents(db, ttl_seconds=1800)
        assert deleted_count == 1
        
        # Verify agent1 is deleted
        agent1_check = await agent_crud.get_agent_by_id(db, "agent-one", include_expired=True)
        assert agent1_check is None
        
        # Clear cache again to ensure fresh fetch
        invalidate_agent_cache("agent-two")
        
        # Get agent2 with fresh query
        agent2_table = await agent_crud.get_agent_by_id(db, "agent-two", include_expired=True)
        assert agent2_table is not None
        
        # CRITICAL: Verify agent2's capabilities don't include agent1's orphaned capabilities
        agent2_capability_ids = [cap.id for cap in agent2_table.capabilities]
        assert len(agent2_table.capabilities) == 1, \
            f"Expected agent2 to have 1 capability, found {len(agent2_table.capabilities)}"
        
        # Verify none of agent1's capabilities are in agent2
        for cap_id in agent1_capability_ids:
            assert cap_id not in agent2_capability_ids, \
                f"Found orphaned capability {cap_id} from agent1 in agent2's capabilities"
