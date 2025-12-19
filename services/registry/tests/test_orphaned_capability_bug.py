"""
Test to reproduce and verify fix for orphaned capabilities attaching to new agents.

This bug occurs when:
1. An agent is deleted but capabilities are orphaned (bug before our fix)
2. A new agent is created with capabilities
3. If orphaned capabilities exist with the same agent_table_id (due to ID reuse),
   they should NOT appear in the new agent's capability list
"""
import pytest
import warnings
from datetime import datetime, timezone
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from registry_service.core.database import AsyncSessionLocal
from registry_service.crud import agent_crud
from registry_service.services.agent_service import AgentRegistryService
from registry_service.models.agent import AgentTable, AgentCapabilityTable
from soorma_common import AgentDefinition, AgentCapability


def _now_utc() -> datetime:
    """Get current UTC time without timezone info (for SQLite compatibility)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


@pytest.mark.asyncio
@pytest.mark.filterwarnings("ignore::sqlalchemy.exc.SAWarning")
async def test_orphaned_capabilities_cleaned_on_agent_creation():
    """
    Test that orphaned capabilities are cleaned up by the background cleanup task.
    
    When orphaned capabilities exist and a new agent gets the same database ID,
    the orphaned capabilities will be visible until the background cleanup task runs.
    This test verifies that running the cleanup task removes the orphans.
    """
    async with AsyncSessionLocal() as db:
        # Step 1: Create an agent with capabilities
        original_agent = AgentDefinition(
            agent_id="original-agent",
            name="Original Agent",
            description="Agent that will be deleted leaving orphans",
            capabilities=[
                AgentCapability(
                    task_name="orphaned_capability",
                    description="This will become orphaned",
                    consumed_event="event.orphaned",
                    produced_events=["result.orphaned"]
                )
            ]
        )
        await AgentRegistryService.register_agent(db, original_agent)
        
        # Get the agent's database ID
        original_agent_table = await agent_crud.get_agent_by_id(
            db, "original-agent", include_expired=True
        )
        original_agent_db_id = original_agent_table.id
        
        # Step 2: Simulate the OLD BUG - use bulk delete on agent, leaving orphaned capability
        # (This is what happened before our first fix)
        await db.execute(
            delete(AgentTable).where(AgentTable.agent_id == "original-agent")
        )
        await db.commit()
        
        # Verify agent is deleted but capability is orphaned
        agent_check = await db.execute(
            select(AgentTable).where(AgentTable.id == original_agent_db_id)
        )
        assert agent_check.scalar_one_or_none() is None, "Agent should be deleted"
        
        orphaned_caps = await db.execute(
            select(AgentCapabilityTable).where(
                AgentCapabilityTable.agent_table_id == original_agent_db_id
            )
        )
        orphaned_caps_list = list(orphaned_caps.scalars().all())
        assert len(orphaned_caps_list) == 1, "Should have 1 orphaned capability for this test"
        
        # Step 3: Create a NEW agent that will get the same database ID
        new_agent = AgentDefinition(
            agent_id="new-agent-proper",
            name="New Agent Proper",
            description="New agent that will initially inherit orphaned capabilities",
            capabilities=[
                AgentCapability(
                    task_name="new_capability",
                    description="This is the only capability it should have after cleanup",
                    consumed_event="event.new",
                    produced_events=["result.new"]
                )
            ]
        )
        
        result = await AgentRegistryService.register_agent(db, new_agent)
        assert result.success is True
        
        # Get the new agent
        new_agent_table = await agent_crud.get_agent_by_id(
            db, "new-agent-proper", include_expired=True
        )
        
        # At this point, if IDs were reused, the agent might show orphaned capabilities
        # (This is the bug - orphaned capabilities can appear in the relationship)
        initial_cap_count = len(new_agent_table.capabilities)
        
        # Step 4: Run the background cleanup task which should remove orphaned capabilities
        deleted_agent_count = await AgentRegistryService.cleanup_expired_agents(db, ttl_seconds=3600)
        
        # No agents should be deleted (our agent is not expired)
        assert deleted_agent_count == 0
        
        # Step 5: Re-fetch the agent - orphaned capabilities should now be gone
        from registry_service.core.cache import invalidate_agent_cache
        invalidate_agent_cache("new-agent-proper")
        
        new_agent_table_after_cleanup = await agent_crud.get_agent_by_id(
            db, "new-agent-proper", include_expired=True
        )
        
        # CRITICAL CHECK: After cleanup, agent should only have its own capability
        assert len(new_agent_table_after_cleanup.capabilities) == 1, \
            f"After cleanup, agent should have exactly 1 capability, found {len(new_agent_table_after_cleanup.capabilities)}"
        
        assert new_agent_table_after_cleanup.capabilities[0].task_name == "new_capability", \
            "After cleanup, agent should only have its own capability, not orphaned ones"
        
        # Verify no orphaned capabilities remain for this agent's DB ID
        caps_for_agent = await db.execute(
            select(AgentCapabilityTable).where(
                AgentCapabilityTable.agent_table_id == new_agent_table_after_cleanup.id
            )
        )
        all_caps_for_id = list(caps_for_agent.scalars().all())
        assert len(all_caps_for_id) == 1, \
            f"Should only have 1 capability for this agent_table_id after cleanup, found {len(all_caps_for_id)}"
        
        assert all_caps_for_id[0].task_name == "new_capability", \
            "The only capability should be the new one, not orphaned"


@pytest.mark.asyncio
async def test_cleanup_removes_orphaned_capabilities():
    """
    Test that background cleanup task removes orphaned capabilities.
    Orphaned capabilities should be cleaned up by the periodic background task,
    not during agent registration.
    """
    async with AsyncSessionLocal() as db:
        # Create a legitimate agent
        agent = AgentDefinition(
            agent_id="cleanup-test-agent",
            name="Cleanup Test Agent",
            description="Agent for cleanup testing",
            capabilities=[
                AgentCapability(
                    task_name="legitimate_task",
                    description="Legitimate capability",
                    consumed_event="event.legitimate",
                    produced_events=["result.legitimate"]
                )
            ]
        )
        await AgentRegistryService.register_agent(db, agent)
        
        # Get agent DB ID
        agent_table = await agent_crud.get_agent_by_id(db, "cleanup-test-agent", include_expired=True)
        agent_db_id = agent_table.id
        
        # Manually insert an orphaned capability with a non-existent agent_table_id
        orphaned_cap = AgentCapabilityTable(
            agent_table_id=99999,  # Non-existent agent
            task_name="orphaned_task",
            description="Orphaned capability",
            consumed_event="event.orphaned",
            produced_events=["result.orphaned"]
        )
        db.add(orphaned_cap)
        await db.commit()
        
        # Verify orphaned capability exists
        all_caps_before = await db.execute(select(AgentCapabilityTable))
        caps_before_count = len(list(all_caps_before.scalars().all()))
        assert caps_before_count >= 2, "Should have at least the legitimate and orphaned capabilities"
        
        # Verify the orphaned capability is there
        orphaned_check = await db.execute(
            select(AgentCapabilityTable).where(
                AgentCapabilityTable.agent_table_id == 99999
            )
        )
        assert orphaned_check.scalar_one_or_none() is not None, "Orphaned capability should exist"
        
        # Now run the cleanup through service layer (as background task does)
        # This should clean up orphaned capabilities
        deleted_agent_count = await AgentRegistryService.cleanup_expired_agents(db, ttl_seconds=3600)
        
        # No agents should be deleted (our agent is not expired)
        assert deleted_agent_count == 0
