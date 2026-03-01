# Registry Service Multi-Tenancy Migration - Remaining Work

##Status: Service Layer Complete, CRUD Layer Partially Complete

### Completed (commits 6607cd4, ad9c044)
- ✅ Migration 003 fixed (deduplication added)
- ✅ Models updated (AgentTable, EventTable with tenant_id/user_id)
- ✅ API dependencies created (get_auth_context)
- ✅ API endpoints updated (agents, events)
- ✅ Service layer updated (agent_service, event_service)
- ✅ CRUD layer (partial): create_agent, upsert_agent, get_agent_by_id

### Remaining CRUD Updates

#### Agent CRUD (`services/registry/src/registry_service/crud/agents.py`)
Methods that need tenant_id parameter added:

1. **update_heartbeat** (line 312) - Add tenant_id param, pass to get_agent_by_id
2. **delete_agent** (line 328) - Add tenant_id param, add WHERE tenant_id filter
3. **get_agents_by_name** (line 193) - Add tenant_id param, add WHERE filter
4. **get_agents_by_consumed_event** (line 217) - Add tenant_id param, add WHERE filter  
5. **get_agents_by_produced_event** (line 241) - Add tenant_id param, add WHERE filter
6. **get_all_agents** (line 265) - Add tenant_id param, add WHERE filter

Pattern for updates:
```python
async def method_name(self, db: AsyncSession, ..., tenant_id: UUID) -> ...:
    query = select(AgentTable).where(
        AgentTable.tenant_id == tenant_id,
        # ... other filters
    )
```

#### Event CRUD (`services/registry/src/registry_service/crud/events.py`)
Methods that need updating:

1. **create_event** - Add tenant_id, user_id params, set in EventTable constructor
2. **upsert_event** - Add tenant_id, user_id params, pass to create_event, add to get_event_by_name call
3. **get_event_by_name** - Add tenant_id param, add WHERE filter
4. **get_events_by_topic** - Add tenant_id param, add WHERE filter
5. **get_all_events** - Add tenant_id param, add WHERE filter

### Testing Plan
After CRUD updates:
1. Restart `soorma dev --build`
2. Test agent registration: `cd examples/01-hello-world && python worker.py`
3. Verify no ValidationError or "null value" errors in logs
4. Test event registration (should happen automatically during agent startup)

### Migration Note
**IMPORTANT**: After completing CRUD updates, users need to:
```bash
soorma dev --down
soorma dev --build
```

This recreates the database with migration 003 applied correctly.
